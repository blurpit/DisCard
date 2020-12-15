import datetime as dt
import random

from sqlalchemy import or_

from . import *


def get_definition(guild_id, card=None, rarity=None):
    if card is None:
        if cfg.config['ENABLED_EVENT_CARD_CATEGORIES'] and random.random() < cfg.config['EVENT_CARD_SPAWN_RATE']:
            return get_random_definition(rarity=cfg.Rarity.EVENT)

        used = dict(session.query(Card.card_id, func.count()) \
            .select_from(Card).join(CardDefinition) \
            .filter(CardDefinition.rarity != cfg.Rarity.EVENT) \
            .filter(Card.owner_ids != None) \
            .filter(not_(Card.owner_ids.endswith(';0')))
            .filter(Card.guild_id == guild_id) \
            .group_by(CardDefinition.id) \
            .order_by(CardDefinition.id) \
            .all())
        definitions = session.query(CardDefinition).all()

        pools = {}
        for definition in definitions:
            r = definition.rarity
            pool = r.pool
            if used.get(definition.id, 0) > 0:
                pool = max(0, pool - used[definition.id])
            if pool > 0:
                if r not in pools:
                    pools[r] = {}
                pools[r][definition.id] = (pool, definition)

        if pools:
            r = rarity or random.choices(list(pools.keys()), weights=[r.chance for r in pools])[0]
            if r in pools:
                return random.choice(list(pools[r].values()))[1]
    else:
        if isinstance(card, int):
            return session.query(CardDefinition).filter_by(id=card).one_or_none()
        elif isinstance(card, str):
            return session.query(CardDefinition).filter_by(name=card).one_or_none()

def get_random_definition(card_set=None, rarity=None):
    q = session.query(CardDefinition)
    if card_set is not None:
        q = q.filter_by(set=card_set)
    if rarity is not None:
        q = q.filter_by(rarity=rarity)
    return q.filter(or_(CardDefinition.rarity != cfg.Rarity.EVENT,
                        CardDefinition.event_category.in_(cfg.config['ENABLED_EVENT_CARD_CATEGORIES']))) \
        .order_by(func.random()) \
        .first()

def create_card_instance(definition, message_id, channel_id, guild_id, owner_id=None):
    card = Card(
        card_id=definition.id,
        owner_ids=owner_id,
        spawn_timestamp=dt.datetime.utcnow(),
        claim_timestamp=None if not owner_id else dt.datetime(1970, 1, 1),
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

    latest_claim = session.query(Card.claim_timestamp, CardDefinition.rarity) \
        .select_from(Card) \
        .join(CardDefinition) \
        .filter(Card.guild_id == guild_id) \
        .filter(Card.owner_ids == str(user_id)) \
        .order_by(Card.claim_timestamp.desc()) \
        .first()

    if latest_claim:
        now = dt.datetime.utcnow()
        timestamp = (now - latest_claim[0]).total_seconds()
        cooldown = cfg.config['CLAIM_COOLDOWN'][latest_claim[1]]
        if timestamp < cooldown:
            remaining = cooldown - timestamp
            raise util.CleanException('Claim cooldown: **{:d}m {:d}s**'.format(int(remaining // 60), int(remaining % 60)))

    card.owner_id = user_id
    card.claim_timestamp = dt.datetime.utcnow()
    session.commit()
    return card
