from currency import Currency
from product import Product
from taxcom_parser import get_items
from route import route, Router


class User(Router):
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
        lines = [x.strip() for x in message["text"].split("\n")]

        if not lines:
            return
        
        a = self.find_route(lines[0])
        if a is None or len(a) < 2:
            self.send("Неизвестная команда")
            self.do_help()
            return
        route, line = a
        if not line:
            lines.pop(0)
        else:
            lines[0] = line
        try:
            route.func(self, message, *lines)
        except TypeError:
            self.error_wrong_syntax()
    
    def error_wrong_syntax(self, info = None):
        msg = "Неверный синтаксис команды"
        if info is not None:
            msg += ":\n" + info
        self.send(msg)

    @route(
        name = "помощь",
        description = "получить список и синтаксис команд",
        aliases = ["?"]
    )
    def do_help(self, message = None, command = None):
        if not self.do_help.help:  # lazy auto help
            msg = "Список доступных команд:\n"
            for i, route in enumerate(self.routes, 1):
                msg += "{0}) {1} -- {2}\n".format(i, route.name.capitalize(), route.description.capitalize())
            msg += "\nДля получения более подробной информации о команде наберите: Помощь [команда]"
            self.do_help.help = msg

        if command is None:
            return self.send(self.do_help.help)
        
        while command:
            route, line = self.find_route(command)
            if route is None or line is None:
                return self.error_wrong_syntax("команды {} не существует".format(command))
            
            self.send(route.help)
            command = line
    
    @route(
        name = "баланс",
        description = "узнать балансы пользователей группы",
        help = "С помощью этой команды можно узнать балансы всех пользователей вашей группы",
        aliases = ["$"]
    )
    def do_balance(self, message = None):
        self.send(
            "\n".join(
                "Баланс {}: {}₽".format(user.name, user.balance)
                for user in self.group.users_by_name.values()
            )
        )
    
    @route(
        name = "купил",
        description = "зарегистрировать покупку",
        help =  "С помощью этой команды можно зарегистрировать покупку. После введения необходимых данных "
                "вам и всем указанным потребителям будет выслан запрос на подтверждение покупки. "
                "Когда все участники подтвердят покупку, будет произведено обновление их балансов (стоимость "
                "покупки распределяется равномерно по потребителям). В случае отказа хотя бы одного участника "
                "покупка считается недействительной. Тогда необходимо устранить причину разногласий участников и "
                "заново ввести команду.\n\n"
                "Синтаксис:\n\n"
                "Купил [потреб. 1] [потреб. 2] | все ...\n"
                "[продукт 1] [стоимость]\n"
                "[продукт 2] [стоимость]\n"
                "..."
    )
    def do_bought(self, message, consumers = None, *lines):
        if consumers is None:
            return self.error_wrong_syntax("Укажите потребителей")
        if not lines:
            return self.error_wrong_syntax("Укажите продукты")
        consumers = consumers.split(' ')
        products = []
        for line in lines:
            try:
                products.append(Product(*line.rsplit(' ', 1)))
            except:
                return self.error_wrong_syntax("ошибка в продукте {}".format(repr(line)))

        self.group.create_transaction(self, products, consumers, message["id"])
    
    @route(
        name = "чек",
        description = "загрузить чек",
        help =  "С помощью этой команды можно загрузить чек. По введенным данным чек будет искаться в базе сайта "
                "receipt.taxcom.ru. В случае успеха продукты, указанные в чеке, будут отправлены вам в формате, "
                "подходящем для команды \"купил\"\n\n"
                "Синтаксис:\n\n"
                "1-ый вариант: Чек [ФПД] [сумма расчета]\n"
                "2-ой вариант: Чек [данные из QR-кода]"
    )
    def do_recipe(self, message, check):
        s = check.split(' ')
        qr_data = None
        if len(s) == 2:
            fiscal_id, receipt_sum = s
            qr_data = "&s={0}&fp={1}".format(receipt_sum, fiscal_id)
        elif len(s) == 1:
            qr_data = check
        else:
            return self.error_wrong_syntax("Введите необходимые данные")
        products = [Product(' '.join(p[0].split(' ')), p[1]) for p in get_items(qr_data)]
        if products:
            self.send('\n'.join(map(str, products)))
        else:
            self.send("Чек не найден, проверьте введенные данные")
    
    @route(
        name = "подтвердить",
        description = "подтвердить покупки",
        help = "",  # TODO
        aliases = ["да", "д", "+", "yes", "y"]
    )
    def do_accept(self, message, all = None):
        if all is not None:
            if all in ("все", "всё"):
                for transaction_id, transaction in tuple(self.group.transactions_by_id.items()):
                    if self in transaction.confirmers:
                        self.group.confirm_transaction(self, transaction_id)
                self.send("Все покупки, в которых вы участвуете, успешно подтверждены")
            else:
                self.error_wrong_syntax()  # TODO
            return
        
        if message['reply_message']['from_id'] != self.id and\
                "Подтверждаете покупку?" in message['reply_message']['text']:
            transaction_id = message['reply_message']['fwd_messages'][0]['id']
            try:
                self.group.confirm_transaction(self, transaction_id)
            except KeyError:
                self.send("Покупка уже завершена")
        else:
            self.send("Неизвестная команда. Если вы хотите ответить на вопрос, который не является последним"
                        " сообщением, то необходимо использовать функцию вк \"ответить\"")
    
    @route(
        name = "отменить",
        description = "отменить покупки",
        help = "",  # TODO
        aliases = ["нет", "н", "no", "n", "-"]
    )
    def do_refuse(self, message, all = None):
        if all is not None:
            if all in ("все", "всё"):
                for transaction_id, transaction in tuple(self.group.transactions_by_id.items()):
                    if self in transaction.confirmers:
                        self.group.decline_transaction(self, transaction_id)
                self.send("Все покупки, в которых вы участвуете, отменены")
            else:
                self.error_wrong_syntax()  # TODO
            return
        
        if message['reply_message']['from_id'] != self.id and\
                "Подтверждаете покупку?" in message['reply_message']['text']:
            transaction_id = message['reply_message']['fwd_messages'][0]['id']
            try:
                self.group.decline_transaction(self, transaction_id)
            except KeyError:
                self.send("Покупка уже завершена")
        else:
            self.send("Неизвестная команда. Если вы хотите ответить на вопрос, который не является последним"
                        " сообщением, то необходимо использовать функцию вк \"ответить\"")

    def send(self, message):
        return self.group.send(self, message)
