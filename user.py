from currency import Currency
from product import Product
from taxcom_parser import get_items


class User:
    HELP_MESSAGES = {'all': "Список доступных команд:\n"
                            "1) Баланс -- узнать балансы пользователей группы\n"
                            "2) Купил -- зарегистрировать покупку\n"
                            "3) Чек -- загрузить чек\n"
                            "4) Подтвердить все -- подтверждение всех покупок\n\n"
                            "Для получения более подробной информации о команде наберите: Помощь [команда]",
                     'error': "Неверный синтаксис команды",
                     'баланс': "С помощью этой команды можно узнать балансы всех пользователей вашей группы",
                     'купил': "С помощью этой команды можно зарегистрировать покупку. После введения необходимых данных "
                              "вам и всем указанным потребителям будет выслан запрос на подтверждение покупки. "
                              "Когда все участники подтвердят покупку, будет произведено обновление их балансов (стоимость "
                              "покупки распределяется равномерно по потребителям). В случае отказа хотя бы одного участника "
                              "покупка считается недействительной. Тогда необходимо устранить причину разногласий участников и "
                              "заново ввести команду.\n\n"
                              "Синтаксис:\n\n"
                              "Купил [потреб. 1] [потреб. 2] | все ...\n"
                              "[продукт 1] [стоимость]\n"
                              "[продукт 2] [стоимость]\n"
                              "...",
                     "чек": "С помощью этой команды можно загрузить чек. По введенным данным чек будет искаться в базе сайта "
                            "receipt.taxcom.ru. В случае успеха продукты, указанные в чеке, будут отправлены вам в формате, "
                            "подходящем для команды \"купил\"\n\n"
                            "Синтаксис:\n\n"
                            "1-ый вариант: Чек [ФПД] [сумма расчета]\n"
                            "2-ой вариант: Чек [данные из QR-кода]",
                     "подтвердить все": "Подтверждение всех покупок, в которых вы участвуете"
                     }

    def __init__(self, group, name, peer_id, balance=0):
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
            if " ".join(lines[0][1:]).lower() in self.HELP_MESSAGES:
                self.send(self.HELP_MESSAGES[" ".join(lines[0][1:]).lower()])
            else:
                self.send(self.HELP_MESSAGES['error'] + ": команды \"%s\" не существует" % lines[0][1].lower())
        elif lines[0][0] == "помощь":
            self.send(self.HELP_MESSAGES['all'])
        elif "подтвердить все" in " ".join(lines[0]):
            for transaction_id, transaction in tuple(self.group.transactions_by_id.items()):
                if self in transaction.confirmers:
                    self.group.confirm_transaction(self, transaction_id)
            self.send("Все покупки, в которых вы участвуете, успешно подтверждены\n")
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
            if message['reply_message']['from_id'] != self.id and "Подтверждаете покупку?" in message['reply_message'][
                'text']:
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
