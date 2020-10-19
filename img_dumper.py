import asyncio

import discord as d
import db

client = d.Client()
DUMP_CHANNEL = 767822158294286387
DUMP_START = 244
DUMP_LIMIT = None
DUMP_DELAY = 2.0

@client.event
async def on_ready():
    print("\nLogged in as {}".format(client.user))

    channel:d.TextChannel = client.get_channel(DUMP_CHANNEL)
    # definitions = db.session.query(db.CardDefinition) \
    #     .limit(DUMP_LIMIT) \
    #     .offset(DUMP_START - 1) \
    #     .all()
    #
    # for definition in definitions:
    #     file = d.File(f'data/images/{definition.id}.png')
    #     msg = await channel.send(file=file)
    #     definition.image_id = msg.id
    #     db.session.commit()
    #
    #     print(definition.id, definition.image_id, file)
    #     await asyncio.sleep(DUMP_DELAY)

    async for msg in channel.history(limit=None, oldest_first=True):
        if msg.attachments:
            file = msg.attachments[0]
            filename = file.filename[:-4]
            image_id = int(file.url.rsplit('/', 2)[1])
            card_id = int(filename) if filename.isnumeric() else filename
            print(card_id, image_id, sep='\t')

    # db.session.commit()


if __name__ == '__main__':
    with open('client_secret.txt', 'r') as secret:
        token = secret.read().strip()
    client.run(token)
