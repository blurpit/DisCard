from operator import itemgetter, attrgetter
from typing import Iterable, List

import discord as d
from discord.ext.commands import Context
from sqlalchemy import Column, Integer, DateTime, ForeignKey, Text, Enum, not_, Boolean, func
from sqlalchemy.orm import relationship

import cfg
import util
from . import Model, session


class CardDefinition(Model):
    __tablename__ = 'definitions'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    rarity = Column(Enum(cfg.Rarity, create_constraint=False), nullable=False)
    set = Column(Enum(cfg.Set, create_constraint=False), nullable=False)
    expansion = Column(Enum(cfg.Expansion, create_constraint=False), nullable=False)
    event_category = Column(Enum(cfg.EventCategory, create_constraint=False))
    image_id = Column(Integer, nullable=True)
    description = Column(Text, nullable=False)

    instances:Iterable = relationship('Card', backref='definition')

    def get_embed(self, preview=False, count=None):
        embed = d.Embed()

        embed.title = f'[#{self.id}] {self.name}'
        embed.url = cfg.config['HELP_URL']
        embed.colour = d.Color(self.rarity.color)
        embed.description = self.description

        embed.set_author(name=cfg.config['EMBED_AUTHOR'])
        embed.add_field(name='Set', value=f'[{self.expansion.text}] {self.set.text}')
        embed.add_field(name='Rarity', value=self.rarity.text)
        embed.set_thumbnail(url=cfg.config['IMAGE_URL_BASE'].format(self.set.image_id, self.set.name))

        if self.image_id is not None:
            embed.set_image(url=cfg.config['IMAGE_URL_BASE'].format(self.image_id, self.id))
        else:
            embed.add_field(name='(No Image)', value='Images pls max', inline=False)

        if preview:
            if count == 1:
                embed.set_footer(text=f'You currently own 1 copy of this card.')
            elif count is not None:
                embed.set_footer(text=f'You currently own {count} copies of this card.')
        else:
            embed.set_footer(text=f'This card is unclaimed! Use $claim to claim it!')

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
    guild_id = Column(Integer, nullable=False)

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

    def get_embed(self, ctx:Context, preview=False, count=None):
        embed:d.Embed = self.definition.get_embed(preview=preview, count=count)

        if self.owner_id is not None:
            if preview: embed.title = '[Preview] ' + embed.title
            else: embed.title = ':white_check_mark: ' + embed.title

            name = ctx.guild.get_member(self.owner_id).display_name
            if not preview:
                embed.set_footer(text=f'Claimed by {name}!')
                if cfg.config['REMOVE_IMAGE_AFTER_CLAIM']:
                    embed.set_image(url=embed.Empty)

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
    guild_id = Column(Integer, nullable=False)

    @property
    def complete(self):
        return self.accepted_1 and self.accepted_2

    @property
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

    def remove_all(self, user:int):
        user = self.get_user(user)
        if user == 1: self.cards_1 = None
        elif user == 1: self.cards_2 = None

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
        result = '• '
        added = 0
        for count, definition in sorted(card_map.values(), key=lambda x: (x[1].rarity.order, x[1].id)):
            line = definition.string(count=count, set=False)
            if added > 0: line = '\n• ' + line
            if len(result + line) > 1000:
                remaining = sum(x[0] for x in card_map.values()) - added
                result += f'\n• ... {remaining} more card(s)'
                break
            else:
                result += line
                added += count
        return result

    @staticmethod
    def _get_discard_offer_field_text(offer):
        if sum(offer.values()) <= 0: return "No cards offered."
        return '\n'.join(f'• Random **{rarity.text}** x {count}' for rarity, count in offer.items() if count > 0)

    def get_embed(self, name_1, name_2, closed=False):
        embed = d.Embed()
        embed.set_author(name=cfg.config['EMBED_AUTHOR'])
        embed.title = "{}Card Trading | {} {} • {} {}".format(
            '[Complete] ' if self.complete else '[Closed] ' if closed else '',
            cfg.emoji['check'] if self.accepted_1 else '', name_1,
            cfg.emoji['check'] if self.accepted_2 else '', name_2
        )

        if not closed and not self.complete:
            if self.is_party(0):
                embed.description = "__**How to Trade:**__\n" \
                    "• Offer one or more of your cards using **$trade [Card ID] [Amount]**.\n" \
                    "• Remove one or more cards you offered with **$untrade [Card ID] [Amount]**.\n" \
                    "• Offer all of your duplicate cards using **$trade duplicates**.\n" \
                    "• Remove all offered cards using **$untrade all**\n" \
                    "• When the exchange looks good, accept it using **$accept**.\n" \
                    "• Call **$cancel** to call the exchange off.\n" \
                    "Be sure to check your inventory! **$inventory** is disabled here to reduce clutter, but you can use it in #ccc-commands.\n"
            else:
                embed.description = "__**How to Trade:**__\n" \
                    "• Offer one or more of your cards using **$trade [Card ID] [Amount]**.\n" \
                    "• Remove a card you offered with **$untrade [Card ID] [Amount]**.\n" \
                    "• Offer all of your duplicate cards using **$trade duplicates**.\n" \
                    "• Remove all offered cards using **$untrade all**\n" \
                    "• When the trade looks good, accept it using **$accept**. Once a trade is accepted, cards can no longer be added or removed.\n" \
                    "• If you change your mind, use **$unaccept** and you'll be able to change your offer.\n" \
                    "• If the trade is a total bust, call **$cancel** to call the whole thing off.\n" \
                    "• When both parties have accepted, the trade will be complete, and you'll each receive each other's offered cards!\n" \
                    "Be sure to check your inventory while trading! **$inventory** is disabled here to reduce clutter, but you can use it in #ccc-commands."

        from . import query_card_map
        embed.add_field(
            name=f"{name_1}'s Offer",
            value=self._get_offer_field_text(query_card_map(self.card_set(1)))
        )
        embed.add_field(
            name=f"{name_2}'s Offer",
            value=self._get_discard_offer_field_text(util.calculate_discard_offer(self.card_set(1)))
                if self.is_party(0) and not self.complete else
                self._get_offer_field_text(query_card_map(self.card_set(2)))
        )

        if closed: embed.set_footer(text='Trade has been canceled.')
        elif self.complete: embed.set_footer(text='Trade completed!')
        elif self.locked: embed.set_footer(text='Trade is locked until both parties accept.')

        embed.url = cfg.config['HELP_URL']
        embed.colour = d.Color(0x0a00c4)
        return embed

    def __repr__(self):
        return "Transaction({0.id}, {0.user_1}, {0.user_2}, {0.cards_1}, {0.cards_2}, " \
               "{0.accepted_1}, {0.accepted_2} {0.message_id})".format(self)

