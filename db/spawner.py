import datetime as dt
import random

from . import *


def random_definition():
    row = random.randrange(0, session.query(CardDefinition).count())
    return session.query(CardDefinition)[row]

def create_card_instance(definition, message):
    session.add(Card(
        card_id=definition.id,
        owner_id=None,
        spawn_timestamp=dt.datetime.utcnow(),
        message_id=message.id
    ))
    session.commit()

def claim(member):
    card = session.query(Card) \
        .filter(Card.owner_id == None) \
        .order_by(Card.spawn_timestamp.desc()) \
        .first()

    if card is not None:
        card.owner_id = member.id
        session.commit()
        return card
