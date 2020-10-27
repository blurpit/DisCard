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
        self.data['type'] = self.__class__.__name__
        self.data['set'] = random.choice([s for s in cfg.Set if s not in (cfg.Set.MEMBERS, cfg.Set.TESTSET)]).name
        self.data['guesses'] = {}

    async def on_message(self, message:d.Message):
        self.data['message_id'] = message.id
        self.data['channel_id'] = message.channel.id
        self.write(message.guild.id)

    def check(self, guess):
        return False

    async def on_guess(self, ctx:Context, guess):
        if ctx.channel.id != self.data['channel_id']:
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
        rarity = random.choices(list(cfg.Rarity), weights=[r.event_weight for r in cfg.Rarity])[0]
        definition = db.spawner.get_random_definition(card_set=card_set, rarity=rarity)

        embed = definition.get_embed(preview=True)
        embed.set_footer(text=f'This card was won by {ctx.author.display_name} in a card spawn event!')
        msg = await ctx.send(content=f'🎉 Congratulations, {ctx.author.mention}! The following card has been added to your inventory:', embed=embed)
        db.spawner.create_card_instance(definition, msg.id, ctx.channel.id, ctx.guild.id, owner_id=str(ctx.author.id))

        self.data = None

    async def on_incorrect(self, ctx, guess, guesses):
        await ctx.message.add_reaction(cfg.emoji['x'])

    async def on_out_of_guesses(self, ctx, guess):
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

class Expression(Event):
    max_guesses = None

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

    async def on_incorrect(self, ctx, guess, guesses):
        await ctx.message.delete()


def create() -> Event:
    return random.choice([Question, Trivia])()

def current(guild_id) -> Optional[Event]:
    data = loads(json.read()).get(str(guild_id), None)
    json.seek(0)
    if not data: return None
    return globals()[data['type']](**data)
