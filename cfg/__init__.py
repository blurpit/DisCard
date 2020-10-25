from .enums import *
import datetime as dt

ADMINISTRATORS = {426246773162639361, 416127116573278208}

config = dict(
    COMMAND_CHANNELS = { # Channels where regular commands are allowed
        693124716176736386: {766730238193041438}, # Dumping Grounds
        768172182312058880: {768172182312058884} # Dumpster Fire
    },
    TRADE_CHANNELS = { # Channels where trade commands are allowed
        693124716176736386: {767876298310942720}, # Dumping Grounds
        768172182312058880: {768203474214191104} # Dumpster Fire
    },
    SPAWN_EXCLUDE_CHANNELS = { # Which channels cards should NOT be able to spawn in
        693124716176736386: {767822158294286387, 767855584560939029}, # Dumping Grounds
        768172182312058880: set() # Dumpster Fire
    },
    SPAWN_EVENT_GAME_CHANNELS = { # Which channels card events can spawn
        693124716176736386: {766730238193041438}, # Dumping Grounds
        768172182312058880: {768172182312058884} # Dumpster Fire
    },

    CLAIM_COOLDOWN = 5*60, # Cooldown (seconds) between allowed card claims

    SPAWN_INTERVAL = 37.5*60, # Time (seconds) between card spawns (0 to disable)
    SPAWN_INTERVAL_START_TIME = 9, # EST time for when cards can start spawning
    SPAWN_INTERVAL_END_TIME = 23, # EST time for when cards stop spawning
    SPAWN_INTERVAL_VARIATION = 0.2, # Percent variation for delay between spawns
    SPAWN_MESSAGE_CHANCE = 1/15, # Chance to spawn card on each message
    SPAWN_MESSAGE_COOLDOWN = 60,

    SPAWN_EVENT_GAME_TIMES = [16], # EST times when card events should spawn

    SPAWN_EVENT_CARD_RATE = 1/4, # Chance to spawn an Event rarity card instead of regular cards
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

last_spawn = dt.datetime(1970, 1, 1)

def set_config(key, value, cast):
    config[key] = cast(value)
    return value, cast