class Inventory:
    def __init__(self, user_id, guild_id, dupes_only=False):
        self.user_id = user_id
        self.dupes_only = dupes_only
        self.inv = {}
        self.cards = session.query(Card) \
            .filter_by(guild_id=guild_id) \
            .filter(Card.owner_ids.endswith(str(user_id))) \
            .all()
        self.inv = util.card_count_map(self.cards)
        self.max_page = util.max_page(len(self.inv)) if not self.dupes_only \
            else util.max_page(sum(True for item in self.inv.values() if item[0] > 1))

    def __getitem__(self, item) -> Card:
        if isinstance(item, int):
            return d.utils.get(self.cards, card_id=item)
        elif isinstance(item, str):
            return d.utils.find(lambda c: c.definition.name.lower() == item.lower(), self.cards)

    def __iter__(self):
        return iter(self.cards)

    def __len__(self):
        """ Number of unique cards """
        return len(self.cards)

    def __contains__(self, card):
        if isinstance(card, int):
            return card in self.inv
        else:
            return card.lower() in map(lambda item: item[1].name.lower(), self.inv.values())

    def filter(self, **kwargs):
        """ Filter the inventory by certain attributes. Ex: inv.filter(set=Set.SMASH, rarity=Rarity.RARE) """
        return filter(
            lambda c: all(getattr(c, attr) == kwargs[attr] for attr in kwargs),
            self.cards
        )

    def count(self, card):
        if isinstance(card, int):
            return self.inv[card][0]
        else:
            return next((count for count, definition in self.inv.values() if definition.name.lower() == card.lower()), 0)

    def _duplicates_only_inv(self):
        for item in self.inv.values():
            if item[0] > 1:
                yield item

    def get_embed(self, name, page):
        page = util.clamp(page, 0, self.max_page)

        embed = d.Embed()
        embed.set_author(name=cfg.config['EMBED_AUTHOR'])
        embed.set_footer(text=f'Page {page+1}/{self.max_page + 1}')
        embed.title = f"{name}'s Card Collection"
        if self.dupes_only: embed.title += ' | (Duplicates Only)'

        num_items = cfg.config['ITEMS_PER_PAGE']
        items = sorted(
            self.inv.values() if not self.dupes_only else self._duplicates_only_inv(),
            key=lambda val: (val[1].set.order, val[1].rarity.order, val[1].id)
        )[num_items*page : num_items*(page+1)]

        if items:
            if not self.dupes_only: embed.description = f'You own {len(self)} cards! ({len(self.inv)} unique)\n'
            else: embed.description = f'You own {len(self)} cards! ({len(items)} with multiple copies)'

            embed.description += '\n**' + items[0][1].set.text + ' Set**'
            for i in range(len(items)):
                count, definition = items[i]
                embed.description += '\n• ' + items[i][1].string(set=False, count=count)
                if i+1 < len(items) and definition.set != items[i+1][1].set:
                    embed.description += '\n\n**' + items[i+1][1].set.text + ' Set**'
        else:
            if not self.dupes_only: embed.description = "There's nothing in your inventory. Use **$claim** to claim a card next time you see one!"
            else: embed.description = "You don't have any duplicate cards in your inventory."

        embed.url = cfg.config['HELP_URL']
        embed.colour = d.Color.blue()
        return embed

