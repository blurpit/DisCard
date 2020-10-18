import datetime as dt

from .enums import *

config = dict(
    COMMAND_CHANNEL_ID = 766730238193041438,
    SPAWN_COOLDOWN = 10*60,
    SPAWN_MESSAGE_CHANCE = 1/25,
    CLAIM_COOLDOWN = 15*60,
    LAST_SPAWN = dt.datetime(1970, 1, 1),
    IMAGE_URL_BASE = 'https://drive.google.com/uc?export=download&id={}'
)

def set_config(key, value, cast):
    config[key] = cast(value)
    return value, cast
