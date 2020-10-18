from enum import Enum


class Rarity(Enum):
    MEMBER = ('Member', 0, 0.05, 1, 0xff2b24)
    EPIC = ('Epic', 1, 0.05, 3, 0xba24ff)
    RARE = ('Rare', 2, 0.25, 15, 0xffd900)
    COMMON = ('Common', 3, 0.65, 40, 0x9aa9b5)

    def __init__(self, text, order, weight, pool, color):
        self.text, self.order, self.weight, self.pool, self.color = text, order, weight, pool, color

class Expansion(Enum):
    BASE = 'Base'

    def __init__(self, text):
        self.text = text

class Set(Enum):
    MEMBERS = ('Members', 0, 'members')
    ICONS = ('Icons', 1, 'icons')
    TRICKCORD = ("Trick'cord Treat", 2, 'trickcord')
    RPI = ('RPI', 3, 'rpi')
    MEMES = ('Memes', 4, 'memes')
    GAMING = ('Variety Gaming', 5, 'gaming')
    SMASH = ('Super Smash Bros.', 6, 'smash')

    def __init__(self, text, order, drive_id):
        self.text, self.order, self.filename = text, order, drive_id

# class Type(Enum):
#     TODO: Card types
#     FIRE = ('Fire',)
