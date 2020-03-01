import time
import vk
import json
import random
import os
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
        self.consumers = consumers
        self.confirmers = confirmers
        self.message_id = message_id

    def to_json(self):
        return {
            "purchaser": self.purchaser.id,
            "products": [p for p in self.products],
            "consumers": [u.id for u in self.consumers],
            "confirmers": [u.id for u in self.confirmers],
            "message_id": self.message_id
        }


class User:
    HELP_MESSAGES = {'all': "Список доступных команд:\n"
                            "1) Баланс -- узнать балансы пользователей группы\n"
                            "2) Купил -- зарегистрировать покупку\n"
                            "3) Чек -- загрузить чек\n\n"
                            "Для получения более подробной информации о команде наберите: Помощь [команда]",
                     'error': "Неверный синтаксис команды",
                     'баланс': "С помощью этой команды можно узнать балансы всех пользователей вашей группы",
                     'купил':  "С помощью этой команды можно зарегистрировать покупку. После введения необходимых данных "
                               "вам и всем указанным потребителям будет выслан запрос на подтверждение покупки. "
                               "Когда все участники подтвердят покупку, будет произведено обновление их балансов (стоимость "
                               "покупки распределяется равномерно по потребителям). В случае отказа хотя бы одного участника "
                               "покупка считается недействительной. Тогда необходимо устранить причину разногласий участников и "
                               "заново ввести команду.\n\n"
                               "Синтаксис:\n\n"
                               "Купил [потреб. 1] [потреб. 2] ...\n"
                               "[продукт 1] [стоимость]\n"
                               "[продукт 2] [стоимость]\n"
                               "...",
                     "чек" : "С помощью этой команды можно загрузить чек. По введенным данным чек будет искаться в базе сайта "
                             "receipt.taxcom.ru. В случае успеха продукты, указанные в чеке, будут отправлены вам в формате, "
                             "подходящем для команды \"купил\"\n\n"
                             "Синтаксис:\n\n"
                             "1-ый вариант: Чек [ФПД] [сумма расчета]\n"
                             "2-ой вариант: Чек [данные из QR-кода]"
                     }

    def __init__(self, group, name, peer_id, balance = 0):
        self.group = group
        self.name = name
        self.id = peer_id
        self.balance = Currency(balance)


    def to_json(self):
        return {
            "name": self.name,
            "id": self.id,
            "balance": self.balance
        }

    def answer(self, message):
        lines = [line.strip().split(' ') for line in message["text"].split('\n')]
        lines[0][0] = lines[0][0].lower()

        if not lines:
            pass
        elif lines[0][0] == "помощь" and len(lines[0]) > 1:
            if lines[0][1].lower() in self.HELP_MESSAGES:
                self.send(self.HELP_MESSAGES[lines[0][1].lower()])
            else:
                self.send(self.HELP_MESSAGES['error'] + ": команды \"%s\" не существует" % lines[0][1].lower())
        elif lines[0][0] == "помощь":
            self.send(self.HELP_MESSAGES['all'])
        elif lines[0][0] == "купил":
            if len(lines[0]) == 1:
                self.send(self.HELP_MESSAGES['error'] + "\nУкажите потребителей")
                return
            consumers = lines[0][1:]
            if len(lines) == 1:
                self.send(self.HELP_MESSAGES['error'] + "\nУкажите продукты")
                return
            products = []
            for line in lines[1:]:
                try:
                    products.append(Product(' '.join(line[:-1]), line[-1]))
                except:
                    self.send(self.HELP_MESSAGES['error'] + ": ошибка в продукте \"%s\"" % ' '.join(line))
                    return

            self.group.create_transaction(self, products, consumers, message["id"])
        elif lines[0][0] == "чек":
            if len(lines[0]) == 3:
                fiscal_id = lines[0][1]
                receipt_sum = lines[0][2]
                qr_data = "&s=%s&fp=%s" % (receipt_sum, fiscal_id)
            elif len(lines[0]) == 2:
                qr_data = lines[0][1]
            else:
                self.send(self.HELP_MESSAGES['error'] + ". Введите необходимые данные")
                return
            products = [Product(' '.join(p[0].split(' ')), p[1]) for p in get_items(qr_data)]
            if products:
                self.send('\n'.join(map(str, products)))
            else:
                self.send("Чек не найден, проверьте введенные данные")
        elif lines[0][0] == "баланс":
            self.send(
                "\n".join(
                    "Баланс {}: {}₽".format(user.name, user.balance)
                    for user in self.group.users_by_name.values()
                )
            )
        elif lines[0][0] == "да" or lines[0][0] == "нет":
            if message['reply_message']['from_id'] != self.id and "Подтверждаете покупку?" in message['reply_message']['text']:
                transaction_id = message['reply_message']['fwd_messages'][0]['id']
                try:
                    if lines[0][0] == "да":
                        self.group.confirm_transaction(self, transaction_id)
                    elif lines[0][0] == "нет":
                        self.group.decline_transaction(self, transaction_id)
                except KeyError:
                    self.send("Покупка уже завершена")
            else:
                self.send("Неизвестная команда. Если вы хотите ответить на вопрос, который не является последним"
                          " сообщением, то необходимо использовать функцию вк \"ответить\"")
        else:
            self.send("Неизвестная команда")
            self.send(self.HELP_MESSAGES['all'])

    def send(self, message):
        return self.group.send(self, message)

