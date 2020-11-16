import math

from sqlalchemy import func, or_

import db
import cfg


def max_page(length):
    return max(int((length-1) // cfg.config['ITEMS_PER_PAGE']), 0)

def clamp(n, low=None, high=None):
    if low is None: low = -math.inf
    if high is None: high = math.inf
    return max(low, min(n, high))

def card_count_map(cards):
    """ Takes a list of Card instances and returns a mapping of
        card_id: [number of cards, CardDefinition] """
    count = {}
    for card in cards:
        # Card definition was deleted - probably a test card. Ignore it.
        if not card.definition: continue

        if card.card_id not in count:
            count[card.card_id] = [0, card.definition]
        count[card.card_id][0] += 1
    return count

def calculate_discard_offer(card_ids):
    result = {}

    weights = {
        'RARE': 3,
        'EPIC': 12
    }
    cost = 1/3

    rarities = db.query_rarity_map(card_ids)
    get = lambda r: rarities.get(r, 0)
    score = get(cfg.Rarity.COMMON) \
            + weights['RARE'] * get(cfg.Rarity.RARE) \
            + weights['EPIC'] * get(cfg.Rarity.EPIC)
    score = score * cost

    result[cfg.Rarity.EPIC] = int(score / weights['EPIC'])
    score %= weights['EPIC']

    result[cfg.Rarity.RARE] = int(score / weights['RARE'])
    score %= weights['RARE']

    result[cfg.Rarity.COMMON] = int(score)

    return result


class CleanException(Exception):
    """ CleanException messages will be sent as normal messages to the context """
    pass

class BadArgument(CleanException):
    def __init__(self, arg, val, message=None):
        if not message: message = "Invalid value for **{}**: '**{}**'"
        super().__init__(message.format(arg, val))

class NoActiveTrade(CleanException):
    def __init__(self, message=None):
        if not message: message = "You don't have an active trade open. Use **$trade @Example** to start trading."
        super().__init__(message)

class UserNotFound(CleanException):
    def __init__(self, user, message=None):
        if not message: message = "User not found: **{}**"
        super().__init__(message.format(user))

class NotInInventory(CleanException):
    def __init__(self, card, message=None):
        if not message: message = "You don't have **{}** in your inventory."
        super().__init__(message.format(card))
