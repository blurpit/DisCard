import datetime as dt
import random

from sqlalchemy import func

from . import *


def get_definition(card=None):
    if card is None:
        pools = {}
        q = session.query(CardDefinition.rarity, CardDefinition, func.count()) \
            .select_from(Card).join(CardDefinition) \
            .group_by(CardDefinition.id) \
            .order_by(CardDefinition.id)

        for rarity, definition, count in q.all():
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

def get_random_definition():
    rand = random.randrange(0, session.query(CardDefinition.id).count())
    return session.query(CardDefinition)[rand]

def create_card_instance(definition, message_id, channel_id, guild_id):
    card = Card(
        card_id=definition.id,
        owner_ids=None,
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
