import datetime as dt
import random
from pprint import pformat
from typing import Union

import discord as d
import pendulum
from discord.ext import commands
from discord.ext.commands import Bot, Context

import cfg
import db
import db.spawner
import db.transactions
import events
import util

intents = d.Intents.default()
intents.members = True
client = Bot(command_prefix='$', intents=intents, case_insensitive=True)
client.remove_command('help')  # Override help command


# --- Command Checks --- #

def admin_command():
    """ Debug command, only available to admins """
    async def predicate(ctx):
        return ctx.author.id in cfg.ADMINISTRATORS
    return commands.check(predicate)

def command_channel():
    """ Command is only available in the specific DisCard command channel. """
    async def predicate(ctx):
        return isinstance(ctx.channel, d.TextChannel) \
               and ctx.channel.id in cfg.config['COMMAND_CHANNELS'][ctx.guild.id]
    return commands.check(predicate)

def trade_channels():
    """ Command is only available in the dedicated trading channel """
    async def predicate(ctx):
        return ctx.channel.id in cfg.config['TRADE_CHANNELS'][ctx.guild.id]
    return commands.check(predicate)


# --- Utility Functions --- #

async def page_turn(message, reaction, func, *args, **kwargs):
    page_text = message.embeds[0].footer.text.split('|')[0].strip()[5:] # "Page x/y | blah" -> "x/y"
    current, max_page = map(lambda n: int(n)-1, page_text.split('/'))

    if reaction == cfg.page_controls['next']: page = util.clamp(current+1, 0, max_page)
    elif reaction == cfg.page_controls['prev']: page = util.clamp(current-1, 0, max_page)
    elif reaction == cfg.page_controls['first']: page = 0
    elif reaction == cfg.page_controls['last']: page = max_page
    else: page = current
    if page == current: return

    user = message.mentions[0] if message.mentions else None
    await func(message, user, page, max_page, *args, **kwargs)

async def add_page_reactions(message, max_page):
    if max_page > 0:
        if max_page > 5: await message.add_reaction(cfg.page_controls['first'])
        await message.add_reaction(cfg.page_controls['prev'])
        await message.add_reaction(cfg.page_controls['next'])
        if max_page > 5: await message.add_reaction(cfg.page_controls['last'])


# --- Client Events --- #

@client.event
async def on_ready():
    util.log.info('\n')
    util.log.info('Logged in as %s (%d)', str(client.user), client.user.id)
    print('Logged in as {}'.format(client.user))

    activity = d.Activity(type=d.ActivityType.listening, name='the sweet sound of shuffling')
    await client.change_presence(activity=activity)

    if cfg.config['SPAWN_INTERVAL'] > 0:
        client.loop.create_task(CardIntervalSpawnTask().create(client))
    if cfg.config['SPAWN_INTERVAL_END_TIME'] - cfg.config['SPAWN_INTERVAL_START_TIME'] > 0:
        client.loop.create_task(CardEventGameTask().create(client))
        client.loop.create_task(CardEventGameTask('hangman').create(client))

@client.event
async def on_command_error(ctx:Context, error):
    if isinstance(error, (commands.errors.CommandNotFound, commands.errors.CheckFailure)):
        return

    if hasattr(error, 'original'):
        error = error.original

    if isinstance(error, util.CleanException):
        await ctx.send(str(error))
        return

    util.log.error('Error on command: %s', ctx.message.content, exc_info=error)
    await ctx.send(f"```{type(error).__name__}: {str(error)}```")

@client.event
async def on_message(message:d.Message):
    if not message.author.bot and not isinstance(message.channel, d.DMChannel) \
            and message.guild.id in cfg.config['ENABLED_GUILDS']:

        cfg.add_consecutive_message(message.author.id)
        if not message.clean_content.startswith(client.command_prefix) \
                and message.channel.id in cfg.config['SPAWN_MESSAGE_CHANNELS'][message.guild.id] \
                and random.random() <= cfg.config['SPAWN_MESSAGE_CHANCE'] \
                and dt.datetime.utcnow() >= cfg.last_spawn + dt.timedelta(seconds=cfg.config['SPAWN_MESSAGE_COOLDOWN']) \
                and cfg.consecutive_messages[1] <= cfg.config['SPAWN_MESSAGE_MAX_CONSECUTIVE']:
            util.log.debug('Message spawn on message by %s: "%s"', str(message.author), message.content)
            await spawn(message.channel)

        await client.process_commands(message)

