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
    MEMBERS = ('Members', 0, '16Qa7A73L9POopG0FZ-961tDNwgVSbvZ5')
    ICONS = ('Icons', 1, '1k8ScqadP1MfigPJqWknbfB73HzoQzltK')
    TRICKCORD = ("Trick'cord Treat", 2, '1IL2Ya-0FrKh7rupBgjkE5HKD7qzBA2f_')
    RPI = ('RPI', 3, '1icF6hEXfHq5BYYb2jdDGq8fGhYGPqVcE')
    MEMES = ('Memes', 4, '19AVuAdLn7afettsuCBdQOoJOcknx8Icx')
    GAMING = ('Variety Gaming', 5, '1z4VJ8K6NOaQN5HMX7MJXNZw4IzAvw-mP')
    SMASH = ('Super Smash Bros.', 6, '1H_YmYYIB-vS5eC_Dr1Pl8otkfmGBi3_N')

    def __init__(self, text, order, drive_id):
        self.text, self.order, self.drive_id = text, order, drive_id

# class Type(Enum):
#     TODO: Card types
#     FIRE = ('Fire',)
