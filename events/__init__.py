import random
import re
from html import unescape
from json import loads, dumps
from typing import Optional

import discord as d
import requests
from discord.ext.commands import Context
import db.spawner

import cfg
import util

json = open('data/event/event.json', 'r+')


class Event:
    max_guesses = None

    def __init__(self, **kwargs):
        self.data = kwargs

    @property
    def content(self):
        return self.data['content']

    @content.setter
    def content(self, con):
        self.data['content'] = con

    def write(self, guild_id):
        load = loads(json.read())
        json.seek(0)
        load[str(guild_id)] = self.data

        json.write(dumps(load, indent=4))
        json.truncate()
        json.seek(0)

    def generate(self):
        self.data['type'] = self.__class__.__name__.lower()
        self.data['set'] = random.choice([s for s in cfg.Set if s != cfg.Set.MEMBERS]).name
        self.data['guesses'] = {}

    async def on_message(self, message:d.Message):
        self.data['message_id'] = message.id
        self.data['channel_id'] = message.channel.id
        self.write(message.guild.id)

    def check(self, guess):
        return False

    async def on_guess(self, ctx:Context, guess):
        if guess is None or ctx.channel.id != self.data['channel_id']:
            return

        guesses = self.data['guesses'].get(str(ctx.author.id), 0)
        if self.max_guesses is not None and guesses >= self.max_guesses:
            await self.on_out_of_guesses(ctx, guess)
        else:
            guesses = self.data['guesses'][str(ctx.author.id)] = guesses + 1
            if self.check(guess):
                await self.on_correct(ctx, guess, guesses)
            else:
                await self.on_incorrect(ctx, guess, guesses)
        self.write(ctx.guild.id)

    async def on_correct(self, ctx:Context, guess, guesses):
        await ctx.message.add_reaction(cfg.emoji['check'])

        card_set = cfg.Set[self.data['set']]
        rarity = random.choices(list(cfg.Rarity), weights=[r.event_chance for r in cfg.Rarity])[0]
        definition = db.spawner.get_random_definition(card_set=card_set, rarity=rarity)

        embed = definition.get_embed(preview=True)
        embed.set_footer(text=f'This card was won by {ctx.author.display_name} in a card spawn event!')
        msg = await ctx.send(content=f'🎉 Congratulations, {ctx.author.mention}! The following card has been added to your inventory:', embed=embed)
        db.spawner.create_card_instance(definition, msg.id, ctx.channel.id, ctx.guild.id, owner_id=str(ctx.author.id))

        self.data = None

    async def on_incorrect(self, ctx:Context, guess, guesses):
        await ctx.message.add_reaction(cfg.emoji['x'])

    async def on_out_of_guesses(self, ctx:Context, guess):
        pass

    def get_embed_base(self):
        embed = d.Embed()
        embed.set_author(name=cfg.config['EMBED_AUTHOR'])
        embed.title = 'Card Spawn Event'
        embed.url = cfg.config['HELP_URL']
        embed.colour = d.Color(0xFEFEFE)

        card_set = cfg.Set[self.data['set']]
        embed.description = f"Answer the following to receive 1 x Guaranteed **Rare or higher** from the *{card_set.text} Set*:\n\n"

        text='Submit your answer using $guess'
        if self.max_guesses == 1:
            text += ' (you have only 1 guess)'
        elif self.max_guesses is not None:
            text += f' (you have {self.max_guesses} guesses)'
        embed.set_footer(text=text)

        return embed

    async def fetch_message(self, ctx:Context):
        try:
            return await ctx.fetch_message(self.data['message_id'])
        except d.NotFound:
            return None

class Question(Event):
    max_guesses = 5

    def generate(self):
        with open('data/event/questions.json') as f:
            super().generate()
            self.content = random.choice(loads(f.read()))

            embed = self.get_embed_base()
            embed.description += f"**{self.content['q']}**"

            return dict(embed=embed)

    def check(self, guess):
        return bool(re.fullmatch(self.content['a'], guess, re.IGNORECASE))

class Trivia(Event):
    max_guesses = 1
    categories = [
        9, # General Knowledge
        15, # Video Games
        17, # Science & Nature
        19, # Science: Math
        18, # Science: Computers
        30, # Science: Gadgets
    ]
    difficulties = ['easy', 'medium', 'hard']

    def generate(self):
        super().generate()
        category = random.choice(self.categories)
        difficulty = random.choice(self.difficulties)
        trivia = requests.get(f'https://opentdb.com/api.php?amount=1&type=multiple&category={category}&difficulty={difficulty}').json()
        trivia = trivia['results'][0]

        letters = "ABCDEFG"
        options = [trivia['correct_answer']] + trivia['incorrect_answers']
        options = list(map(unescape, options))
        random.shuffle(options)
        self.content = {
            'category': unescape(trivia['category']),
            'difficulty': unescape(trivia['difficulty'].title()),
            'question': unescape(trivia['question']),
            'answer': letters[options.index(unescape(trivia['correct_answer']))]
        }

        embed = self.get_embed_base()
        embed.description += f"({self.content['difficulty']}) [{self.content['category']}] **{self.content['question']}**\n"
        embed.description += '\n'.join(f"{letters[i]}) {option}" for i, option in enumerate(options))

        return dict(embed=embed)

    def check(self, guess):
        return guess.upper() == self.content['answer']

    async def on_incorrect(self, ctx:Context, guess, guesses):
        await ctx.message.delete()

