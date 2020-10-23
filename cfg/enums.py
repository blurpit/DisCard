from enum import Enum


class Rarity(Enum):
    COMMON = ('Common', 3, 0.65, 1,  0,    20, 0x9aa9b5)
    RARE   = ('Rare',   2, 0.25, 5,  0.75, 15, 0xffd900)
    EPIC   = ('Epic',   1, 0.05, 20, 0.25, 5,  0xba24ff)
    MEMBER = ('Member', 0, 0.05, 25, 0,    1,  0xff2b24)

    def __init__(self, text, order, chance, weight, event_weight, pool, color):
        self.text = text
        self.order = order
        self.chance = chance
        self.weight = weight
        self.event_weight = event_weight
        self.pool = pool
        self.color = color

class Expansion(Enum):
    BASE = 'Base'

    def __init__(self, text):
        self.text = text

class Set(Enum):
    MEMBERS   = ('Members',           0, 767845266224578640)
    ICONS     = ('Icons',             1, 767845253847449640)
    TRICKCORD = ("Trick'cord Treat",  2, 767845285480366080)
    RPI       = ('RPI',               3, 767845277003415612)
    MEMES     = ('Memes',             4, 767845271551737901)
    GAMING    = ('Variety Gaming',    5, 767845287800078356)
    SMASH     = ('Super Smash Bros.', 6, 767845280607109160)

    def __init__(self, text, order, image_id):
        self.text = text
        self.order = order
        self.image_id = image_id

# class Type(Enum):
#     TODO: Card types
#     FIRE = ('Fire',)
