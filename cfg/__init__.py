from .enums import *
import datetime as dt

ADMINISTRATORS = {426246773162639361, 416127116573278208}

config = dict(
    ENABLED_GUILDS = {
        687146032416555047, # Cool Cids Club
        # 693124716176736386, # Dumping Grounds
        # 768172182312058880  # Dumpster Fire
    },
    LOG_CHANNEL = 772548035616047110,

    COMMAND_CHANNELS = { # Channels where regular commands are allowed
        687146032416555047: {767452299236474910}, # ccc-commands
        693124716176736386: {766730238193041438}, # Dumping Grounds
        768172182312058880: {768172182312058884} # Dumpster Fire
    },
    TRADE_CHANNELS = { # Channels where trade commands are allowed
        687146032416555047: {767813524519911486}, # ccc-trades
        693124716176736386: {767876298310942720}, # Dumping Grounds
        768172182312058880: {768203474214191104} # Dumpster Fire
    },
    SPAWN_INTERVAL_CHANNELS = { # Which channels cards should NOT be able to spawn in
        # main-chat, ideas-for-the-server, voice-text-channel, memes-and-videos, games, minecraft, destiny-2, music
        687146032416555047: {781599858858917918},
        693124716176736386: {766730238193041438, 693124716176736389}, # Dumping Grounds
        768172182312058880: {768172182312058884} # Dumpster Fire
    },
    SPAWN_MESSAGE_CHANNELS = {
        # main-chat, ideas-for-the-server, voice-text-channel, memes-and-videos, games, minecraft, destiny-2, music
        687146032416555047: {687146032416555057, 687151973463883778, 700516725044805652,
                             687152279895408661, 687152338011815966, 689254144502268089,
                             690936793247252531, 687154101611528200},
        693124716176736386: {766730238193041438, 693124716176736389}, # Dumping Grounds
        768172182312058880: {768172182312058884} # Dumpster Fire
    },
    SPAWN_EVENT_GAME_CHANNELS = { # Which channels card events can spawn
        687146032416555047: {687146032416555057}, # main-chat
        693124716176736386: {766730238193041438}, # Dumping Grounds
        768172182312058880: {768172182312058884} # Dumpster Fire
    },

    CLAIM_COOLDOWN = { # Cooldown (seconds) between allowed card claims
        Rarity.COMMON: 5*60,
        Rarity.RARE: 25*60,
        Rarity.EPIC: 60*60,
        Rarity.MEMBER: 4*60*60,
        Rarity.EVENT: 10*60
    },

    SPAWN_INTERVAL = 37.5*60, # Time (seconds) between card spawns (0 to disable)
    SPAWN_INTERVAL_VARIATION = 0.2,  # Percent variation for delay between spawns
    SPAWN_INTERVAL_START_TIME = 9, # EST time for when cards can start spawning
    SPAWN_INTERVAL_END_TIME = 23, # EST time for when cards stop spawning
    SPAWN_MESSAGE_CHANCE = 1/30, # Chance to spawn card on each message
    SPAWN_MESSAGE_COOLDOWN = 5*60, # Minimum time (seconds) between random message spawns
    SPAWN_MESSAGE_MAX_CONSECUTIVE = 5, # Maximum number of consecutive messages by the same user before cards no longer spawn

    EVENT_CARD_SPAWN_RATE = 1/5, # Chance to spawn an Event rarity card instead of regular cards
    ENABLED_EVENT_CARD_CATEGORIES = set(), # Which categories should spawn Event cards
    HANGMAN_CHUNGUS_USER = None, # Chungus easter egg for hangman
    HANGMAN_CHUNGUS_LETTERS = 'CHUNGUS', # Letters to use in chungus easter egg for hangman

    REMOVE_IMAGE_AFTER_CLAIM = True,
    ITEMS_PER_PAGE = 15, # Number of items that appear before wrapping to the next page
    IMAGE_URL_BASE = 'https://cdn.discordapp.com/attachments/767822158294286387/{}/{}.png', # Base URL for card images
    HELP_URL = 'https://docs.google.com/document/d/1wYg8EPSKm8Ndum1659isF7ho8P-bPlJHRELrXENn1fs/edit?usp=sharing', # URL link to help page
    EMBED_AUTHOR = 'Cool Cids Cards' # Author text for all embeds
)

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

# Time since last random card spawn
last_spawn = dt.datetime(1970, 1, 1)
consecutive_messages = [0, 0]

def set_config(key, value):
    if value.lower() in ('true', 'false'):
        value = value == 'true'
    elif value.lower() == 'none':
        value = None
    else:
        try:
            value = float(value)
            if value % 1 == 0:
                value = int(value)
        except ValueError:
            pass
    config[key] = value
    return value

def add_consecutive_message(user_id):
    """ Adds 1 to the number of consecutive messages for this user, or sets it to 1 if """
    if config['SPAWN_MESSAGE_MAX_CONSECUTIVE'] > 0:
        if consecutive_messages[0] == user_id:
            consecutive_messages[1] += 1
        else:
            consecutive_messages[0] = user_id
            consecutive_messages[1] = 1
    else:
        # If max consecutive is 0 or None, disable the check
        consecutive_messages[1] = 0