@client.event
async def on_reaction_add(reaction:d.Reaction, user:d.Member):
    if not user.bot and reaction.message.author == client.user \
            and not isinstance(reaction.message.channel, d.DMChannel) \
            and reaction.message.guild.id in cfg.config['ENABLED_GUILDS']:

        title = reaction.message.embeds[0].title
        if reaction.emoji in cfg.page_controls.values():
            if 'Card Collection' in title:
                await page_turn(reaction.message, reaction.emoji, inventory_page_turn,
                                dupes_only='(Duplicates Only)' in title)
            elif 'CardDex' in title:
                await page_turn(reaction.message, reaction.emoji, cardex_page_turn)
            elif 'Leaderboard' in title:
                await page_turn(reaction.message, reaction.emoji, leaderboard_page_turn)
        elif reaction.emoji == cfg.emoji['arrows_toggle']:
            if 'Leaderboard' in title:
                await leaderboard_toggle(reaction.message)

        await reaction.remove(user)


# --- Help --- #

@client.group()
async def help(ctx:Context):
    if ctx.invoked_subcommand is None:
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

@help.command()
async def chungus(ctx:Context):
    card = db.spawner.get_definition(ctx.guild.id, 94)
    await ctx.send(embed=card.get_embed(preview=True))


# --- Administrator Commands --- #

@client.command()
@admin_command()
async def ping(ctx:Context):
    latency = client.latency * 1000
    util.log.debug('[Admin] Pinged with latency: %f ms', latency)
    await ctx.send('Pong! (latency: {:.0f} ms)'.format(latency))

@client.command()
@admin_command()
async def kill(ctx:Context):
    await ctx.send('Goodbye...')
    util.log.warning('[Admin] Bot killed by %s', str(ctx.author))
    await client.close()

@client.command()
@admin_command()
async def sql(ctx:Context, *, clause:str):
    util.log.warning('[Admin] Execute SQL: %s', clause)
    response = db.session.execute(clause)
    if response.returns_rows:
        content = '\n'.join(', '.join(map(str, row)) for row in response)
        if not content:
            content = 'No results'
        elif len(content) > 1991:
            content = content[:1991] + '...'
        await ctx.send('```' + content + '```')
    else:
        db.session.commit()
        await ctx.send('Successfully updated.')

@client.command()
@admin_command()
async def config(ctx:Context, key=None, value=None):
    if key is None:
        await ctx.send("Available Config Options:```\n• " + '\n• '.join(cfg.config.keys()) + '```')
    else:
        if value is None:
            value = cfg.config[key]
            await ctx.send("```py\n{}\n{}```".format(pformat(value, indent=4, width=90, compact=True), type(value)))
        else:
            util.log.warning("[Admin] Config change for %s to %s %s", key, str(value), str(type(value)))
            value = cfg.set_config(key, value)
            await ctx.send("Set `{} = {} {}`".format(key, value, type(value)))

