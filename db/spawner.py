import datetime as dt
import random

from sqlalchemy import func

from . import *


def get_definition(card=None):
    if card is None:
        # Mapping from Rarity to the total pool amount for that rarity
        pools = session.query(CardDefinition.rarity, func.count(CardDefinition.id)) \
            .group_by(CardDefinition.rarity) \
            .all()
        pools = {rarity: count*rarity.pool for rarity, count in pools}

        # Mapping from Rarity to the number of cards of that rarity that have been claimed
        used = session.query(CardDefinition.rarity, func.count(Card.id)) \
            .join(CardDefinition) \
            .filter(not_(Card.owner_ids.endswith(';0'))) \
            .group_by(CardDefinition.rarity) \
            .all()
        used = dict(used)

        pools = {rarity: count-used[rarity] for rarity, count in pools.items() if pools[rarity] > used[rarity] }
        if pools:
            rarity = random.choices(list(pools.keys()), weights=[r.chance for r in pools])[0]
            return session.query(CardDefinition).filter_by(rarity=rarity).order_by(func.random()).first()
    else:
        if isinstance(card, int):
            return session.query(CardDefinition).filter_by(id=card).one_or_none()
        elif isinstance(card, str):
            return session.query(CardDefinition).filter_by(name=card).one_or_none()

def create_card_instance(definition, message_id, channel_id, guild_id):
    session.add(Card(
        card_id=definition.id,
        owner_ids=None,
        spawn_timestamp=dt.datetime.utcnow(),
        message_id=message_id,
        channel_id=channel_id,
        guild_id=guild_id
    ))
    session.commit()

def delete_card_instance(card):
    if isinstance(card, Card): session.delete(card)
    else: session.query(Card).filter_by(id=card).delete()
    session.commit()

def claim(user_id, channel_id):
    card = session.query(Card) \
        .filter_by(channel_id=channel_id) \
        .filter(Card.owner_ids == None) \
        .order_by(Card.spawn_timestamp.desc()) \
        .first()

    if not card:
        return None

    latest_claim = session.query(Card.claim_timestamp) \
        .filter(Card.owner_ids == str(user_id)) \
        .order_by(Card.claim_timestamp.desc()) \
        .first()

    if latest_claim:
        delta = (dt.datetime.utcnow() - latest_claim[0])
        if delta.total_seconds() < cfg.config['CLAIM_COOLDOWN']:
            return delta

    card.owner_id = user_id
    card.claim_timestamp = dt.datetime.utcnow()
    session.commit()
    return card
