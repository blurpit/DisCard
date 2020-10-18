from typing import Iterable

import discord as d
from discord.ext.commands import Context
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship

import cfg
from . import Model, session


class CardDefinition(Model):
    __tablename__ = 'definitions'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    rarity = Column(Enum(cfg.Rarity), nullable=False)
    set = Column(Enum(cfg.Set), nullable=False)
    expansion = Column(Enum(cfg.Expansion), nullable=False)
    drive_id = Column(Text, nullable=True)
    description = Column(Text, nullable=False)
    # type = Column(Enum(cfg.CardType), nullable=False)

    instances:Iterable = relationship('Card', backref='definition')

    def get_embed(self):
        embed = d.Embed()

        embed.title = f'[#{self.id}] {self.name}'
        embed.url = 'https://google.com'
        embed.colour = d.Color(self.rarity.color)
        embed.description = self.description
        embed.set_author(name=f'Cool Cids Cards')
        embed.set_footer(text=f'This card is unclaimed! Use $claim to claim it!')
        embed.add_field(name='Set', value=f'[{self.expansion.text}] {self.set.text}')
        embed.add_field(name='Rarity', value=self.rarity.text)
        embed.set_thumbnail(url=cfg.config['IMAGE_URL_BASE'].format(self.set.drive_id))
        if self.drive_id is not None:
            embed.set_image(url=cfg.config['IMAGE_URL_BASE'].format(self.drive_id))
        else:
            embed.add_field(name='(No Image)', value='Images pls max', inline=False)

        return embed

    def __repr__(self):
        return "CardDefinition({0.id}, {0.name}, {0.drive_id}, {0.description}, " \
               "{0.expansion}, {0.set}, {0.rarity})".format(self)

    def string(self, count=1):
        return "[#{0.id}] **{0.name}**: _{0.set.text}_ ({0.rarity.text}) x {1}".format(self, count)

class Card(Model):
    __tablename__ = 'cards'

    id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey(CardDefinition.id), nullable=False)
    owner_id = Column(Integer, nullable=True)
    spawn_timestamp = Column(DateTime, nullable=False)
    claim_timestamp = Column(DateTime, nullable=True)
    message_id = Column(Integer, nullable=False)

    def get_embed(self, ctx:Context, preview=False, count=1):
        embed:d.Embed = self.definition.get_embed()

        if self.owner_id is not None:
            if preview: embed.title = '[Preview] ' + embed.title
            else: embed.title = ':white_check_mark: ' + embed.title

            name = ctx.guild.get_member(self.owner_id).display_name

            if preview:
                if count == 1: text = f'You own 1 copy of this card.'
                else: text = f'You own {count} copies of this card.'
            else:
                text=f'Claimed by {name}!'
            embed.set_footer(text=text)

        return embed

    def __repr__(self):
        return "Card({0.id}, {0.card_id}, {0.owner_id}, {0.spawn_timestamp}, " \
               "{0.message_id})".format(self)

class Inventory:
    def __init__(self, discord_id):
        self.discord_id = discord_id
        self.inv = {}
        self.cards = session.query(Card).filter_by(owner_id=discord_id).all()
        # {card_id: [card count, card definition]
        for card in self.cards:
            if card.card_id not in self.inv:
                self.inv[card.card_id] = [1, card.definition]
            else:
                self.inv[card.card_id][0] += 1
        self.max_page = max(int((len(self.inv)-1) // cfg.config['ELEMENTS_PER_PAGE']), 0)

    def __getitem__(self, item):
        if isinstance(item, int):
            return d.utils.get(self.cards, card_id=item)
        elif isinstance(item, str):
            return d.utils.get(self.cards, name=item)

    def __iter__(self):
        return iter(self.cards)

    def __len__(self):
        """ Number of unique cards """
        return len(self.cards)

    def __contains__(self, card_id):
        return card_id in self.inv

    def filter(self, **kwargs):
        """ Filter the inventory by certain attributes. Ex: inv.filter(set=Set.SMASH, rarity=Rarity.RARE) """
        return filter(
            lambda c: all(getattr(c, attr) == kwargs[attr] for attr in kwargs),
            self.cards
        )

    def count(self, card_id):
        return self.inv[card_id][0]

    def get_embed(self, user:d.Member, page):
        elements = cfg.config['ELEMENTS_PER_PAGE']
        page = max(0, min(page, self.max_page)) # Clamp pages to between 0 and the number of allowed pages

        embed = d.Embed()
        embed.set_author(name=f'Cool Cids Cards')
        embed.set_footer(text=f'Page {page+1}/{self.max_page + 1}')
        embed.title = f"{user.display_name}'s Card Collection"

        definitions = sorted(
            self.inv.values(),
            key=lambda val: (val[1].set.order, val[1].rarity.order, val[1].id)
        )
        embed.description = f'You own {len(self)} cards!\n\n• '
        embed.description += '\n• '.join(
            definition.string(count)
            for count, definition in definitions[elements*page:elements*(page+1)]
        )

        embed.url = 'https://google.com'
        embed.colour = d.Color.blue()
        return embed
