import datetime as dt

from .enums import *

config = dict(
    COMMAND_CHANNELS = {766730238193041438},
    SPAWN_EXCLUDE_CHANNELS = set(),
    SPAWN_INTERVAL = 10*60,
    SPAWN_INTERVAL_START_TIME = 9, # EST
    SPAWN_INTERVAL_END_TIME = 23, # EST
    SPAWN_INTERVAL_VARIATION = 0.2,
    SPAWN_MESSAGE_CHANCE = 1/25,
    CLAIM_COOLDOWN = 60,
    LAST_SPAWN = dt.datetime(2020, 10, 1),
    IMAGE_URL_BASE = 'https://cdn.discordapp.com/attachments/767822158294286387/{}/{}.png',
    HELP_URL = 'https://docs.google.com/document/d/1wYg8EPSKm8Ndum1659isF7ho8P-bPlJHRELrXENn1fs/edit?usp=sharing',
    EMBED_AUTHOR = 'Cool Cids Cards',
    ITEMS_PER_PAGE = 15
)

def set_config(key, value, cast):
    config[key] = cast(value)
    return value, cast
