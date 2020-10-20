from operator import itemgetter, attrgetter
from operator import itemgetter, attrgetter
from typing import Iterable, List

import discord as d
from discord.ext.commands import Context
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Text, Enum, and_, not_, Boolean
from sqlalchemy.ext.hybrid import hybrid_property
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
    image_id = Column(Integer, nullable=True)
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
        embed.set_thumbnail(url=cfg.config['IMAGE_URL_BASE'].format(self.set.image_id, self.set.name))
        if self.image_id is not None:
            embed.set_image(url=cfg.config['IMAGE_URL_BASE'].format(self.image_id, self.id))
        else:
            embed.add_field(name='(No Image)', value='Images pls max', inline=False)

        return embed

    def __repr__(self):
        return "CardDefinition({0.id}, {0.name}, {0.image_id}, {0.description}, " \
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
    channel_id = Column(Integer, nullable=False)

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

class Transaction(Model):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True)
    user_1 = Column(Integer, nullable=False)
    user_2 = Column(Integer, nullable=False)
    cards_1 = Column(Text, nullable=True)
    cards_2 = Column(Text, nullable=True)
    accepted_1 = Column(Boolean, nullable=False, default=False)
    accepted_2 = Column(Boolean, nullable=False, default=False)
    message_id = Column(Integer, nullable=True)

    @hybrid_property
    def complete(self):
        return self.accepted_1 and self.accepted_2

    @hybrid_property
    def locked(self):
        return self.accepted_1 or self.accepted_2

    def is_party(self, user):
        """ Gets whether a user ID is either user 1 or 2. """
        return self.get_user(user) is not None

    def has_accepted(self, user):
        user = self.get_user(user)
        return getattr(self, 'accepted_' + str(user))

    def card_set(self, user):
        user = self.get_user(user)
        card_set = getattr(self, 'cards_' + str(user))
        if card_set is None: return set()
        else: return set(map(int, card_set.split(';')))

    def add_cards(self, user:int, cards:List[Card]):
        user = self.get_user(user)
        card_set = self.card_set(user)
        card_set |= set(map(attrgetter('id'), cards))
        setattr(self, 'cards_' + str(user), ';'.join(map(str, card_set)))

    def remove_cards(self, user:int, cards:List[Card]):
        user = self.get_user(user)
        card_set = self.card_set(user)
        for card in cards:
            card_set.discard(card.id)
        setattr(self, 'cards_' + str(user), ';'.join(map(str, card_set)) or None)

    def set_accepted(self, user:int, accepted:bool):
        user = self.get_user(user)
        setattr(self, 'accepted_' + str(user), accepted)

    def get_user(self, user:int):
        if user == 1 or user == 2: return user
        elif user == self.user_1: return 1
        elif user == self.user_2: return 2
        else: return None

    @staticmethod
    def _get_offer_field_text(card_map):
        if not card_map: return "No cards have been added."
        return '\n'.join('• ' + definition.string(count=count)
                         for count, definition in sorted(card_map.values(), key=lambda x: x[1].id))

    def get_embed(self, name_1, name_2, closed=False):
        embed = d.Embed()
        embed.set_author(name=cfg.config['EMBED_AUTHOR'])
        embed.title = "{}Card Trading | {} {} • {} {}".format(
            '[Complete] ' if self.complete else '[Closed] ' if closed else '',
            u'\u2705' if self.accepted_1 else '', name_1,
            u'\u2705' if self.accepted_2 else '', name_2
        )
        if not closed and not self.complete: embed.description = "__**How to trade:**__\n" \
            "• Offer one or more of your cards using **$trade [Card ID] [Amount]**.\n" \
            "• Remove a card you offered with **$untrade [Card ID] [Amount]**.\n" \
            "• When the trade looks good, accept it using **$accept**. Once a trade is accepted, cards can no longer be added or removed.\n" \
            "• If you change your mind, use **$unaccept** and you'll be able to change your offer.\n" \
            "• If the trade is a total bust, call **$cancel** to call the whole thing off.\n" \
            "• When both parties have accepted, the trade will be complete, and you'll each receive each other's offered cards!\n" \
            "Be sure to check your inventory while trading! **$inventory** is disabled here to reduce clutter, but you can use it in #ccc-commands, or in DMs."

        embed.add_field(
            name=f"{name_1}'s Offer",
            value=self._get_offer_field_text(util.query_card_map(self.card_set(1)))
        )
        embed.add_field(
            name=f"{name_2}'s Offer",
            value=self._get_offer_field_text(util.query_card_map(self.card_set(2)))
        )

        if closed: embed.set_footer(text='Trade has been canceled.')
        elif self.complete: embed.set_footer(text='Trade completed!')
        elif self.locked: embed.set_footer(text='Trade is locked until both parties accept.')

        embed.url = cfg.config['HELP_URL']
        embed.colour = d.Color(0xff00c8)
        return embed

    def __repr__(self):
        return "Transaction({0.id}, {0.user_1}, {0.user_2}, {0.cards_1}, {0.cards_2}, {0.accepted_1}, {0.accepted_2}" \
               "{0.message_id})".format(self)

