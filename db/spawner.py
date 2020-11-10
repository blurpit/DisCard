import datetime as dt
import random

from sqlalchemy import func, or_

from . import *


def get_definition(guild_id, card=None):
    if card is None:
        if cfg.config['ENABLED_EVENT_CARD_SETS'] and random.random() < cfg.config['SPAWN_EVENT_CARD_RATE']:
            return get_random_definition(rarity=cfg.Rarity.EVENT)

        pools = {r: {} for r in cfg.Rarity}
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

        for definition in definitions:
            rarity = definition.rarity
            pool = rarity.pool
            if used.get(definition.id, 0) > 0:
                pool = max(0, pool - used[definition.id])
            if pool > 0:
                pools[rarity][definition.id] = (pool, definition)

        if any(any(pools[r][card][0] > 0 for card in pools[r]) for r in pools):
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

    claims = session.query(Card.claim_timestamp) \
        .filter_by(guild_id=guild_id) \
        .filter(Card.owner_ids == str(user_id)) \
        .order_by(Card.claim_timestamp.desc()) \
        .limit(cfg.config['CLAIM_LIMIT']) \
        .all()

    if claims:
        now = dt.datetime.utcnow()
        latest = (now - claims[0][0]).total_seconds()
        oldest = (now - claims[-1][0]).total_seconds()
        if latest < cfg.config['CLAIM_COOLDOWN']:
            remaining = cfg.config['CLAIM_COOLDOWN'] - latest
            raise util.CleanException('Claim cooldown: **{:d}m {:d}s**'
                                      .format(int(remaining // 60), int(remaining % 60)))
        if len(claims) >= cfg.config['CLAIM_LIMIT'] and oldest < cfg.config['CLAIM_LIMIT_PERIOD']:
            remaining = cfg.config['CLAIM_LIMIT_PERIOD'] - oldest
            raise util.CleanException('Claim limit reached! You can claim again in: **{:d}h {:d}m {:d}s**'
                                      .format(int(remaining // 3600), int(remaining // 60 % 60), int(remaining % 60)))

    card.owner_id = user_id
    card.claim_timestamp = dt.datetime.utcnow()
    session.commit()
    return card