class Group:
    def __init__(self):
        self.session = vk.Session(access_token=open("key.txt").read().strip())
        self.api = vk.API(self.session)
        self.vk_version = "5.103"
        self.users = []
        self.users_by_name = dict()
        self.users_by_id = dict()
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

    def add_user(self, peer_id):
        usr = self.api.users.get(
            v = self.vk_version,
            user_id = peer_id
        )
        user = User(self, usr[0]["first_name"], peer_id)

        self.users.append(user)
        self.users_by_name[user.name] = user
        self.users_by_id[peer_id] = user

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
        except Exception as e:
            self.send(self.users_by_name["Дима"], e)
            self.send(self.users_by_name["Ваня"], e)
        finally:
            try:
                self.save(open("data_tmp.json", "w", encoding='utf-8'))
            except Exception:
                raise
            else:
                os.rename("data_tmp.json", "data.json")

    def send(self, user, message, *args, **kwargs):
        return self.api.messages.send(
            v = self.vk_version,
            peer_id = user.id,
            random_id = random.random(),
            message = message,
            *args, **kwargs
        )

    def make_transaction(self, transaction):
        val_per_usr = transaction.value / len(transaction.consumers)
        transaction.purchaser.balance += val_per_usr * len(transaction.consumers)
        for user in transaction.consumers:
            user.balance -= val_per_usr

    def confirm_transaction(self, user, transaction_id):
        transaction = self.transactions_by_id[transaction_id]
        transaction.confirmers.remove(user)

        if not transaction.confirmers:
            self.make_transaction(transaction)
            self.send(
                transaction.purchaser,
                "Покупка подтверждена\n",
                forward_messages = transaction.message_id
            )
            self.send(
                transaction.purchaser,
                "\n".join(
                    "Баланс {}: {}₽".format(user.name, user.balance)
                    for user in self.users_by_name.values()
                )
            )
            del self.transactions_by_id[transaction.message_id]

    def decline_transaction(self, user, transaction_id):
        transaction = self.transactions_by_id[transaction_id]
        for consumer in transaction.consumers:
            self.send(
                consumer,
                "{} не подтвердил покупку".format(user.name),
                forward_messages = transaction.message_id
            )
        if transaction.purchaser not in transaction.consumers:
            self.send(
                transaction.purchaser,
                "{} не подтвердил покупку".format(user.name),
                forward_messages=transaction.message_id
            )
        del self.transactions_by_id[transaction.message_id]

    def create_transaction(self, purchaser, products, consumers, message_id):
        for i in range(len(consumers)):
            if consumers[i] in self.users_by_name:
                consumers[i] = self.users_by_name[consumers[i]]
            else:
                purchaser.send("Пользователя с именем \"%s\" нет в вашей группе" % consumers[i])
                return
        confirmers = consumers.copy()
        if purchaser not in consumers:
            confirmers.append(purchaser)
        transaction = Transaction(purchaser, products, consumers, confirmers, message_id)
        self.transactions_by_id[message_id] = transaction

        for user in confirmers:
            self.send(
                user,
                message = "Подтверждаете покупку? Всего {}₽".format(transaction.value),
                forward_messages = message_id
            )

    def idle(self):
        result = self.api.messages.getConversations(
            v = self.vk_version,
            filter = "unread"
        )
        if result["count"] == 0:
            return
        for conv in result["items"]:
            conv = conv["conversation"]
            peer_id = conv["peer"]["id"]

            history = self.api.messages.getHistory(
                v = self.vk_version,
                peer_id = peer_id,
                start_message_id = max(conv["in_read"] + 1, conv["out_read"] + 1),
                count = conv["unread_count"] + 1,
            )

            user = None
            if peer_id not in self.users_by_id:
                user = self.add_user(peer_id)
            else:
                user = self.users_by_id[peer_id]

            messages = history['items'][::-1]
            for i in range(1, len(messages)):
                if 'reply_message' not in messages[i]:
                    messages[i]['reply_message'] = messages[i-1]
                else:
                    messages[i]['reply_message'] = self.api.messages.getById(
                        v = self.vk_version,
                        message_ids = [messages[i]['reply_message']['id']]
                    )['items'][0]
                user.answer(messages[i])

            self.api.messages.markAsRead(
                v = self.vk_version,
                peer_id = peer_id
            )


def main():
    app = Group()
    app.run()


if __name__ == "__main__":
    main()
