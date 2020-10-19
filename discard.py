import asyncio
import datetime as dt
import random
import traceback
from pydoc import locate

import discord as d
import pendulum
from discord.ext import commands
from discord.ext.commands import Bot, Context

import cfg
import db
import db.spawner

intents = d.Intents.default()
intents.members = True
client = Bot(command_prefix='$', intents=intents)
client.remove_command('help')  # Override help command


emoji = {
    'arrow_next': u'\u25B6',
    'arrow_prev': u'\u25c0',
    'check': u'\u2705',
    'x': u'\u274c'
}


def admin_command():
    """ Debug command, only available to admins """
    async def predicate(ctx):
        return ctx.author.id in (426246773162639361, 416127116573278208)
    return commands.check(predicate)

def command_channel():
    """ Command is only available in the specific DisCard command channel. """
    async def predicate(ctx):
        return ctx.channel.id == cfg.config['COMMAND_CHANNEL_ID']
    return commands.check(predicate)

async def page_turn(message, func, direction):
    user = message.mentions[0]
    page, max_page = map(lambda n: int(n)-1, message.embeds[0].footer.text[5:].split('/'))  # cut off "Page " and split the slash

    if (page == max_page and direction > 0) or (page == 0 and direction < 0):
        return

    await func(message, user, page+direction, max_page)


@client.event
async def on_ready():
    print("\nLogged in as {}".format(client.user))

    cmd_channel = client.get_channel(cfg.config['COMMAND_CHANNEL_ID']).name
    activity = d.Activity(type=d.ActivityType.listening, name='$help in #'+cmd_channel)
    await client.change_presence(activity=activity)

    client.loop.create_task(card_spawn_timer())

@client.event
async def on_command_error(ctx:Context, error):
    if isinstance(error, (commands.errors.CommandNotFound, commands.errors.CheckFailure)):
        return

    print(f'\nMessage: "{ctx.message.content}"')
    traceback.print_exception(type(error), error, error.__traceback__)
    if hasattr(error, 'original'):
        error = error.original
    await ctx.send(f"```{type(error).__name__}: {str(error)}```")

@client.event
async def on_message(message:d.Message):
    if not message.author.bot:
        if not message.clean_content.startswith(client.command_prefix) \
                and random.random() <= cfg.config['SPAWN_MESSAGE_CHANCE']:
            await spawn(message.channel)
        await client.process_commands(message)

@client.event
async def on_reaction_add(reaction:d.Reaction, user:d.Member):
    if not user.bot and reaction.message.author == client.user:
        if reaction.emoji in (emoji['arrow_prev'], emoji['arrow_next']):
            direction = 1 if reaction.emoji == emoji['arrow_next'] else -1
            if reaction.message.embeds[0].title.endswith('Card Collection'):
                await page_turn(reaction.message, inventory_page_turn, direction)
            await reaction.remove(user)


@client.command()
async def ping(ctx:Context):
    await ctx.send('Pong!')

@client.command()
@admin_command()
async def config(ctx:Context, key, value=None, cast='str'):
    if value is None:
        val = cfg.config[key]
        await ctx.send(f"{key} = {val} {type(val)}")
    else:
        value, typ = cfg.set_config(key, value, locate(cast))
        await ctx.send(f"Set {key} = {value} {typ}")

@client.command()
@admin_command()
async def spawn(ctx:d.abc.Messageable, card_id:int=None):
    definition = db.spawner.get_definition(card_id)
    msg = await ctx.send(embed=definition.get_embed())
    db.spawner.create_card_instance(definition, msg.id)

@client.command()
@admin_command()
async def give(ctx:Context, recipient:d.Member, card_id:int):
    card = db.Inventory(ctx.author.id)[card_id]
    if card is None:
        await ctx.send("You don't have that card in your collection.")
    else:
        card.owner_id = recipient.id
        db.session.commit()
        await ctx.send(f"Gave {card.definition.string()} to **{recipient.display_name}**.")

@client.command()
async def claim(ctx:Context):
    card = db.spawner.claim(ctx.author.id)
    if card is None:
        # No claimable cards
        await ctx.message.add_reaction(emoji['x'])
    elif isinstance(card, dt.timedelta):
        # Claim is on cooldown
        total = cfg.config['CLAIM_COOLDOWN'] - card.total_seconds()
        await ctx.send("Claim cooldown: **{:d}m {:d}s**".format(int(total//60), int(total%60)))
    elif isinstance(card, db.Card):
        # Claim successful
        msg = await ctx.channel.fetch_message(card.message_id)
        await msg.edit(embed=card.get_embed(ctx))
        await ctx.message.add_reaction(emoji['check'])

@client.command(aliases=['inv'])
@command_channel()
async def inventory(ctx:Context):
    inv = db.Inventory(ctx.author.id)
    msg = await ctx.send(content=ctx.author.mention, embed=inv.get_embed(ctx.author.display_name, 0))
    if inv.max_page > 0:
        await msg.add_reaction(emoji['arrow_prev'])
        await msg.add_reaction(emoji['arrow_next'])

async def inventory_page_turn(message, user, page, max_page):
    inv = db.Inventory(user.id)
    await message.edit(content=user.mention, embed=inv.get_embed(user.display_name, page))

@client.command(aliases=['preview', 'view'])
@command_channel()
async def show(ctx:Context, card_id:int):
    inv = db.Inventory(ctx.author.id)
    if card_id in inv:
        await ctx.send(embed=inv[card_id].get_embed(
            ctx, preview=True,
            count=inv.count(card_id))
        )
    else:
        await ctx.send("You don't have that card in your collection.")


async def card_spawn_timer():
    await client.wait_until_ready()
    while not client.is_closed():
        delay = cfg.config['SPAWN_INTERVAL']

        now = pendulum.now('US/Eastern')
        time = now.add(seconds=delay)
        start, end = cfg.config['SPAWN_INTERVAL_START_TIME'], cfg.config['SPAWN_INTERVAL_END_TIME']
        if not start < time.hour < end:
            time = time.set(hour=start, minute=0, second=0, microsecond=0)
            if not time > now:
                time = time.add(days=1)
            delay = (time - now).total_seconds()

        await asyncio.sleep(delay)

        channel = client.get_channel(cfg.config['SPAWN_INTERVAL_CHANNEL_ID'])
        await spawn(channel)


if __name__ == '__main__':
    with open('client_secret.txt', 'r') as secret:
        token = secret.read().strip()
    client.run(token)

    # db.Model.metadata.create_all(db.engine)
