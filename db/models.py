from typing import Iterable

import discord as d
from discord.ext.commands import Context
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship

import cfg
import util
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
        embed.url = cfg.config['HELP_URL']
        embed.colour = d.Color(self.rarity.color)
        embed.description = self.description
        embed.set_author(name=cfg.config['EMBED_AUTHOR'])
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

    def string(self, id=True, name=True, set=True, rarity=True, count=None):
        result = []
        if id: result.append(f"[#{self.id}]")
        if name: result.append(f"**{self.name}**")
        if set: result.append(f"*{self.set.text}*")
        if rarity: result.append(f"({self.rarity.text})")
        if count not in (1, None): result.append(f"x {count}")
        return ' '.join(result)

class Card(Model):
    __tablename__ = 'cards'

    id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey(CardDefinition.id), nullable=False)
    owner_ids = Column(Text, nullable=True)
    spawn_timestamp = Column(DateTime, nullable=False)
    claim_timestamp = Column(DateTime, nullable=True)
    message_id = Column(Integer, nullable=False)

    @property
    def owner_id_list(self):
        if self.owner_ids is None: return []
        else: return list(map(int, self.owner_ids.split(';')))

    @owner_id_list.setter
    def owner_id_list(self, lis):
        if not lis: self.owner_ids = None
        else: self.owner_ids = ';'.join(map(str, lis))

    @property
    def owner_id(self):
        if self.owner_ids is None: return None
        else: return int(self.owner_ids.rsplit(';', 1)[-1])

    @owner_id.setter
    def owner_id(self, id):
        self.owner_id_list += [id]

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
    def __init__(self, user_id):
        self.user_id = user_id
        self.inv = {}
        self.cards = session.query(Card).filter(Card.owner_ids.endswith(str(user_id))).all()
        # {card_id: [card count, card definition]
        for card in self.cards:
            if card.card_id not in self.inv:
                self.inv[card.card_id] = [1, card.definition]
            else:
                self.inv[card.card_id][0] += 1
        self.max_page = util.max_page(len(self.inv))

    def __getitem__(self, item) -> Card:
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

    def get_embed(self, name, page):
        page = util.clamp(page, 0, self.max_page)

        embed = d.Embed()
        embed.set_author(name=cfg.config['EMBED_AUTHOR'])
        embed.set_footer(text=f'Page {page+1}/{self.max_page + 1}')
        embed.title = f"{name}'s Card Collection"

        definitions = sorted(
            self.inv.values(),
            key=lambda val: (val[1].set.order, val[1].rarity.order, val[1].id)
        )

        num_items = cfg.config['ITEMS_PER_PAGE']
        items = definitions[num_items*page:num_items*(page+1)]

        embed.description = f'You own {len(self)} cards! ({len(self.inv)} unique)\n'
        embed.description += '\n**' + items[0][1].set.text + ' Set**'
        for i in range(len(items)):
            count, definition = items[i]
            embed.description += '\n• ' + items[i][1].string(set=False, count=count)
            if i+1 < len(items) and definition.set != items[i+1][1].set:
                embed.description += '\n\n**' + items[i+1][1].set.text + ' Set**'

        embed.url = cfg.config['HELP_URL']
        embed.colour = d.Color.blue()
        return embed

class CardDex:
    def __init__(self, user_id):
        self.user_id = user_id
        self.length = session.query(CardDefinition.id).count()
        self.cards = session.query(CardDefinition) \
            .join(Card) \
            .filter(Card.owner_ids.contains(str(user_id))) \
            .all()
        self.max_page = util.max_page(self.length)

    def get_embed(self, name, page):
        page = util.clamp(0, page, self.max_page)

        embed = d.Embed()
        embed.set_author(name=cfg.config['EMBED_AUTHOR'])
        embed.set_footer(text=f'Page {page + 1}/{self.max_page + 1}')
        embed.title = f"{name}'s CardDex"

        num_items = cfg.config['ITEMS_PER_PAGE']

        embed.description = f'You have discovered {len(self.cards)} of {self.length} total cards.\n\n• '
        items_start = num_items*page
        items_end = min(num_items*(page+1), self.length)
        items = [f'[#{i+1}] ???' for i in range(items_start, items_end)]
        for definition in self.cards:
            if items_start <= definition.id <= items_end:
                items[definition.id % num_items - 1] = definition.string()
        embed.description += '\n• '.join(items)

        embed.url = cfg.config['HELP_URL']
        embed.colour = d.Color.green()
        return embed