@client.command()
@admin_command()
async def enable(ctx:Context, channel:d.TextChannel, option:str, *sub_opts:str):
    util.log.warning("[Admin] Enable channel '%s' (%d) for %s", channel, channel.id, '/'.join((option, *sub_opts)))
    if option == 'commands':
        cfg.config['COMMAND_CHANNELS'][ctx.guild.id].add(channel.id)
        await ctx.send(f'Enabled {channel.mention} for commands.')
    elif option == 'spawning':
        if not sub_opts or sub_opts[0] == 'message':
            cfg.config['SPAWN_MESSAGE_CHANNELS'][ctx.guild.id].add(channel.id)
            await ctx.send(f'Enabled {channel.mention} for card message spawning.')
        if not sub_opts or sub_opts[0] == 'interval':
            cfg.config['SPAWN_INTERVAL_CHANNELS'][ctx.guild.id].add(channel.id)
            await ctx.send(f'Enabled {channel.mention} for card interval spawning.')
    elif option == 'trading':
        cfg.config['TRADE_CHANNELS'][ctx.guild.id].add(channel.id)
        await ctx.send(f'Enabled {channel.mention} for card trading.')
    elif option == 'events':
        cfg.config['SPAWN_EVENT_GAME_CHANNELS'].add(channel.id)
        await ctx.send(f'Enabled {channel.mention} for event game spawning.')

@client.command()
@admin_command()
async def disable(ctx:Context, channel:d.TextChannel, option:str, *sub_opts:str):
    util.log.warning("[Admin] Disable channel '%s' (%d) for %s", channel, channel.id, '/'.join((option, *sub_opts)))
    if option == 'commands':
        cfg.config['COMMAND_CHANNELS'][ctx.guild.id].discard(channel.id)
        await ctx.send(f'Disabled {channel.mention} for commands.')
    elif option == 'spawning':
        if not sub_opts or sub_opts[0] == 'message':
            cfg.config['SPAWN_MESSAGE_CHANNELS'][ctx.guild.id].discard(channel.id)
            await ctx.send(f'Disabled {channel.mention} for card message spawning.')
        if not sub_opts or sub_opts[0] == 'interval':
            cfg.config['SPAWN_INTERVAL_CHANNELS'][ctx.guild.id].discard(channel.id)
            await ctx.send(f'Disabled {channel.mention} for card interval spawning.')
    elif option == 'trading':
        cfg.config['TRADE_CHANNELS'][ctx.guild.id].discard(channel.id)
        await ctx.send(f'Disabled {channel.mention} for card trading.')
    elif option == 'events':
        cfg.config['SPAWN_EVENT_GAME_CHANNELS'].discard(channel.id)
        await ctx.send(f'Disabled {channel.mention} for event game spawning.')

@client.command()
@admin_command()
async def enable_event_category(ctx:Context, category:str):
    util.log.warning('[Admin] Enable event card category: %s', category)
    cat = cfg.EventCategory[category.upper()]
    cfg.config['ENABLED_EVENT_CARD_CATEGORIES'].add(cat)
    await ctx.send('Enabled event card spawning for **{}**.'.format(cat))

@client.command()
@admin_command()
async def disable_event_category(ctx:Context, category:str):
    util.log.warning('[Admin] Disable event card category: %s', category)
    cat = cfg.EventCategory[category.upper()]
    cfg.config['ENABLED_EVENT_CARD_CATEGORIES'].discard(cat)
    await ctx.send('Disabled event card spawning for **{}**.'.format(cat))

@client.command()
@admin_command()
async def set_claim_cooldown(ctx:Context, rarity:str, value:int):
    util.log.warning('[Admin] Set claim cooldown for %s: %d', rarity, value)
    rarity = cfg.Rarity[rarity.upper()]
    cfg.config['CLAIM_COOLDOWN'][rarity] = value
    await ctx.send('Set claim cooldown for {} to {} seconds'.format(rarity, value))

@client.command()
@admin_command()
async def spawn(ctx, card:Union[int, str]=None):
    definition = db.spawner.get_definition(ctx.guild.id, card)
    if definition:
        msg = await ctx.send(embed=definition.get_embed())
        db.spawner.create_card_instance(definition, msg.id, msg.channel.id, msg.guild.id)
        util.log.info('Card Spawn: [#%d] %s (%s), guild: %s, channel: %s',
                      definition.id, definition.name, definition.rarity.name, str(msg.guild), str(msg.channel))
        cfg.last_spawn = dt.datetime.utcnow()
    else:
        util.log.error('No definition was found for card spawn!')

