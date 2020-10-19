import datetime as dt
import random

from . import *


def get_definition(card_id=None):
    if card_id is None:
        row = random.randrange(0, session.query(CardDefinition).count())
        return session.query(CardDefinition)[row]
    else:
        return session.query(CardDefinition).filter_by(id=card_id).one_or_none()

def create_card_instance(definition, message_id, channel_id):
    session.add(Card(
        card_id=definition.id,
        owner_ids=None,
        spawn_timestamp=dt.datetime.utcnow(),
        message_id=message_id,
        channel_id=channel_id
    ))
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
        .filter(Card.owner_ids.endswith(str(user_id))) \
        .filter(Card.claim_timestamp != None) \
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
