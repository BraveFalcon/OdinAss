from group import BaseGroup
from user import User


class MockBot:
    def __init__(self):
        self.messages = dict()
        self.msg_id = 0

    def create_message(self, text, *args, **kwargs):
        message = {
            "text": text,
            "id": self.msg_id
        }
        message.update(kwargs)
        self.messages[self.msg_id] = message
        self.msg_id += 1
        return message


class MockGroup(BaseGroup):
    def __init__(self):
        super().__init__()
    
    def save_data(self):
        pass

    def send(self, user, message):
        print(message)
    
    def confirm_transaction(self, user, transaction_id):
        transaction = super().confirm_transaction(user, transaction_id)
        print("Confirm transaction: transaction = {}".format(transaction))
    
    def decline_transaction(self, user, transaction_id):
        transaction = super().decline_transaction(user, transaction_id)
        print("Cancel transaction: transaction = {}".format(transaction))
    
    def create_transaction(self, purchaser, products, consumers, message_id):
        super().create_transaction(purchaser, products, consumers, message_id)
        print("Create transaction: purchaser = {0}, products = {1}, consumers = {2}, message_id = {3}"
            .format(purchaser, products, consumers, message_id))


bot = MockBot()
group = MockGroup()
group.load(open("data.json", encoding='utf-8'))
user = group.users_by_name["Дима"]

user.answer(bot.create_message("?"))
user.answer(bot.create_message("? ?"))
user.answer(bot.create_message("? $"))
user.answer(bot.create_message("? купил"))
user.answer(bot.create_message("? чек"))
user.answer(bot.create_message("? +"))
user.answer(bot.create_message("? -"))
user.answer(bot.create_message("$"))
user.answer(bot.create_message("чек 2478417427 1532.00"))
user.answer(bot.create_message("чек &s=1532.00&fn=9251440300215132&fp=2478417427"))
user.answer(bot.create_message("купил Ваня\nмолоко аыфдвлаодылва 100\nпомидоры алыдвофдалофыду 200"))

msg_buy1 = bot.create_message("купил Дима Ваня\nмолоко аыфдвлаодылва 100\nпомидоры алыдвофдалофыду 200")
user.answer(msg_buy1)
msg_answer1 = bot.create_message(
    "Подтверждаете покупку?",
    from_id=0,
    fwd_messages=[msg_buy1]
)

msg_buy2 = bot.create_message("купил все\nмолоко аыфдвлаодылва 100\nпомидоры алыдвофдалофыду 200")
user.answer(msg_buy2)
msg_answer2 = bot.create_message(
    "Подтверждаете покупку?",
    from_id=0,
    fwd_messages=[msg_buy2]
)

user.answer(bot.create_message("+", reply_message=msg_answer1))
user.answer(bot.create_message("-", reply_message=msg_answer2))
user.answer(bot.create_message("+ всё"))
user.answer(bot.create_message("- все"))