class Inventory:
    def __init__(self, user_id):
        self.user_id = user_id
        self.inv = {}
        self.cards = session.query(Card).filter(Card.owner_ids.endswith(str(user_id))).all()
        self.inv = util.card_count_map(self.cards)
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

        num_items = cfg.config['ITEMS_PER_PAGE']
        items = sorted(
            self.inv.values(),
            key=lambda val: (val[1].set.order, val[1].rarity.order, val[1].id)
        )[num_items*page : num_items*(page+1)]

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
        self.definitions = session.query(CardDefinition) \
            .join(Card) \
            .filter(Card.owner_ids.contains(str(user_id))) \
            .all()
        self.max_page = util.max_page(self.length)

    def __contains__(self, card_id):
        return d.utils.get(self.definitions, id=card_id) is not None

    def __iter__(self):
        return iter(self.definitions)

    def __len__(self):
        return self.length

    def num_discovered(self):
        return len(self.definitions)

    def num_undiscovered(self):
        return len(self) - self.num_discovered()

    def get_embed(self, name, page):
        page = util.clamp(0, page, self.max_page)

        embed = d.Embed()
        embed.set_author(name=cfg.config['EMBED_AUTHOR'])
        embed.set_footer(text=f'Page {page + 1}/{self.max_page + 1}')
        embed.title = f"{name}'s CardDex"

        num_items = cfg.config['ITEMS_PER_PAGE']

        embed.description = f'You have discovered {len(self.definitions)} of {self.length} total cards.\n\n• '
        items_start = num_items*page
        items_end = min(num_items*(page+1), self.length)
        items = [f'[#{i+1}] ???' for i in range(items_start, items_end)]
        for definition in self.definitions:
            if items_start <= definition.id - 1 < items_end:
                items[(definition.id - 1) % num_items] = definition.string()
        embed.description += '\n• '.join(items)

        embed.url = cfg.config['HELP_URL']
        embed.colour = d.Color.green()
        return embed

class Leaderboard:
    UNWEIGHTED = 0
    WEIGHTED = 1

    def __init__(self, mode):
        self.mode = mode
        cards = session.query(Card).filter(and_(
            Card.claim_timestamp != None,
            not_(Card.owner_ids.endswith(';NULL'))
        )).all()
        self.board = {}
        for card in cards:
            id = card.owner_id
            if id not in self.board: self.board[id] = 0
            if mode == self.UNWEIGHTED:
                self.board[id] += 1
            else:
                self.board[id] += card.definition.rarity.weight
        self.board = sorted(self.board.items(), key=itemgetter(1), reverse=True)
        self.max_page = util.max_page(len(self.board))

    def __len__(self):
        return len(self.board)

    def get_embed(self, get_member, page):
        page = util.clamp(page, 0, self.max_page)

        embed = d.Embed()
        embed.set_author(name=cfg.config['EMBED_AUTHOR'])
        embed.set_footer(text=f'Page {page + 1}/{self.max_page + 1} | React with \U0001f504 to toggle Weighted and Unweighted leaderboards.')
        embed.title = "Leaderboard | " + ('Unweighted' if self.mode == self.UNWEIGHTED else 'Weighted')

        num_items = cfg.config['ITEMS_PER_PAGE']

        items_start = num_items * page
        items_end = min(num_items * (page + 1), len(self))
        items = []
        for i, (user_id, score) in enumerate(self.board[items_start:items_end]):
            items.append(f"#{i+1} - **{get_member(user_id).display_name}**: {score}")
        embed.description = '\n'.join(items)

        embed.url = cfg.config['HELP_URL']
        embed.colour = d.Color.orange()
        return embed
