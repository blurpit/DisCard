import datetime as dt
import random

from sqlalchemy import func, or_

from . import *


def get_definition(card=None):
    if card is None:
        if cfg.config['ENABLED_EVENT_CARD_SETS'] and random.random() < cfg.config['SPAWN_EVENT_CARD_RATE']:
            return get_random_definition(rarity=cfg.Rarity.EVENT)

        pools = {}
        q = session.query(CardDefinition, func.count()) \
            .select_from(Card).join(CardDefinition) \
            .filter(CardDefinition.rarity != cfg.Rarity.EVENT) \
            .group_by(CardDefinition.id) \
            .order_by(CardDefinition.id)

        for definition, count in q.all():
            rarity = definition.rarity
            pool = rarity.pool - count
            if pool > 0:
                if rarity not in pools:
                    pools[rarity] = {}
                pools[rarity][definition.id] = (pool, definition)

        if pools:
            r = random.choices(list(pools.keys()), weights=[r.chance for r in pools])[0]
            return random.choice(list(pools[r].values()))[1]
    else:
        if isinstance(card, int):
            return session.query(CardDefinition).filter_by(id=card).one_or_none()
        elif isinstance(card, str):
            return session.query(CardDefinition).filter_by(name=card).one_or_none()

def get_random_definition(card_set=None, rarity=None):
    return session.query(CardDefinition) \
        .filter(or_(card_set is None, CardDefinition.set == card_set)) \
        .filter(or_(rarity is None, CardDefinition.rarity == rarity)) \
        .filter(or_(CardDefinition.rarity != cfg.Rarity.EVENT, CardDefinition.set.in_(cfg.config['ENABLED_EVENT_CARD_SETS']))) \
        .order_by(func.random()) \
        .first()

def create_card_instance(definition, message_id, channel_id, guild_id, owner_id=None):
    card = Card(
        card_id=definition.id,
        owner_ids=owner_id,
        spawn_timestamp=dt.datetime.utcnow(),
        message_id=message_id,
        channel_id=channel_id,
        guild_id=guild_id
    )
    session.add(card)
    session.commit()
    return card

def delete_card_instance(card):
    if isinstance(card, Card): session.delete(card)
    else: session.query(Card).filter_by(id=card).delete()
    session.commit()

def claim(user_id, channel_id, guild_id):
    card = session.query(Card) \
        .filter_by(channel_id=channel_id) \
        .filter_by(guild_id=guild_id) \
        .filter(Card.owner_ids == None) \
        .order_by(Card.spawn_timestamp.desc()) \
        .first()

    if not card:
        return None

    latest_claim = session.query(Card.claim_timestamp) \
        .filter_by(guild_id=guild_id) \
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
