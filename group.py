import vk
import json
import os
import random
import time
import requests.exceptions
from user import User
from transaction import Transaction
from product import Product


def to_json(o):
    return o.to_json()


class BaseGroup:
    def __init__(self):
        self.users = []
        self.users_by_name = dict()
        self.users_by_id = dict()
        self.admins_id = [211401321]
        self.transactions_by_id = dict()

    def to_json(self):
        return {
            "users": [
                u for u in self.users
            ],
            "transactions": [
                t for t in self.transactions_by_id.values()
            ]
        }

    def load(self, stream):
        res = json.load(stream)

        for u in res["users"]:
            self.add_user(User(
                self,
                u["name"],
                u["id"],
                u["balance"]
            ))

        for t in res["transactions"]:
            t = Transaction(
                self.users_by_id[t["purchaser"]],
                [Product(p[0], p[1]) for p in t["products"]],
                [self.users_by_id[id] for id in t["consumers"]],
                {self.users_by_id[id] for id in t["confirmers"]},
                t["message_id"]
            )
            self.transactions_by_id[t.message_id] = t
    
    def add_user(self, user: User):
        self.users.append(user)
        self.users_by_name[user.name] = user
        self.users_by_id[user.id] = user

    def save(self, stream):
        json.dump(
            self.to_json(),
            stream,
            ensure_ascii=False,
            indent=4,
            default=to_json
        )

    def save_data(self):
        with open("data_tmp.json", "w", encoding="utf-8") as file:
            self.save(file)
        os.remove("data.json")
        os.rename("data_tmp.json", "data.json")
    
    def create_transaction(self, purchaser, products, names, message_id):
        consumers = []

        for name in names:
            if name in self.users_by_name:
                consumers.append(self.users_by_name[name])
            elif name in ("все", "всем"):
                consumers = self.users
                break
            else:
                return  # TODO: add error raise and handle in subclass

        confirmers = consumers.copy()
        if purchaser not in consumers:
            confirmers.append(purchaser)
        transaction = Transaction(purchaser, products, consumers, confirmers, message_id)
        self.transactions_by_id[message_id] = transaction
        self.save_data()
        return transaction
    
    def decline_transaction(self, user, transaction_id):
        transaction = self.transactions_by_id[transaction_id]
        del self.transactions_by_id[transaction_id]
        self.save_data()
        return transaction

    def confirm_transaction(self, user, transaction_id):
        transaction = self.transactions_by_id[transaction_id]
        if user not in transaction.confirmers:
            return  # TODO: add error raise and handle in subclass
        transaction.confirmers.remove(user)

        if not transaction.confirmers:
            self.make_transaction(transaction)
            del self.transactions_by_id[transaction.message_id]
        self.save_data()
        return transaction

    def make_transaction(self, transaction):
        val_per_usr = transaction.value / len(transaction.consumers)
        transaction.purchaser.balance += val_per_usr * len(transaction.consumers)
        for user in transaction.consumers:
            user.balance -= val_per_usr
        self.save_data()


class Group(BaseGroup):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
    
    def save_data(self):
        try:
            super().save_data()
        except Exception as e:
            self.send_admins(e)

    def add_user(self, user):
        if isinstance(user, User):
            return super().add_user(user)
        
        peer_id = user
        user = self.bot.get_user(peer_id)
        user = User(self, user[0]["first_name"], peer_id)

        self.users.append(user)
        self.users_by_name[user.name] = user
        self.users_by_id[peer_id] = user

        return user

    def run(self):
        try:
            self.load(open("data.json", encoding='utf-8'))
        except Exception as e:
            self.send_admins(e)
        else:
            try:
                while True:
                    self.idle()
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
            except Exception as e:
                self.send_admins(type(e))
                self.send_admins(e)
                raise e
            finally:
                self.save_data()

    def send(self, user, message, *args, **kwargs):
        return self.bot.send(
            peer_id=user.id,
            random_id=random.random(),
            message=message,
            *args, **kwargs
        )

    def send_admins(self, message):
        for id in self.admins_id:
            self.send(self.users_by_id[id], message)

    def confirm_transaction(self, user, transaction_id):
        transaction = super().confirm_transaction(user, transaction_id)

        if not transaction.confirmers:
            self.send(
                transaction.purchaser,
                "Покупка подтверждена\n",
                forward_messages=transaction.message_id
            )
            self.send(
                transaction.purchaser,
                "\n".join(
                    "Баланс {}: {}₽".format(user.name, user.balance)
                    for user in self.users_by_name.values()
                )
            )

    def decline_transaction(self, user, transaction_id):
        transaction = super().decline_transaction(user, transaction_id)
        for consumer in transaction.consumers:
            self.send(
                consumer,
                "{} не подтвердил покупку".format(user.name),
                forward_messages=transaction.message_id
            )
        if transaction.purchaser not in transaction.consumers:
            self.send(
                transaction.purchaser,
                "{} не подтвердил покупку".format(user.name),
                forward_messages=transaction.message_id
            )

    def create_transaction(self, purchaser, products, names, message_id):
        transaction = super().create_transaction(purchaser, products, names, message_id)
        for user in transaction.confirmers:
            self.send(
                user,
                message="Подтверждаете покупку? Всего {}₽ (да/нет)".format(transaction.value),
                forward_messages=message_id
            )

    def idle(self):
        try:
            result = self.bot.get_conversations("unread")
        except requests.exceptions.ConnectionError:
            time.sleep(300)
        except requests.exceptions.ReadTimeout:
            time.sleep(600)
        else:
            if result["count"] == 0:
                return
            for conv in result["items"]:
                conv = conv["conversation"]
                peer_id = conv["peer"]["id"]

                history = self.bot.get_history(
                    peer_id,
                    start_message_id=max(conv["in_read"] + 1, conv["out_read"] + 1),
                    count=conv["unread_count"] + 1,
                )

                if peer_id not in self.users_by_id:
                    user = self.add_user(peer_id)
                else:
                    user = self.users_by_id[peer_id]

                messages = history['items'][::-1]
                for i in range(1, len(messages)):
                    if 'reply_message' not in messages[i]:
                        messages[i]['reply_message'] = messages[i - 1]
                    else:
                        messages[i]['reply_message'] = self.bot.get_messages(
                            [messages[i]['reply_message']['id']]
                        )['items'][0]
                    user.answer(messages[i])

                self.bot.mark_as_read(peer_id)
