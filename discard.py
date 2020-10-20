import asyncio
import datetime as dt
import random
import traceback
from operator import attrgetter
from pydoc import locate
from typing import Union

import discord as d
import pendulum
from discord.ext import commands
from discord.ext.commands import Bot, Context

import cfg
import db
import db.spawner
import db.transactions
import util

intents = d.Intents.default()
intents.members = True
client = Bot(command_prefix='$', intents=intents)
client.remove_command('help')  # Override help command


emoji = {
    'arrows_toggle': u'\U0001f504',
    'check': u'\u2705',
    'x': u'\u274c'
}
page_controls = {
    'next': u'\u25B6',
    'prev': u'\u25c0',
    'first': u'\u23eA',
    'last': u'\u23e9',
}


# --- Command Checks --- #

def admin_command():
    """ Debug command, only available to admins """
    async def predicate(ctx):
        return ctx.author.id in (426246773162639361, 416127116573278208)
    return commands.check(predicate)

def command_channel():
    """ Command is only available in the specific DisCard command channel. """
    async def predicate(ctx):
        return isinstance(ctx.channel, d.DMChannel) or ctx.channel.id in cfg.config['COMMAND_CHANNELS']
    return commands.check(predicate)

def trade_channel():
    """ Command is only available in the dedicated trading channel """
    async def predicate(ctx):
        return ctx.channel.id in cfg.config['TRADE_CHANNELS']
    return commands.check(predicate)

def no_private_messages():
    """ Command is not available in DMs """
    async def predicate(ctx:Context):
        return not isinstance(ctx.channel, d.DMChannel)
    return commands.check(predicate)


# --- Utility Functions --- #

async def page_turn(message, reaction, func):
    user = message.mentions[0]
    current, max_page = map(lambda n: int(n)-1, message.embeds[0].footer.text[5:].split('/'))  # cut off "Page " and split the slash

    if reaction == page_controls['next']: page = util.clamp(current+1, 0, max_page)
    elif reaction == page_controls['prev']: page = util.clamp(current-1, 0, max_page)
    elif reaction == page_controls['first']: page = 0
    elif reaction == page_controls['last']: page = max_page
    else: page = current

    if current == page: return
    await func(message, user, page, max_page)

async def add_page_reactions(message, max_page):
    if max_page > 0:
        if max_page > 5: await message.add_reaction(page_controls['first'])
        await message.add_reaction(page_controls['prev'])
        await message.add_reaction(page_controls['next'])
        if max_page > 5: await message.add_reaction(page_controls['last'])


# --- Client Events --- #

@client.event
async def on_ready():
    print("\nLogged in as {}".format(client.user))

    activity = d.Activity(type=d.ActivityType.listening, name='the sweet sound of a shuffling deck')
    await client.change_presence(activity=activity)

    client.loop.create_task(card_spawn_timer())

@client.event
async def on_command_error(ctx:Context, error):
    if isinstance(error, (commands.errors.CommandNotFound, commands.errors.CheckFailure)):
        return

    if hasattr(error, 'original'):
        error = error.original

    if isinstance(error, util.CleanException):
        await ctx.send(str(error))
        return

    print(f'\nMessage: "{ctx.message.content}"')
    traceback.print_exception(type(error), error, error.__traceback__)
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

        title = reaction.message.embeds[0].title
        if reaction.emoji in page_controls.values():
            if 'Card Collection' in title:
                await page_turn(reaction.message, reaction.emoji, inventory_page_turn)
            elif 'CardDex' in title:
                await page_turn(reaction.message, reaction.emoji, cardex_page_turn)
        elif reaction.emoji == emoji['arrows_toggle']:
            if 'Leaderboard' in title:
                await leaderboard_toggle(reaction.message)

        if not isinstance(reaction.message.channel, d.DMChannel): # Reactions can't be removed in DMs
            await reaction.remove(user)


# --- Help --- #

