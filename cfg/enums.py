from enum import Enum


class Rarity(Enum):
    COMMON = ('Common', 4, 0.65, 1,  0,    20, 0xb86800)
    RARE   = ('Rare',   3, 0.25, 5,  0.75, 15, 0xffd900)
    EPIC   = ('Epic',   1, 0.05, 20, 0.25, 5,  0xba24ff)
    MEMBER = ('Member', 0, 0.05, 25, 0,    1,  0xff2b24)
    EVENT  = ('Event',  2, 0,    15, 0,    0,  0x00e8f0)

    def __init__(self, text, order, chance, weight, event_chance, pool, color):
        self.text = text
        self.order = order
        self.chance = chance
        self.weight = weight
        self.event_chance = event_chance
        self.pool = pool
        self.color = color

class Expansion(Enum):
    BASE = 'Base'

    def __init__(self, text):
        self.text = text

class Set(Enum):
    MEMBERS   = ('Members',           0, 769742920009252864, '<:MEMBERS:769742719165661215>')
    ICONS     = ('Icons',             1, 767845253847449640, '<:ICONS:769740679285964810>')
    TRICKCORD = ("Trick'cord Treat",  2, 767845285480366080, '<:TRICKCORD:769742193756733470>')
    RPI       = ('RPI',               3, 767845277003415612, '<:RPI:769740679818510336>')
    MEMES     = ('Memes',             4, 767845271551737901, '<:MEMES:769740679273775134>')
    GAMING    = ('Variety Gaming',    5, 767845287800078356, '<:GAMING:769740678673465373>')
    SMASH     = ('Super Smash Bros.', 6, 767845280607109160, '<:SMASH:769740679295270963>')

    def __init__(self, text, order, image_id, badge):
        self.text = text
        self.order = order
        self.image_id = image_id
        self.badge = badge
