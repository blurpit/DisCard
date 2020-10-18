from typing import Iterable

import discord as d
from discord.ext.commands import Context
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship

import cfg
from . import Model


class CardDefinition(Model):
    __tablename__ = 'definitions'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    drive_id = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    expansion = Column(Enum(cfg.Expansion), nullable=False)
    set = Column(Enum(cfg.Set), nullable=False)
    rarity = Column(Enum(cfg.Rarity), nullable=False)
    # type = Column(Enum(cfg.CardType), nullable=False)

    instances:Iterable = relationship('Card', backref='definition')

    def get_embed(self):
        embed = d.Embed()
        # embed.set_thumbnail()
        embed.set_image(url=cfg.config['IMAGE_URL_BASE'].format(self.drive_id))
        embed.set_author(name=f'Cool Cids Cards')
        embed.set_footer(text=f'This item is unclaimed! Use $claim to claim it!')
        embed.add_field(name='Set', value=f'[{self.expansion.text}] {self.set.text}')
        embed.add_field(name='Rarity', value=self.rarity.text)
        embed.description = self.description
        embed.title = f'[#{self.id}] {self.name}'
        embed.url = 'https://google.com'
        embed.colour = d.Color(self.rarity.color)
        return embed

    def __repr__(self):
        return "CardDefinition({0.id}, {0.name}, {0.drive_id}, {0.description}, " \
               "{0.expansion}, {0.set}, {0.rarity})".format(self)

class Card(Model):
    __tablename__ = 'cards'

    id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey(CardDefinition.id), nullable=False)
    owner_id = Column(Integer, nullable=True)
    spawn_timestamp = Column(DateTime, nullable=False)
    message_id = Column(Integer, nullable=False)

    def get_embed(self, ctx:Context):
        embed = self.definition.get_embed()
        if self.owner_id is not None:
            embed.title = ':white_check_mark: ' + embed.title
            name = ctx.guild.get_member(self.owner_id).display_name
            embed.set_footer(text=f'Claimed by {name}!')
        return embed

    def __repr__(self):
        return "Card({0.id}, {0.card_id}, {0.owner_id}, {0.spawn_timestamp}, " \
               "{0.message_id})".format(self)
