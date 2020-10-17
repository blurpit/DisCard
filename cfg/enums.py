from enum import Enum


class Rarity(Enum):
    COMMON = ('Common', 65, 0x9aa9b5)
    RARE = ('Rare', 25, 0xffd900)
    EPIC = ('Epic', 5, 0xba24ff)
    MEMBER = ('Member', 5, 0xff2b24)

    def __init__(self, text, weight, color):
        self.text, self.weight, self.color = text, weight, color

class Expansion(Enum):
    BASE = 'Base'

    def __init__(self, text):
        self.text = text

class Set(Enum):
    MEMBERS = ('Members', 'members')
    ICONS = ('Icons', 'icons')
    TRICKCORD = ("Trick'cord Treat", 'trickcord')
    RPI = ('RPI', 'rpi')
    MEMES = ('Memes', 'memes')
    GAMING = ('Variety Gaming', 'gaming')
    SMASH = ('Super Smash Bros.', 'smash')

    def __init__(self, text, filename):
        self.text, self.filename = text, filename

# class Type(Enum):
#     TODO: Card types
#     FIRE = ('Fire',)