class CardDex:
    def __init__(self, user_id, guild_id):
        self.length = session.query(CardDefinition.id).count()
        self.definitions = session.query(CardDefinition) \
            .join(Card) \
            .filter(Card.guild_id == guild_id) \
            .filter(Card.owner_ids.contains(str(user_id))) \
            .all()
        self.set_totals = dict(session.query(CardDefinition.set, func.count()) \
            .group_by(CardDefinition.set) \
            .all())
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
        sets = {}
        for definition in self.definitions:
            sets[definition.set] = sets.get(definition.set, 0) + 1
            if items_start <= definition.id - 1 < items_end:
                items[(definition.id - 1) % num_items] = definition.string()
        embed.description += '\n• '.join(items)

        badges = ' '.join(s.badge for s, c in sets.items() if c >= self.set_totals[s])
        if badges:
            embed.description = badges + '\n' + embed.description

        embed.url = cfg.config['HELP_URL']
        embed.colour = d.Color.green()
        return embed

class Leaderboard:
    UNWEIGHTED = 0
    WEIGHTED = 1

    def __init__(self, mode, guild_id):
        self.mode = mode
        cards = session.query(Card) \
            .filter(Card.claim_timestamp != None) \
            .filter(not_(Card.owner_ids.endswith(';0'))) \
            .filter(Card.guild_id == guild_id) \
            .all()
        self.board = {}
        for card in cards:
            # Card definition was deleted - probably a test card. Ignore it.
            if not card.definition: continue

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
            user = get_member(user_id)
            if user: items.append(f"#{i+1} - **{user.display_name}**: {score}")
        embed.description = '\n'.join(items)

        embed.url = cfg.config['HELP_URL']
        embed.colour = d.Color.orange()
        return embed