@client.command()
@admin_command()
async def spawn_event(ctx:d.abc.Messageable, event_type:str=None):
    event = events.create(event_type)
    util.log.info('Event spawned of type: %s', str(event))

    msg = await ctx.send(**event.generate())
    await event.on_message(msg)

@client.command()
@admin_command()
async def testview(ctx:Context, card:Union[int, str]):
    card = db.spawner.get_definition(ctx.guild.id, card)
    await ctx.send(embed=card.get_embed(preview=True))

@client.command()
@admin_command()
async def gift(ctx:Context, user:Union[d.Member, str], rarity:str):
    rarity = cfg.Rarity[rarity.upper()]
    if user == 'everyone' or user == 'all':
        response = f":partying_face: Hey hey! Everyone has been generously gifted 1 x Random **{rarity.text}**! ヽ(^o^)ノ"
    elif isinstance(user, d.Member):
        response = f":partying_face: Hey {user.mention}, you have been generously gifted 1 x Random **{rarity.text}**! ヽ(^o^)ノ"
    else:
        return

    for user in ctx.guild.members if user == 'everyone' or user == 'all' else (user,):
        if not user.bot:
            definition = db.spawner.get_definition(ctx.guild.id, rarity=rarity)
            if definition:
                db.spawner.create_card_instance(definition, 0, 0, ctx.guild.id, user.id)
                response += f'\n\t• **{user.display_name}**: You got [#{definition.id}] **{definition.name}** *{definition.set.text}*'
            else:
                response += '\nUnfortunately, the pool ran out before everyone could get their card. Sorry :pensive:'
                break
    await ctx.send(response)


# --- Card Claiming --- #

@client.command()
async def claim(ctx:Context):
    card = db.spawner.claim(ctx.author.id, ctx.channel.id, ctx.guild.id)
    if card is None:
        # No claimable cards
        await ctx.message.add_reaction(cfg.emoji['x'])
    else:
        # Claim successful
        util.log.info('Card Claim by %s: [#%d] %s, instance ID: %d, guild: %s, channel: %s',
                      str(ctx.author), card.definition.id, card.definition.name, card.id, str(ctx.guild),
                      str(ctx.channel))
        try:
            msg = await ctx.channel.fetch_message(card.message_id)
        except d.NotFound:
            await ctx.send(embed=card.get_embed(ctx))
        else:
            await msg.edit(embed=card.get_embed(ctx))
        await ctx.message.add_reaction(cfg.emoji['check'])


# --- Events --- #

@client.command(aliases=['guess'])
async def answer(ctx:Context, *, guess:str=None):
    event = events.current(ctx.guild.id)
    if event:
        await event.on_guess(ctx, guess)


# --- Inventory, Dex, Leaderboard --- #

@client.command(aliases=['inv'])
@command_channel()
async def inventory(ctx:Context, dupes_only:str=''):
    dupes_only = dupes_only.lower() in ('dupe', 'dupes', 'duplicate', 'duplicates')
    inv = db.Inventory(ctx.author.id, ctx.guild.id, dupes_only)
    msg = await ctx.send(content=ctx.author.mention, embed=inv.get_embed(ctx.author.display_name, 0))
    await add_page_reactions(msg, inv.max_page)

async def inventory_page_turn(message, user, page, max_page, dupes_only=False):
    inv = db.Inventory(user.id, message.guild.id, dupes_only)
    await message.edit(content=user.mention, embed=inv.get_embed(user.display_name, page))

@client.command(aliases=['show', 'preview'])
@command_channel()
async def view(ctx:Context, *, card:Union[int, str]):
    definition, count = db.query_card_ownership(ctx.author.id, ctx.guild.id, card)
    if definition:
        await ctx.send(embed=definition.get_embed(preview=True, count=count))
    else:
        await ctx.send("You haven't discovered that card.")

@client.command(aliases=['deck', 'cardeck', 'carddeck', 'cardex', 'carddex'])
@command_channel()
async def dex(ctx:Context):
    dex = db.CardDex(ctx.author.id, ctx.guild.id)
    msg = await ctx.send(content=ctx.author.mention, embed=dex.get_embed(ctx.author.display_name, 0))
    await add_page_reactions(msg, dex.max_page)

