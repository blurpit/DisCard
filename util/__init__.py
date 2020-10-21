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
        if card.card_id not in count:
            count[card.card_id] = [0, card.definition]
        count[card.card_id][0] += 1
    return count

def query_card_amount(user_id, guild_id, card, amount, exclude=()):
    return db.session.query(db.Card) \
        .join(db.CardDefinition) \
        .filter(db.Card.guild_id == guild_id) \
        .filter(db.Card.owner_ids.endswith(str(user_id))) \
        .filter(or_(db.Card.card_id == card, db.CardDefinition.name == card)) \
        .filter(db.Card.id.notin_(exclude)) \
        .order_by(db.Card.claim_timestamp.desc()) \
        .limit(amount if amount != 'all' else None) \
        .all()

def query_cards(card_ids, card_filter=None):
    q = db.session.query(db.Card).filter(db.Card.id.in_(card_ids))
    if isinstance(card_filter, int): q = q.filter_by(card_id=card_filter)
    elif isinstance(card_filter, str): q = q.join(db.CardDefinition).filter(db.CardDefinition.name == card_filter)
    return q.all()

def query_card_map(card_ids):
    if not card_ids: return {}
    cards = db.session.query(db.Card.card_id, func.count(), db.CardDefinition) \
        .select_from(db.Card).join(db.CardDefinition) \
        .filter(db.Card.id.in_(card_ids)) \
        .group_by(db.Card.card_id) \
        .all()
    return {card_id: [count, definition] for card_id, count, definition in cards}

def calculate_discard_offer(card_ids):
    # TODO: Implement discard offer
    return {cfg.Rarity.RARE: 2, cfg.Rarity.EPIC: 1}


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
