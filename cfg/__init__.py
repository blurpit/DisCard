from .enums import *
import datetime as dt

ADMINISTRATORS = {426246773162639361, 416127116573278208}

config = dict(
    ENABLED_GUILDS = {
        687146032416555047, # Cool Cids Club
        # 693124716176736386, # Dumping Grounds
        # 768172182312058880  # Dumpster Fire
    },

    COMMAND_CHANNELS = { # Channels where regular commands are allowed
        687146032416555047: {767452299236474910}, # ccc-commands, main-chat
        693124716176736386: {766730238193041438}, # Dumping Grounds
        768172182312058880: {768172182312058884} # Dumpster Fire
    },
    TRADE_CHANNELS = { # Channels where trade commands are allowed
        687146032416555047: {767813524519911486}, # ccc-trades
        693124716176736386: {767876298310942720}, # Dumping Grounds
        768172182312058880: {768203474214191104} # Dumpster Fire
    },
    SPAWN_EXCLUDE_CHANNELS = { # Which channels cards should NOT be able to spawn in
        # ccc-commands, ccc-feedback, spam, nsfw, secret-mod-chat, secreter-bot-testing
        687146032416555047: {767452299236474910, 768193489585963048, 701264348860907582, 700426514436587541, 687165310054432805, 691763308059164722},
        693124716176736386: {767822158294286387, 767855584560939029}, # Dumping Grounds
        768172182312058880: set() # Dumpster Fire
    },
    SPAWN_EVENT_GAME_CHANNELS = { # Which channels card events can spawn
        687146032416555047: {687146032416555057}, # main-chat
        693124716176736386: {766730238193041438}, # Dumping Grounds
        768172182312058880: {768172182312058884} # Dumpster Fire
    },

    CLAIM_COOLDOWN = 5*60, # Cooldown (seconds) between allowed card claims

    SPAWN_INTERVAL = 37.5*60, # Time (seconds) between card spawns (0 to disable)
    SPAWN_INTERVAL_VARIATION=0.2,  # Percent variation for delay between spawns
    SPAWN_INTERVAL_START_TIME = 9, # EST time for when cards can start spawning
    SPAWN_INTERVAL_END_TIME = 23, # EST time for when cards stop spawning
    SPAWN_MESSAGE_CHANCE = 1/15, # Chance to spawn card on each message
    SPAWN_MESSAGE_COOLDOWN = 60, # Minimum time (seconds) between random message spawns
    SPAWN_MESSAGE_MAX_CONSECUTIVE = 5, # Maximum number of consecutive messages by the same user before cards no longer spawn

    SPAWN_EVENT_GAME_TIMES = [15], # EST times when card events should spawn

    SPAWN_EVENT_CARD_RATE = 1/5, # Chance to spawn an Event rarity card instead of regular cards
    ENABLED_EVENT_CARD_SETS = set(), # Which sets should spawn Event cards

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

def set_config(key, value, cast):
    config[key] = cast(value)
    return value, cast

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