@client.command()
async def help(ctx:Context):
    embed = d.Embed()
    embed.set_author(name=cfg.config['EMBED_AUTHOR'])
    embed.title = 'Welcome to CCCards!'
    embed.url = cfg.config['HELP_URL']
    embed.set_thumbnail(url='https://cdn.discordapp.com/avatars/767097388212813854/066d29ec0189ce94f3271984f500bc84.png?size=256')
    embed.description = "Hey there! Welcome to the CCCards casino, friend. I'm your trusty card dealer, DisCard. " \
                        f"If you need some help, be sure to read our handbook here:\n{cfg.config['HELP_URL']}\n\n" \
                        "See ya in the leaderboards!"
    embed.colour = d.Color.dark_red()
    await ctx.send(embed=embed)


# --- Administrator Commands --- #

@client.command()
@admin_command()
async def ping(ctx:Context):
    await ctx.send('Pong!')

@client.command()
@admin_command()
async def config(ctx:Context, key=None, value=None, cast='str'):
    if key is None:
        await ctx.send("Available Config Options:```\n• " + '\n• '.join(cfg.config.keys()) + '```')
    else:
        if value is None:
            val = cfg.config[key]
            await ctx.send(f"{key} = {val} {type(val)}")
        else:
            value, typ = cfg.set_config(key, value, locate(cast))
            await ctx.send(f"Set {key} = {value} {typ}")

@client.command()
@admin_command()
async def enable(ctx:Context, channel:d.TextChannel, option:str):
    if option == 'commands':
        cfg.config['COMMAND_CHANNELS'].add(channel.id)
        await ctx.send(f'Enabled {channel.mention} for commands.')
    elif option == 'spawning':
        cfg.config['SPAWN_EXCLUDE_CHANNELS'].discard(channel.id)
        await ctx.send(f'Enabled {channel.mention} for card spawning.')
    elif option == 'trading':
        cfg.config['TRADE_CHANNELS'].add(channel.id)
        await ctx.send(f'Enabled {channel.mention} for card trading.')

@client.command()
@admin_command()
async def disable(ctx:Context, channel:d.TextChannel, option:str):
    if option == 'commands':
        cfg.config['COMMAND_CHANNELS'].discard(channel.id)
        await ctx.send(f'Disabled {channel.mention} for commands.')
    elif option == 'spawning':
        cfg.config['SPAWN_EXCLUDE_CHANNELS'].add(channel.id)
        await ctx.send(f'Disabled {channel.mention} for card spawning.')
    elif option == 'trading':
        cfg.config['TRADE_CHANNELS'].discard(channel.id)
        await ctx.send(f'Disabled {channel.mention} for card trading.')

@client.command()
@admin_command()
async def spawn(ctx:d.abc.Messageable, card_id:int=None):
    definition = db.spawner.get_definition(card_id)
    if definition:
        msg = await ctx.send(embed=definition.get_embed())
        db.spawner.create_card_instance(definition, msg.id, msg.channel.id)

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


# --- Card Claiming --- #

