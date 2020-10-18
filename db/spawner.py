import datetime as dt
import random

from . import *


def get_definition(card_id=None):
    if card_id is None:
        row = random.randrange(0, session.query(CardDefinition).count())
        return session.query(CardDefinition)[row]
    else:
        return session.query(CardDefinition).filter_by(id=card_id).one_or_none()

def create_card_instance(definition, message_id):
    session.add(Card(
        card_id=definition.id,
        owner_id=None,
        spawn_timestamp=dt.datetime.utcnow(),
        message_id=message_id
    ))
    session.commit()

def claim(member):
    latest_claim = session.query(Card.claim_timestamp) \
        .filter_by(owner_id=member.id) \
        .filter(Card.claim_timestamp != None) \
        .order_by(Card.claim_timestamp.desc()) \
        .first()

    if latest_claim:
        delta = (dt.datetime.utcnow() - latest_claim[0])
        if delta.total_seconds() < cfg.config['CLAIM_COOLDOWN']:
            return delta

    card = session.query(Card) \
        .filter(Card.owner_id == None) \
        .order_by(Card.spawn_timestamp.desc()) \
        .first()

    if card is not None:
        card.owner_id = member.id
        card.claim_timestamp = dt.datetime.utcnow()
        session.commit()
        return card
