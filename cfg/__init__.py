import datetime as dt

from .enums import *

config = dict(
    COMMAND_CHANNEL_ID = 766730238193041438,
    SPAWN_INTERVAL = 10*60,
    SPAWN_INTERVAL_CHANNEL_ID = 766730238193041438,
    SPAWN_INTERVAL_START_TIME = 9, # EST
    SPAWN_INTERVAL_END_TIME = 12, # EST
    SPAWN_MESSAGE_CHANCE = 1/25,
    CLAIM_COOLDOWN = 60,
    LAST_SPAWN = dt.datetime(2020, 10, 1),
    IMAGE_URL_BASE = 'https://drive.google.com/uc?export=download&id={}',
    HELP_URL = 'https://google.com',
    EMBED_AUTHOR = 'Cool Cids Cards',
    ITEMS_PER_PAGE = 15
)

def set_config(key, value, cast):
    config[key] = cast(value)
    return value, cast
