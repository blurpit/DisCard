from .enums import *

config = dict(
    COMMAND_CHANNELS = {
        693124716176736386: {766730238193041438}, # Dumping Grounds
        768172182312058880: {768172182312058884} # Dump2
    },
    TRADE_CHANNELS = {
        693124716176736386: {767876298310942720}, # Dumping Grounds
        768172182312058880: {768203474214191104} # Dump2
    },
    SPAWN_EXCLUDE_CHANNELS = {
        693124716176736386: {767822158294286387, 767855584560939029}, # Dumping Grounds
        768172182312058880: set()
    },
    SPAWN_INTERVAL = 0,
    SPAWN_INTERVAL_START_TIME = 9, # EST
    SPAWN_INTERVAL_END_TIME = 23, # EST
    SPAWN_INTERVAL_VARIATION = 0.2,
    SPAWN_MESSAGE_CHANCE = 0,
    CLAIM_COOLDOWN = 0,
    IMAGE_URL_BASE = 'https://cdn.discordapp.com/attachments/767822158294286387/{}/{}.png',
    HELP_URL = 'https://docs.google.com/document/d/1wYg8EPSKm8Ndum1659isF7ho8P-bPlJHRELrXENn1fs/edit?usp=sharing',
    EMBED_AUTHOR = 'Cool Cids Cards',
    ITEMS_PER_PAGE = 15
)

def set_config(key, value, cast):
    config[key] = cast(value)
    return value, cast
