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


def admins_only():
    async def predicate(ctx):
        return ctx.author.id in (426246773162639361, 416127116573278208)
    return commands.check(predicate)


@client.event
async def on_ready():
    print("\nLogged in as {}".format(client.user))

@client.event
async def on_command_error(ctx:Context, error):
    if isinstance(error, commands.errors.CommandNotFound):
        return

    print(f'\nMessage: "{ctx.message.content}"')
    traceback.print_exception(type(error), error, error.__traceback__)
    if hasattr(error, 'original'):
        error = error.original
    await ctx.send(f"```{type(error).__name__}: {str(error)}```")


@client.command()
async def ping(ctx:Context):
    await ctx.send('Pong!')

@client.command()
@admins_only()
async def config(ctx:Context, key, value=None, cast='str'):
    if value is None:
        val = cfg.config[key]
        await ctx.send(f"{key} = {val} {type(val)}")
    else:
        value, typ = cfg.set_config(key, value, locate(cast))
        await ctx.send(f"Set {key} = {value} {typ}")

@client.command()
@admins_only()
async def spawn(ctx:Context):
    definition = db.spawner.random_definition()
    msg = await ctx.send(embed=definition.get_embed())
    db.spawner.create_card_instance(definition, msg)

@client.command()
async def claim(ctx:Context):
    card = db.spawner.claim(ctx.author)
    if card is None:
        # No claimable cards
        await ctx.message.add_reaction('❌')
    elif isinstance(card, dt.timedelta):
        # Claim is on cooldown
        total = cfg.config['CLAIM_COOLDOWN'] - card.total_seconds()
        await ctx.send("Claim cooldown: {:d}m {:d}s".format(int(total//60), int(total%60)))
    elif isinstance(card, db.Card):
        # Claim successful
        msg = await ctx.channel.fetch_message(card.message_id)
        await msg.edit(embed=card.get_embed(ctx))
        await ctx.message.add_reaction('✅')


if __name__ == '__main__':
    with open('client_secret.txt', 'r') as secret:
        token = secret.read().strip()
    client.run(token)

    # db.Model.metadata.create_all(db.engine)
