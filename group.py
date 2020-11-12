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


class Group:
    def __init__(self):
        self.session = vk.Session(access_token=open("key.txt").read().strip())
        self.api = vk.API(self.session)
        self.vk_version = "5.103"
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
            u = User(
                self,
                u["name"],
                u["id"],
                u["balance"]
            )
            self.users.append(u)
            self.users_by_name[u.name] = u
            self.users_by_id[u.id] = u

        for t in res["transactions"]:
            t = Transaction(
                self.users_by_id[t["purchaser"]],
                [Product(p[0], p[1]) for p in t["products"]],
                [self.users_by_id[id] for id in t["consumers"]],
                {self.users_by_id[id] for id in t["confirmers"]},
                t["message_id"]
            )
            self.transactions_by_id[t.message_id] = t

    def save(self, stream):
        json.dump(
            self.to_json(),
            stream,
            ensure_ascii=False,
            indent=4,
            default=to_json
        )

    def save_data(self):
        try:
            self.save(open("data_tmp.json", "w", encoding='utf-8'))
        except Exception as e:
            self.send_admins(e)
        else:
            os.remove("data.json")
            os.rename("data_tmp.json", "data.json")

    def add_user(self, peer_id):
        usr = self.api.users.get(
            v=self.vk_version,
            user_id=peer_id
        )
        user = User(self, usr[0]["first_name"], peer_id)

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
        return self.api.messages.send(
            v=self.vk_version,
            peer_id=user.id,
            random_id=random.random(),
            message=message,
            *args, **kwargs
        )

    def send_admins(self, message):
        for id in self.admins_id:
            self.send(self.users_by_id[id], message)

    def make_transaction(self, transaction):
        val_per_usr = transaction.value / len(transaction.consumers)
        transaction.purchaser.balance += val_per_usr * len(transaction.consumers)
        for user in transaction.consumers:
            user.balance -= val_per_usr
        self.save_data()

    def confirm_transaction(self, user, transaction_id):
        transaction = self.transactions_by_id[transaction_id]
        if user not in transaction.confirmers:
            self.send(
                user,
                "Покупка уже была подтверждена\n"
            )
            return
        transaction.confirmers.remove(user)

        if not transaction.confirmers:
            self.make_transaction(transaction)
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
            del self.transactions_by_id[transaction.message_id]
        self.save_data()

    def decline_transaction(self, user, transaction_id):
        transaction = self.transactions_by_id[transaction_id]
        del self.transactions_by_id[transaction_id]
        self.save_data()
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
        consumers = []

        for name in names:
            if name in self.users_by_name:
                consumers.append(self.users_by_name[name])
            elif name in ("все", "всем"):
                consumers = self.users
                break
            else:
                purchaser.send("Пользователя с именем \"%s\" нет в вашей группе" % name)
                return

        confirmers = consumers.copy()
        if purchaser not in consumers:
            confirmers.append(purchaser)
        transaction = Transaction(purchaser, products, consumers, confirmers, message_id)
        self.transactions_by_id[message_id] = transaction
        self.save_data()
        for user in confirmers:
            self.send(
                user,
                message="Подтверждаете покупку? Всего {}₽ (да/нет)".format(transaction.value),
                forward_messages=message_id
            )

    def idle(self):
        try:
            result = self.api.messages.getConversations(
                v=self.vk_version,
                filter="unread"
            )
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

                history = self.api.messages.getHistory(
                    v=self.vk_version,
                    peer_id=peer_id,
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
                        messages[i]['reply_message'] = self.api.messages.getById(
                            v=self.vk_version,
                            message_ids=[messages[i]['reply_message']['id']]
                        )['items'][0]
                    user.answer(messages[i])

                self.api.messages.markAsRead(
                    v=self.vk_version,
                    peer_id=peer_id
                )
