from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///data/testing.db')
Model = declarative_base()
Session = sessionmaker(bind=engine)
session = Session()

from .models import *


def query_inventory(member):
    return Inventory(
        member.id,
        session.query(Card).filter_by(owner_id=member.id).all()
    )

class Inventory:
    def __init__(self, discord_id, cards):
        self.discord_id = discord_id
        self.cards = cards

    def __getitem__(self, item):
        if isinstance(item, int):
            return d.utils.get(self.cards, id=item)
        else:
            return d.utils.get(self.cards, name=item)

    def __iter__(self):
        return iter(self.cards)

    def filter(self, **kwargs):
        """ Filter the inventory by certain attributes. Ex: inv.filter(set='Smash Bros.', rarity='Rare') """
        return filter(
            lambda c: all(getattr(c, attr) == kwargs[attr] for attr in kwargs),
            self.cards
        )

    def get_embed(self, client:d.Client):
        raise NotImplemented
