import time
import vk
import json
import random
from taxcom_parser import get_items, Currency


def to_json(o):
    return o.to_json()


class Product:
    def __init__(self, name, cost):
        self.name = name
        self.cost = Currency(cost)
    
    def __str__(self):
        return "{} {}".format(self.name, self.cost)
    
    def to_json(self):
        return [self.name, self.cost.to_json()]
    

class Transaction:
    def __init__(self, purchaser, products, consumers, confirmers, message_id):
        self.purchaser = purchaser
        self.products = products
        self.value = sum(map(lambda x: x.cost, products))
        print("Value: ", self.value)
        self.consumers = consumers
        self.confirmers = confirmers
        self.message_id = message_id
    
    def to_json(self):
        return {
            "purchaser": self.purchaser.peer_id,
            "products": [p for p in self.products],
            "consumers": [u.peer_id for u in self.consumers],
            "confirmers": [u.peer_id for u in self.confirmers],
            "message_id": self.message_id
        }


class User:
    HELP_MESSAGE = \
'''
Список доступных команд:
1) помощь -- показать это сообщение
2) купил -- зарегистрировать единичную покупку
3) чеки -- загрузить чеки
'''

    def __init__(self, group, name, peer_id, balance = 0, transactions = []):
        self.group = group
        self.name = name
        self.peer_id = peer_id
        self.balance = Currency(balance)

        if transactions is None:
            transactions = []
        self.transactions = transactions
    
    def to_json(self):
        return {
            "name": self.name,
            "peer_id": self.peer_id,
            "balance": self.balance,
            "transactions": [t.message_id for t in self.transactions]
        }
    
    def answer(self, message):
        lines = [line.strip().split(' ') for line in message["text"].split('\n')]
        lines[0][0] = lines[0][0].lower()

        if not lines:
            pass
        elif lines[0][0] == "помощь":
            self.send(self.HELP_MESSAGE)
        elif lines[0][0] == "купил":
            consumers = lines[0][1:]
            products = [Product(' '.join(line[:-1]), line[-1]) for line in lines[1:]]
            self.group.begin_transaction(self, products, consumers, message["id"])
        elif lines[0][0] == "чеки":
            consumers = lines[0][1:]
            products = []
            for line in lines[1:]:
                fiscal_id = line[0] if len(line) > 0 else 0  # TODO: ask for fiscal_id
                receipt_sum = line[1] if len(line) > 1 else 0  # TODO: ask for receipt_sum
                products += [Product(' '.join(p[0].split(' ')[:2]), p[1]) for p in get_items(fiscal_id, receipt_sum)]
            self.send(
                "купил " + ' '.join(consumers) + '\n' +\
                '\n'.join(map(str, products))
            )
            # self.group.begin_transaction(self, products, consumers, message_id)
        elif lines[0][0] == "баланс":
            self.send(
                "\n".join(
                    "Баланс {}: {}".format(user.name, user.balance)
                    for user in self.group.users_by_name.values()
                )
            )
        elif self.transactions:
            if lines[0][0] == "да":
                self.group.confirm_transaction(self, self.transactions.pop())
            elif lines[0][0] == "нет":
                self.group.decline_transaction(self, self.transactions.pop())
            else:
                self.send("Неизвестная команда2\n\n" + self.HELP_MESSAGE)
        else:
            self.send("Неизвестная команда\n\n" + self.HELP_MESSAGE)
    
    def send(self, message):
        return self.group.send(self, message)