async def cardex_page_turn(message, user, page, max_page):
    dex = db.CardDex(user.id, message.guild.id)
    await message.edit(content=user.mention, embed=dex.get_embed(user.display_name, page))

@client.command(aliases=['lb', 'leaderboards', 'scoreboard'])
@command_channel()
async def leaderboard(ctx:Context):
    lb = db.Leaderboard(db.Leaderboard.WEIGHTED, ctx.guild.id)
    msg = await ctx.send(embed=lb.get_embed(ctx.guild.get_member, 0))
    await add_page_reactions(msg, lb.max_page)
    await msg.add_reaction(cfg.emoji['arrows_toggle'])

async def leaderboard_page_turn(message, user, page, max_page):
    mode = db.Leaderboard.WEIGHTED if '| Weighted' in message.embeds[0].title else db.Leaderboard.UNWEIGHTED
    lb = db.Leaderboard(mode, message.guild.id)
    await message.edit(embed=lb.get_embed(message.guild.get_member, page))

async def leaderboard_toggle(message):
    mode = db.Leaderboard.UNWEIGHTED if '| Weighted' in message.embeds[0].title else db.Leaderboard.WEIGHTED
    lb = db.Leaderboard(mode, message.guild.id)
    await message.edit(embed=lb.get_embed(message.guild.get_member, 0))


# --- Trading & Discarding --- #

@client.command()
@trade_channels()
async def trade(ctx:Context, action:Union[d.Member, int, str, None]=None, amount:Union[int, str]=1):
    await ctx.message.delete(delay=1)

    transaction = db.transactions.get_active_transaction(ctx.author.id, ctx.guild.id)

    if isinstance(action, d.Member):
        if action == ctx.author: await ctx.send("Hey, feel free to trade with yourself all you like, you don't need me for that.")
        elif action == client.user: await ctx.send("Wanna trade some cards with me? Try using **$exchange**!")
        elif action.bot: await ctx.send("Sorry, but bots just don't show enough appreciation for the art of the trade for me to support that. Call it principle.")
        elif not transaction:
            transaction = db.transactions.open_transaction(ctx.author.id, action.id, ctx.guild.id)
            util.log.info('[Trade] Transaction opened between %s and %s', str(ctx.author), str(action))
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
        if not await trade_add(ctx, transaction, action, amount):
            if transaction: raise util.NotInInventory(action)
            else: raise util.UserNotFound(action)

    elif action is None:
        if not transaction: raise util.NoActiveTrade()

async def update_trade(ctx:Context, transaction:db.Transaction, closed=False):
    member_1 = ctx.guild.get_member(transaction.user_1)
    member_2 = ctx.guild.get_member(transaction.user_2) if transaction.user_2 != 0 else client.user
    if transaction.message_id:
        msg = await ctx.channel.fetch_message(transaction.message_id)
        await msg.edit(
            content=f'{member_1.mention} {member_2.mention}',
            embed=transaction.get_embed(member_1.display_name, member_2.display_name, closed=closed)
        )
    else:
        msg = await ctx.send(
            content=f'{member_1.mention} {member_2.mention}',
            embed=transaction.get_embed(member_1.display_name, member_2.display_name, closed=closed)
        )
        db.transactions.set_transaction_message(transaction, msg.id)

async def resend_trade(ctx:Context, transaction:db.Transaction):
    transaction.message_id = None
    await update_trade(ctx, transaction)