class Hangman(Event):
    max_guesses = 1
    image_ids = [
        777400582973030400, # Gallows (Empty)
        777400587754799144, # Head
        777400591751053312, # Body
        777400594981715978, # Leg 1
        777400598583705620, # Leg 2
        777400603441496084, # Arm 1
        777400607128289312, # Arm 2
        777437991664746506, # Eye 1
        777437985783808001, # Eye 2
        777438502233047050 # Mouth
    ]

    def generate(self):
        with open('data/event/hangman/words.txt') as f:
            super().generate()

            answer = next(f).strip().upper()
            for i, line in enumerate(f, 2):
                if random.randrange(i): continue
                answer = line.strip().upper()

            self.content = {
                'answer': answer,
                'guessed': ''
            }

            return dict(embed=self.get_embed_base())

    def check(self, guess):
        return guess == self.content['answer']

    async def on_guess(self, ctx:Context, guess):
        if guess is None: return
        guess = guess.strip().upper()

        guesses = self.data['guesses'].get(str(ctx.author.id), 0)
        if self.max_guesses is not None and guesses >= self.max_guesses:
            await self.on_out_of_guesses(ctx, guess)
        else:
            if len(guess) > 1:
                await super().on_guess(ctx, guess)
            elif len(guess) == 1 and guess in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' and guess not in self.content['guessed']:
                if guess in self.content['answer']:
                    await self.on_correct(ctx, guess, 0)
                else:
                    await self.on_incorrect(ctx, guess, 0)
                self.write(ctx.guild.id)

    async def on_correct(self, ctx:Context, guess, guesses):
        if len(guess) > 1:
            return await super().on_correct(ctx, guess, guesses)
        elif len(guess) == 1:
            await ctx.message.add_reaction(cfg.emoji['check'])
            await self._update_letter_guess(ctx, guess)

    async def on_incorrect(self, ctx:Context, guess, guesses):
        await super().on_incorrect(ctx, guess, guesses)
        if len(guess) == 1:
            await self._update_letter_guess(ctx, guess)

    def get_embed_base(self):
        embed = super().get_embed_base()
        if self.failed: embed.description = 'RIP in peace. Nobody guessed the word and the Hangman has died. Press F to pay respects.\n\nAnswer:\n'
        embed.description += self._get_letter_display()
        embed.description += f"\nGuessed: **{self._get_guessed_text()}**"

        embed.set_image(url=self._get_image_url())
        text = 'Guess a letter or the full word using $guess'
        if self.failed:
            text = embed.Empty
        elif self.max_guesses > 1:
            text += f' (you have unlimited letter guesses but {self.max_guesses} word guesses)'
        else:
            text += ' (you have unlimited letter guesses but only 1 word guess)'
        embed.set_footer(text=text)
        return embed

    async def _update_letter_guess(self, ctx:Context, guess):
        self.content['guessed'] += guess
        msg = await self.fetch_message(ctx)
        if msg:
            await msg.edit(embed=self.get_embed_base())
        else:
            msg = await ctx.send(embed=self.get_embed_base())
            await self.on_message(msg)
        if self.failed:
            await ctx.send(f"RIP in peace. Nobody guessed the word and the Hangman has died. "
                           f"Press F to pay respects.\nAnswer was: **{self.content['answer']}**")
            self.data = None

    @property
    def stage(self):
        return util.clamp(
            len(set(self.content['guessed']) - set(self.content['answer'])),
            0, len(self.image_ids)-1
        )

    @property
    def failed(self):
        return self.stage == len(self.image_ids)-1

    def _get_letter_display(self):
        text = ''
        for ch in self.content['answer']:
            if ch == ' ':
                text += ':black_small_square: '
            elif ch in self.content['guessed'] or self.failed:
                text += ':regional_indicator_' + ch.lower() + ': '
            else:
                text += ':blue_square: '
        return text

    def _get_image_url(self):
        return cfg.config['IMAGE_URL_BASE'].format(self.image_ids[self.stage], self.stage)

    def _get_guessed_text(self):
        if self.content['guessed']:
            return ', '.join(sorted(self.content['guessed']))
        else:
            return 'None'


event_map = {
    'question': Question,
    'trivia': Trivia,
    'hangman': Hangman
}

def create(cls=None) -> Event:
    if cls is None:
        cls = random.choice([Question, Trivia])
    else:
        cls = event_map[cls.lower()]
    return cls()

def current(guild_id) -> Optional[Event]:
    data = loads(json.read()).get(str(guild_id), None)
    json.seek(0)
    if not data: return None
    return event_map[data['type'].lower()](**data)
