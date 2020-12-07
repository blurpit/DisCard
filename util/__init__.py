import asyncio
import logging
import math

import discord as d

import cfg
import db

log = logging.getLogger('DiscardLogger')
handler = logging.FileHandler('logs/discard.log')
handler.setFormatter(logging.Formatter('[%(levelname)s] [%(asctime)s] %(message)s'))
log.addHandler(handler)
log.setLevel(logging.DEBUG)


def max_page(length):
    return max(int((length-1) // cfg.config['ITEMS_PER_PAGE']), 0)

def clamp(n, low=None, high=None):
    if low is None: low = -math.inf
    if high is None: high = math.inf
    return max(low, min(n, high))

def card_count_map(cards):
    """ Takes a list of Card instances and returns a mapping of
        card_id: [number of cards, CardDefinition] """
    count = {}
    for card in cards:
        # Card definition was deleted - probably a test card. Ignore it.
        if not card.definition: continue

        if card.card_id not in count:
            count[card.card_id] = [0, card.definition]
        count[card.card_id][0] += 1
    return count

def calculate_discard_offer(card_ids):
    result = {}

    weights = {
        'RARE': 3,
        'EPIC': 12
    }
    cost = 1/3

    rarities = db.query_rarity_map(card_ids)
    get = lambda r: rarities.get(r, 0)
    score = get(cfg.Rarity.COMMON) \
            + weights['RARE'] * get(cfg.Rarity.RARE) \
            + weights['EPIC'] * get(cfg.Rarity.EPIC)
    score = score * cost

    result[cfg.Rarity.EPIC] = int(score / weights['EPIC'])
    score %= weights['EPIC']

    result[cfg.Rarity.RARE] = int(score / weights['RARE'])
    score %= weights['RARE']

    result[cfg.Rarity.COMMON] = int(score)

    return result


class TaskLooper:
    min_delay = 60 # Minimum delay. Prevents tasks running too quickly
    post_delay = 30 # Delay after running and before calculating the next delay
    err_delay = 5*60 # Delay for retrying after an error

    def delay(self):
        raise NotImplemented

    async def run(self, client:d.Client):
        raise NotImplemented

    async def create(self, client:d.Client):
        await client.wait_until_ready()
        log.info('Task created: %s', str(self))
        while True:
            if client.is_closed():
                raise d.ClientException('Client is closed.')

            delay = clamp(self.delay(), low=self.min_delay)
            log.debug('Scheduled task %s for %.0fhr %.0fmin %.2fsec (%f)',
                     str(self), delay//3600, delay%3600//60, delay%60, delay)

            await asyncio.sleep(delay)
            for guild in client.guilds:
                if guild.id in cfg.config['ENABLED_GUILDS']:
                    while not await self._execute(client, guild):
                        await asyncio.sleep(self.err_delay)

    async def handle(self, client:d.Client, guild:d.Guild, error):
        try:
            if cfg.config['LOG_CHANNEL']:
                channel = client.get_channel(cfg.config['LOG_CHANNEL'])
                await channel.send(":warning: Failed to run task '{}' in guild '{}'. Error:```\n{}: {}```Trying again in {} seconds."
                                   .format(str(self), str(guild), type(error).__name__, str(error), self.err_delay))
        except:
            log.error('Failed to send error to log channel.')
        finally:
            log.error("Failed to run task '%s'. Trying again in %d seconds.", str(self), self.err_delay, exc_info=error)
            return False

    async def _execute(self, client, guild):
        try:
            log.info("Running task %s for guild '%s' (%d)", str(self), guild.name, guild.id)
            await self.run(guild)
            await asyncio.sleep(self.post_delay)
            return True
        except Exception as error:
            return await self.handle(client, guild, error)

    def __str__(self):
        return self.__class__.__name__


class CleanException(Exception):
    """ CleanException messages will be sent as normal messages to the context """
    pass

class BadArgument(CleanException):
    def __init__(self, arg, val, message=None):
        if not message: message = "Invalid value for **{}**: '**{}**'"
        super().__init__(message.format(arg, val))

class NoActiveTrade(CleanException):
    def __init__(self, message=None):
        if not message: message = "You don't have an active trade open. Use **$trade @Example** to start trading."
        super().__init__(message)

class UserNotFound(CleanException):
    def __init__(self, user, message=None):
        if not message: message = "User not found: **{}**"
        super().__init__(message.format(user))

class NotInInventory(CleanException):
    def __init__(self, card, message=None):
        if not message: message = "You don't have **{}** in your inventory."
        super().__init__(message.format(card))
