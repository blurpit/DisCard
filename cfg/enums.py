from enum import Enum


class Rarity(Enum):
    COMMON = ('Common', 4, 0.65, 1,  0,    20, 0xb86800)
    RARE   = ('Rare',   3, 0.25, 5,  0.75, 15, 0xffd900)
    EPIC   = ('Epic',   1, 0.05, 20, 0.25, 5,  0xba24ff)
    MEMBER = ('Member', 0, 0.05, 25, 0,    1,  0xff2b24)
    EVENT  = ('Event',  2, 0,    15, 0,    0,  0x00e8f0)

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
    TEST = 'Test'

    def __init__(self, text):
        self.text = text

class Set(Enum):
    MEMBERS   = ('Members',           1, 767845266224578640)
    ICONS     = ('Icons',             2, 767845253847449640)
    TRICKCORD = ("Trick'cord Treat",  3, 767845285480366080)
    RPI       = ('RPI',               4, 767845277003415612)
    MEMES     = ('Memes',             5, 767845271551737901)
    GAMING    = ('Variety Gaming',    6, 767845287800078356)
    SMASH     = ('Super Smash Bros.', 7, 767845280607109160)
    TESTSET   = ('Testing',           0, 767845280607109160)

    def __init__(self, text, order, image_id):
        self.text = text
        self.order = order
        self.image_id = image_id

# class Type(Enum):
#     TODO: Card types
#     FIRE = ('Fire',)