class Group:
    def __init__(self):
        self.session = vk.Session(access_token=open("key.txt").read().strip())
        self.api = vk.API(self.session)
        self.v = "5.103"
        self.users = []
        self.users_by_name = dict()
        self.users_by_peer = dict()
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
                u["peer_id"],
                u["balance"],
                u["transactions"]
            )
            self.users.append(u)
            self.users_by_name[u.name] = u
            self.users_by_peer[u.peer_id] = u
        
        for t in res["transactions"]:
            t = Transaction(
                self.users_by_peer[t["purchaser"]],
                [Product(p[0], p[1]) for p in t["products"]],
                [self.users_by_peer[peer_id] for peer_id in t["consumers"]],
                {self.users_by_peer[peer_id] for peer_id in t["confirmers"]},
                t["message_id"]
            )
            self.transactions_by_id[t.message_id] = t
        
        for u in self.users:
            u.transactions = [self.transactions_by_id[t] for t in u.transactions]
    
    def save(self, stream):
        json.dump(
            self.to_json(),
            stream,
            ensure_ascii=False,
            indent=4,
            default=to_json
        )
    
    def add_user(self, peer_id):
        usr = self.api.users.get(
            v = self.v,
            user_id = peer_id
        )
        user = User(self, usr[0]["first_name"], peer_id)

        self.users.append(user)
        self.users_by_name[user.name] = user
        self.users_by_peer[peer_id] = user

        return user
        
    def run(self):
        try:
            self.load(open("data.json", encoding='utf-8'))
        except:
            pass
        try:
            while True:
                self.idle()
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        except:
            raise
        finally:
            self.save(open("data.json", "w", encoding='utf-8'))
    
    def send(self, user, message, *args, **kwargs):
        return self.api.messages.send(
            v = self.v,
            peer_id = user.peer_id,
            random_id = random.random(),
            message = message,
            *args, **kwargs
        )
    
    def make_transaction(self, transaction):
        value = transaction.value / len(transaction.consumers)
        trv = value * len(transaction.consumers)
        transaction.purchaser.balance += trv
        print(trv, value, transaction.purchaser.balance)
        for user in transaction.consumers:
            user.balance -= value
    
    def confirm_transaction(self, user, transaction):
        transaction.confirmers.remove(user)

        if not transaction.confirmers:
            self.make_transaction(transaction)

            # for consumer in transaction.consumers:
            self.send(
                transaction.purchaser,
                "Транзакция подтверждена\nВаш текущий баланс: {}".format(transaction.purchaser.balance),
                forward_messages = transaction.message_id
            )
            
            del self.transactions_by_id[transaction.message_id]
    
    def decline_transaction(self, user, transaction):
        for consumer in transaction.consumers:
            self.send(
                consumer,
                "{} отменил транзакцию".format(user.name),
                forward_messages = transaction.message_id
            )
            if consumer is not user:
                consumer.transactions.remove(transaction)

        del self.transactions_by_id[transaction.message_id]
    
    def begin_transaction(self, purchaser, products, consumers, message_id):
        consumers = [self.users_by_name[name] for name in consumers]
        confirmers = { c for c in consumers }# if c is not purchaser }
        confirmers.add(purchaser)
        transaction = Transaction(purchaser, products, consumers, confirmers, message_id)
        self.transactions_by_id[message_id] = transaction

        for user in confirmers:
            self.send(
                user,
                message = "Подтверждаете транзакцию? Всего: {}".format(transaction.value),
                forward_messages = message_id
            )
            user.transactions.append(transaction)
        
        if not confirmers:
            self.make_transaction(transaction)
    
    def idle(self):
        result = self.api.messages.getConversations(
            v = self.v,
            filter = "unread"
        )
        if result["count"] == 0:
            return
        for conv in result["items"]:
            conv = conv["conversation"]
            peer_id = conv["peer"]["id"]

            history = self.api.messages.getHistory(
                v = self.v,
                peer_id = peer_id,
                start_message_id = max(conv["in_read"] + 1, conv["out_read"] + 1),
                count = conv["unread_count"],
            )
            
            user = None
            if peer_id not in self.users_by_peer:
                user = self.add_user(peer_id)
            else:
                user = self.users_by_peer[peer_id]
            
            for h in history["items"]:
                if h["from_id"] != user.peer_id:
                    continue
                user.answer(h)
            
            self.api.messages.markAsRead(
                v = self.v,
                peer_id = peer_id
            )


def main():
    app = Group()
    app.run()


if __name__ == "__main__":
    main()