@client.command()
@no_private_messages()
async def claim(ctx:Context):
    card = db.spawner.claim(ctx.author.id, ctx.channel.id)
    if card is None:
        # No claimable cards
        await ctx.message.add_reaction(emoji['x'])
    elif isinstance(card, dt.timedelta):
        # Claim is on cooldown
        total = cfg.config['CLAIM_COOLDOWN'] - card.total_seconds()
        await ctx.send("Claim cooldown: **{:d}m {:d}s**".format(int(total//60), int(total%60)))
    elif isinstance(card, db.Card):
        # Claim successful
        try:
            msg = await ctx.channel.fetch_message(card.message_id)
        except d.NotFound:
            db.spawner.delete_card_instance(card)
            await claim(ctx) # Claim the next available card
        else:
            await msg.edit(embed=card.get_embed(ctx))
            await ctx.message.add_reaction(emoji['check'])


# --- Inventory, Dex, Leaderboard --- #

@client.command(aliases=['inv'])
@command_channel()
async def inventory(ctx:Context):
    inv = db.Inventory(ctx.author.id)
    msg = await ctx.send(content=ctx.author.mention, embed=inv.get_embed(ctx.author.display_name, 0))
    await add_page_reactions(msg, inv.max_page)

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

@client.command(aliases=['deck', 'cardeck', 'carddeck', 'dex', 'carddex'])
@command_channel()
async def cardex(ctx:Context):
    dex = db.CardDex(ctx.author.id)
    msg = await ctx.send(content=ctx.author.mention, embed=dex.get_embed(ctx.author.display_name, 0))
    await add_page_reactions(msg, dex.max_page)

async def cardex_page_turn(message, user, page, max_page):
    dex = db.CardDex(user.id)
    await message.edit(content=user.mention, embed=dex.get_embed(user.display_name, page))

@client.command(aliases=['lb'])
async def leaderboard(ctx:Context):
    lb = db.Leaderboard(db.Leaderboard.WEIGHTED)
    msg = await ctx.send(embed=lb.get_embed(ctx.guild.get_member, 0))
    await add_page_reactions(msg, lb.max_page)
    await msg.add_reaction(emoji['arrows_toggle'])

async def leaderboard_page_turn(message, user, page, max_page):
    mode = db.Leaderboard.WEIGHTED if '| Weighted' in message.embeds[0].title else db.Leaderboard.UNWEIGHTED
    lb = db.Leaderboard(mode)
    await message.edit(embed=lb.get_embed(message.guild.get_member, page))

async def leaderboard_toggle(message):
    mode = db.Leaderboard.UNWEIGHTED if '| Weighted' in message.embeds[0].title else db.Leaderboard.WEIGHTED
    lb = db.Leaderboard(mode)
    await message.edit(embed=lb.get_embed(message.guild.get_member, 0))


# --- Trading & Discarding --- #

@client.command()
@trade_channel()
async def trade(ctx:Context, action:Union[d.Member, int, str, None]=None, amount:Union[int, str]=1):
    await ctx.message.delete(delay=1)

    transaction = db.transactions.get_active_transaction(ctx.author.id)

    if isinstance(action, d.Member):
        if action == ctx.author: await ctx.send("Hey, feel free to trade with yourself all you like, you don't need me for that.")
        elif action == client.user: await ctx.send("I'd love to, but I gotta keep it fair here, and trading cards with the dealer is a bit disingenuous.")
        elif action.bot: await ctx.send("Sorry, but bots just don't show enough appreciation for the art of the trade for me to support that. Call it principle.")
        elif not transaction:
            transaction = db.transactions.open_transaction(ctx.author.id, action.id)
            await update_trade(ctx, transaction)
        elif transaction.is_party(ctx.author.id): await ctx.send("You already have an active trade open. Please finish or cancel it before starting another one.")
        elif transaction.is_party(action.id): await ctx.send("This person already has an active trade open. Please wait for them to finish before starting a trade.")
        else: raise RuntimeError(f"Invalid transaction: {transaction.id}")

    elif isinstance(action, int):
        await trade_add(ctx, transaction, action, amount)

    elif action == 'resend':
        if not transaction: raise util.NoActiveTrade()
        await resend_trade(ctx, transaction)

    elif isinstance(action, str):
        raise util.UserNotFound(action)

    elif action is None:
        if not transaction: raise util.NoActiveTrade()

async def update_trade(ctx:Context, transaction:db.Transaction, closed=False):
    name_1 = ctx.guild.get_member(transaction.user_1).display_name
    name_2 = ctx.guild.get_member(transaction.user_2).display_name
    if transaction.message_id:
        msg = await ctx.channel.fetch_message(transaction.message_id)
        await msg.edit(embed=transaction.get_embed(name_1, name_2, closed=closed))
    else:
        msg = await ctx.send(embed=transaction.get_embed(name_1, name_2, closed=closed))
        db.transactions.set_transaction_message(transaction, msg.id)

async def resend_trade(ctx:Context, transaction:db.Transaction):
    transaction.message_id = None
    await update_trade(ctx, transaction)

async def trade_add(ctx:Context, transaction:db.Transaction, card_id:int, amount:Union[int, str]):
    if not transaction: raise util.NoActiveTrade()
    if (isinstance(amount, str) and amount != 'all') \
    or (isinstance(amount, int) and amount < 1): return

    if transaction.locked: return

    added_cards = transaction.card_set(transaction.get_user(ctx.author.id))
    cards = util.query_card_amount(ctx.author.id, card_id, amount, exclude=added_cards)
    if cards:
        transaction.add_cards(ctx.author.id, cards)
        db.session.commit()
        await update_trade(ctx, transaction)

@client.command()
@trade_channel()
async def add(ctx:Context, card_id:int, amount:Union[int, str]=1):
    await ctx.message.delete(delay=1)
    transaction = db.transactions.get_active_transaction(ctx.author.id)
    await trade_add(ctx, transaction, card_id, amount=amount)

@client.command(aliases=['remove'])
@trade_channel()
async def untrade(ctx:Context, card_id:int, amount:Union[int, str]=1):
    await ctx.message.delete(delay=1)
    if (isinstance(amount, str) and amount != 'all') \
    or (isinstance(amount, int) and amount < 1): return

    transaction = db.transactions.get_active_transaction(ctx.author.id)
    if not transaction: raise util.NoActiveTrade()
    if transaction.locked: return

    cards = util.query_cards(transaction.card_set(ctx.author.id), card_id=card_id)[:amount if amount != 'all' else None]
    if cards:
        transaction.remove_cards(ctx.author.id, cards)
        db.session.commit()
        await update_trade(ctx, transaction)

@client.command()
@trade_channel()
async def accept(ctx:Context):
    await ctx.message.delete(delay=1)

    transaction = db.transactions.get_active_transaction(ctx.author.id)
    if not transaction: raise util.NoActiveTrade()
    if transaction.has_accepted(ctx.author.id): return

    transaction.set_accepted(ctx.author.id, True)
    if transaction.complete:
        db.transactions.execute(transaction)
    await update_trade(ctx, transaction)

@client.command()
@trade_channel()
async def unaccept(ctx:Context):
    await ctx.message.delete(delay=1)

    transaction = db.transactions.get_active_transaction(ctx.author.id)
    if not transaction: raise util.NoActiveTrade()
    if not transaction.has_accepted(ctx.author.id): return

    transaction.set_accepted(ctx.author.id, False)
    await update_trade(ctx, transaction)

@client.command(aliases=['close'])
@trade_channel()
async def cancel(ctx:Context):
    await ctx.message.delete(delay=1)

    transaction = db.transactions.close_active_transaction(ctx.author.id)
    if transaction:
        name_1 = ctx.guild.get_member(transaction.user_1).display_name
        name_2 = ctx.guild.get_member(transaction.user_2).display_name
        await update_trade(ctx, transaction, closed=True)
        await ctx.send(f"Trade between {name_1} and {name_2} has been closed.")
    else:
        raise util.NoActiveTrade()


# --- Event Schedulers --- #

async def card_spawn_timer():
    await client.wait_until_ready()
    while not client.is_closed():
        variation = cfg.config['SPAWN_INTERVAL_VARIATION']
        delay = cfg.config['SPAWN_INTERVAL'] * (1 - (random.random() * variation*2 - variation))

        now = pendulum.now('US/Eastern')
        time = now.add(seconds=delay)
        start, end = cfg.config['SPAWN_INTERVAL_START_TIME'], cfg.config['SPAWN_INTERVAL_END_TIME']
        if not start < time.hour < end:
            time = time.set(hour=start, minute=0, second=0, microsecond=0)
            if not time > now:
                time = time.add(days=1)
            delay = (time - now).total_seconds()

        await asyncio.sleep(delay)

        def spawnable(channel):
            return isinstance(channel, d.TextChannel) and channel.id != cfg.config['TRADE_CHANNEL']

        channels = set(map(
            attrgetter('id'), # Map channel to channel ID
            filter(spawnable, client.get_all_channels()) # Filter for only TextChannels
        ))
        await spawn(client.get_channel(
            random.choice(list(channels - cfg.config['SPAWN_EXCLUDE_CHANNELS']))
        ))


# --- Main --- #

if __name__ == '__main__':
    with open('client_secret.txt', 'r') as secret:
        token = secret.read().strip()
    client.run(token)

    # db.Model.metadata.create_all(db.engine)
