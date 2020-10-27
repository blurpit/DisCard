from sqlalchemy import or_, and_

from . import *


def get_active_transaction(user_id, guild_id):
    return session.query(Transaction) \
        .filter_by(guild_id=guild_id) \
        .filter(or_(Transaction.user_1 == user_id, Transaction.user_2 == user_id)) \
        .filter(not_(and_(Transaction.accepted_1, Transaction.accepted_2))) \
        .one_or_none()

def open_transaction(user_1, user_2, guild_id):
    transaction = Transaction(
        user_1=user_1,
        user_2=user_2,
        guild_id=guild_id
    )
    session.add(transaction)
    session.commit()
    return transaction

def close_active_transaction(user_id, guild_id):
    transaction = get_active_transaction(user_id, guild_id)
    if transaction:
        session.delete(transaction)
        session.commit()
        return transaction

def set_transaction_message(transaction:Transaction, message_id):
    transaction.message_id = message_id
    session.commit()

def set_transaction_accepted(transaction:Transaction, user_id, accepted):
    if user_id == transaction.user_1: transaction.accepted_1 = accepted
    elif user_id == transaction.user_2: transaction.accepted_2 = accepted
    session.commit()

def execute(transaction:Transaction):
    if not (transaction.cards_1 and transaction.cards_2): return

    for card in util.query_cards(transaction.card_set(1)):
        card.owner_ids += ';' + str(transaction.user_2)
    for card in util.query_cards(transaction.card_set(2)):
        card.owner_ids += ';' + str(transaction.user_1)
    session.commit()
