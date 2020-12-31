from enum import Enum


class Rarity(Enum):
    COMMON = ('Common', 4, 0.75, 1,  0,    20, 0xb86800)
    RARE   = ('Rare',   3, 0.18, 5,  0.75, 15, 0xffd900)
    EPIC   = ('Epic',   1, 0.05, 15, 0.25, 5,  0xba24ff)
    MEMBER = ('Member', 0, 0.02, 25, 0,    1,  0xff2b24)
    EVENT  = ('Event',  2, 0,    4,  0,    0,  0x00e8f0)

    def __init__(self, text, order, chance, weight, event_chance, pool, color):
        self.text = text
        self.order = order
        self.chance = chance
        self.weight = weight
        self.event_chance = event_chance
        self.pool = pool
        self.color = color
    def __repr__(self):
        return str(self)

class Expansion(Enum):
    BASE = 'Base'
    EX1  = 'Crucial Cards Collection'
    EX2  = 'Christmas Combat Crisis'
    EX3  = 'Media Mashup Madness'

    def __init__(self, text):
        self.text = text
    def __repr__(self):
        return str(self)

class Set(Enum):
    MEMBERS   = ('Members',           0,  769742920009252864, '<:MEMBERS:769742719165661215>')
    ICONS     = ('Icons',             1,  767845253847449640, '<:ICONS:769740679285964810>')
    TRICKCORD = ("Trick'cord Treat",  2,  767845285480366080, '<:TRICKCORD:769742193756733470>')
    RPI       = ('RPI',               3,  767845277003415612, '<:RPI:769740679818510336>')
    MEMES     = ('Memes',             4,  767845271551737901, '<:MEMES:769740679273775134>')
    GAMING    = ('Variety Gaming',    5,  767845287800078356, '<:GAMING:769740678673465373>')
    SMASH     = ('Super Smash Bros.', 6,  767845280607109160, '<:SMASH:769740679295270963>')
    SYSTEMS   = ('Game Systems',      7,  775857654118744115, '<:SYSTEMS:775861575889846333>')
    SIMIAN    = ('Simian',            8,  775857676427984946, '<:SIMIAN:775862931552075797>')
    GRADY     = ('Grady',             9,  775857721744031764, '<:GRADY:775861580977537074>')
    WINTER    = ('Winter Holiday',    10, 785737702955024444, '<:WINTER:784888230386204682>')
    POKEMON   = ('Pokémon',           11, 785737698606055435, '<:POKEMON:784888230645334098>')
    MINECRAFT = ('Minecraft',         12, 794047026614239232, '<:MINECRAFT:789961023183388682>')
    BRITISH   = ('British',           13, 794047032293064725, '<:BRITISH:789961022827790337>')
    YOUTUBER  = ('YouTubers',         14, 794047878372786196, '<:YOUTUBER:789961022927536168>')

    def __init__(self, text, order, image_id, badge):
        self.text = text
        self.order = order
        self.image_id = image_id
        self.badge = badge
    def __repr__(self):
        return str(self)

class EventCategory(Enum):
    XMAS = 0
    NEWYEAR = 1
    HALLOWEEN = 2

    def __repr__(self):
        return str(self)