async def trade_add(ctx:Context, transaction:db.Transaction, card:Union[int, str], amount:Union[int, str]):
    if not transaction: raise util.NoActiveTrade()
    if isinstance(amount, str) and amount != 'all':
        raise util.BadArgument('Amount', amount, message="Invalid value for {}: **{}**. If you're trying to add a card by name, make sure to put it in quotes.")
    if isinstance(amount, int) and amount < 1:
        raise util.BadArgument('Amount', amount)

    if transaction.locked: return

    added_cards = transaction.card_set(transaction.get_user(ctx.author.id))
    cards = db.query_from_inventory(ctx.author.id, ctx.guild.id, card, amount, exclude=added_cards)
    if cards:
        # Cannot add member cards to Discard trade
        if transaction.is_party(0) and any(c.definition.rarity == cfg.Rarity.MEMBER for c in cards):
            raise util.CleanException("Sorry, Member cards are not exchangeable.")

        transaction.add_cards(ctx.author.id, cards)
        db.session.commit()
        util.log.debug('[Trade] Added card instances to transaction: %s [%s]',
                       str(ctx.author), ', '.join('#'+str(c.card_id) for c in cards))
        await update_trade(ctx, transaction)
        return True

@client.command(aliases=['offer'])
@trade_channels()
async def add(ctx:Context, card:Union[int, str], amount:Union[int, str]=1):
    await ctx.message.delete(delay=1)
    transaction = db.transactions.get_active_transaction(ctx.author.id, ctx.guild.id)
    await trade_add(ctx, transaction, card, amount=amount)

@client.command(aliases=['remove'])
@trade_channels()
async def untrade(ctx:Context, card:Union[int, str], amount:Union[int, str]=1):
    await ctx.message.delete(delay=1)
    if isinstance(amount, str) and amount != 'all':
        raise util.BadArgument('Amount', amount, message="Invalid value for {}: **{}**. If you're trying to remove a card by name, make sure to put it in quotes.")
    if isinstance(amount, int) and amount < 1:
        raise util.BadArgument('Amount', amount)

    transaction = db.transactions.get_active_transaction(ctx.author.id, ctx.guild.id)
    if not transaction: raise util.NoActiveTrade()
    if transaction.locked: return

    cards = db.query_cards(transaction.card_set(ctx.author.id), card_filter=card)[:amount if amount != 'all' else None]
    if cards:
        transaction.remove_cards(ctx.author.id, cards)
        db.session.commit()
        util.log.debug('[Trade] Removed card instances from transaction: %s [%s]',
                       str(ctx.author), ', '.join('#'+str(c.card_id) for c in cards))
        await update_trade(ctx, transaction)

@client.command()
@trade_channels()
async def accept(ctx:Context):
    await ctx.message.delete(delay=1)

    transaction = db.transactions.get_active_transaction(ctx.author.id, ctx.guild.id)
    if not transaction: raise util.NoActiveTrade()
    if transaction.has_accepted(ctx.author.id): return

    transaction.set_accepted(ctx.author.id, True)
    util.log.debug('[Trade] %s has accepted the transaction.', str(ctx.author))

    # Discard
    if transaction.is_party(0):
        await discard_accept(ctx, transaction)
    db.session.commit()

    if transaction.complete:
        db.transactions.execute(transaction)
        util.log.info('[Trade] Transaction completed & executed. (accepted by %s)', str(ctx.author))
    await update_trade(ctx, transaction)

@client.command()
@trade_channels()
async def unaccept(ctx:Context):
    await ctx.message.delete(delay=1)

    transaction = db.transactions.get_active_transaction(ctx.author.id, ctx.guild.id)
    if not transaction: raise util.NoActiveTrade()
    if not transaction.has_accepted(ctx.author.id): return

    transaction.set_accepted(ctx.author.id, False)
    util.log.debug('[Trade] %s has unaccepted the transaction.', str(ctx.author))
    await update_trade(ctx, transaction)

@client.command(aliases=['close'])
@trade_channels()
async def cancel(ctx:Context):
    await ctx.message.delete(delay=1)

    transaction = db.transactions.close_active_transaction(ctx.author.id, ctx.guild.id)
    if transaction:
        member_1 = ctx.guild.get_member(transaction.user_1)
        member_2 = ctx.guild.get_member(transaction.user_2) if transaction.user_2 != 0 else client.user
        util.log.info('[Trade] Transaction closed between %s and %s', str(member_1), str(member_2))
        await update_trade(ctx, transaction, closed=True)
        await ctx.send(f"Trade between {member_1.display_name} and {member_2.display_name} has been closed.")
    else:
        raise util.NoActiveTrade()

