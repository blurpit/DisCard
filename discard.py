import datetime as dt
import traceback
from pydoc import locate

import discord as d
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
    async def predicate(ctx):
        return ctx.author.id in (426246773162639361, 416127116573278208)
    return commands.check(predicate)

def command_channel():
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
async def spawn(ctx:Context):
    definition = db.spawner.random_definition()
    msg = await ctx.send(embed=definition.get_embed())
    db.spawner.create_card_instance(definition, msg)

@client.command()
async def claim(ctx:Context):
    card = db.spawner.claim(ctx.author)
    if card is None:
        # No claimable cards
        await ctx.message.add_reaction(emoji['x'])
    elif isinstance(card, dt.timedelta):
        # Claim is on cooldown
        total = cfg.config['CLAIM_COOLDOWN'] - card.total_seconds()
        await ctx.send("Claim cooldown: {:d}m {:d}s".format(int(total//60), int(total%60)))
    elif isinstance(card, db.Card):
        # Claim successful
        msg = await ctx.channel.fetch_message(card.message_id)
        await msg.edit(embed=card.get_embed(ctx))
        await ctx.message.add_reaction(emoji['check'])

@client.command(aliases=['inv'])
@command_channel()
async def inventory(ctx:Context):
    inv = db.Inventory(ctx.author.id)
    msg = await ctx.send(content=ctx.author.mention, embed=inv.get_embed(ctx.author, 0))
    if inv.max_page > 0:
        await msg.add_reaction(emoji['arrow_prev'])
        await msg.add_reaction(emoji['arrow_next'])

async def inventory_page_turn(message, user, page, max_page):
    inv = db.Inventory(user.id)
    await message.edit(content=user.mention, embed=inv.get_embed(user, page))


if __name__ == '__main__':
    with open('client_secret.txt', 'r') as secret:
        token = secret.read().strip()
    client.run(token)

    # db.Model.metadata.create_all(db.engine)
