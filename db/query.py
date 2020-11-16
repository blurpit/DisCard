from operator import or_

from . import session
from .models import *


def query_card_amount(user_id, guild_id, card, amount, exclude=()):
    return session.query(Card) \
        .join(CardDefinition) \
        .filter(Card.guild_id == guild_id) \
        .filter(Card.owner_ids.endswith(str(user_id))) \
        .filter(or_(Card.card_id == card, func.lower(CardDefinition.name) == func.lower(card))) \
        .filter(Card.id.notin_(exclude)) \
        .order_by(Card.claim_timestamp.desc()) \
        .limit(amount if amount != 'all' else None) \
        .all()

def query_cards(card_ids, card_filter=None):
    q = session.query(Card).filter(Card.id.in_(card_ids))
    if isinstance(card_filter, int):
        q = q.filter_by(card_id=card_filter)
    elif isinstance(card_filter, str):
        q = q.join(CardDefinition).filter(func.lower(CardDefinition.name) == func.lower(card_filter))
    return q.all()

def query_card_map(card_ids):
    if not card_ids: return {}
    cards = session.query(Card.card_id, func.count(), CardDefinition) \
        .select_from(Card).join(CardDefinition) \
        .filter(Card.id.in_(card_ids)) \
        .group_by(Card.card_id) \
        .all()
    return {card_id: [count, definition] for card_id, count, definition in cards}

def query_rarity_map(card_ids):
    if not card_ids: return {}
    cards = session.query(CardDefinition.rarity, func.count()) \
        .select_from(Card).join(CardDefinition) \
        .filter(Card.id.in_(card_ids)) \
        .group_by(CardDefinition.rarity) \
        .all()
    return dict(cards)