@client.command(aliases=['exc', 'exchange'])
@trade_channels()
async def discard(ctx:Context, card:Union[int, str]=None, amount:Union[int, str]=1):
    await ctx.message.delete(delay=1)

    transaction = db.transactions.get_active_transaction(ctx.author.id, ctx.guild.id)
    if not transaction:
        transaction = db.transactions.open_transaction(ctx.author.id, 0, ctx.guild.id)
        util.log.info('[Trade] Transaction opened between %s and DisCard', str(ctx.author))
        await update_trade(ctx, transaction)
    elif not transaction.is_party(0):
        raise util.CleanException("You already have an active trade open. Please finish or cancel it before starting another one.")

    if card == 'resend':
        if not transaction: raise util.NoActiveTrade()
        await resend_trade(ctx, transaction)

    if card is not None:
        if not await trade_add(ctx, transaction, card, amount):
            raise util.NotInInventory(card)

async def discard_accept(ctx:Context, transaction:db.Transaction):
    offer = util.calculate_discard_offer(transaction.card_set(1))

    cards = []
    for rarity, count in offer.items():
        for i in range(count):
            if rarity == cfg.Rarity.EPIC:
                definition = db.spawner.get_random_definition_unique(ctx.guild.id, ctx.author.id, rarity=rarity)
            else:
                definition = db.spawner.get_random_definition(rarity=rarity)
            card = db.spawner.create_card_instance(definition, 0, 0, ctx.guild.id, owner_id='0')
            cards.append(str(card.id))
    transaction.cards_2 = ';'.join(cards) or None
    transaction.accepted_2 = True
    util.log.info('[Trade] Discard Transaction completed. Offer: %s', str(offer))


# --- Event Schedulers --- #

class CardIntervalSpawnTask(util.TaskLooper):
    def delay(self):
        variation = cfg.config['SPAWN_INTERVAL_VARIATION']
        delay = cfg.config['SPAWN_INTERVAL'] * (1 - (random.random() * variation * 2 - variation))

        now = pendulum.now('US/Eastern')
        time = now.add(seconds=delay)
        start, end = cfg.config['SPAWN_INTERVAL_START_TIME'], cfg.config['SPAWN_INTERVAL_END_TIME']
        if not start <= time.hour < end:
            time = time.set(hour=start, minute=0, second=0, microsecond=0)
            if not time > now:
                time = time.add(days=1)
            delay += (time - now).total_seconds()

        return delay

    async def run(self, guild:d.Guild):
        channel_id = random.choice(list(cfg.config['SPAWN_INTERVAL_CHANNELS'][guild.id]))
        await spawn(guild.get_channel(channel_id))

class CardEventGameTask(util.TaskLooper):
    def __init__(self, event_type=None):
        self.event_type = event_type

    def delay(self):
        now = pendulum.now('US/Eastern')

        start, end = cfg.config['SPAWN_INTERVAL_START_TIME'], cfg.config['SPAWN_INTERVAL_END_TIME']
        time = now.replace(hour=start, minute=0, second=0, microsecond=0)
        if time < now:
            time = time.add(days=1)
        sec_range = (end - start) * 60*60
        time = time.add(seconds=random.randrange(0, sec_range))

        return (time - now).total_seconds()

    async def run(self, guild:d.Guild):
        channel_id = random.choice(list(cfg.config['SPAWN_EVENT_GAME_CHANNELS'][guild.id]))
        await spawn_event(guild.get_channel(channel_id), self.event_type)

    def __str__(self):
        return super().__str__() + '[type=' + str(self.event_type) + ']'


# --- Main --- #

if __name__ == '__main__':
    with open('client_secret.txt', 'r') as secret:
        token = secret.read().strip()
    client.run(token)
    # db.Model.metadata.create_all(db.engine)
