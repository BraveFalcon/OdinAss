

class User:
    def __init__(self, id, name, credit=0):
        self.credit = credit
        self.name = name
        self.id = id

    def __str__(self):
        return self.name

    DEFAULT_PATH = "User{}.name"

    @property
    def default_path(self):
        return self.DEFAULT_PATH.format(self.name)

    def save(self, stream=None):
        if stream is None:
            stream = open(self.default_path, "w")
        print("{0.name} {0.credit}".format(self), file=stream)

    def load(self, stream=None):
        if stream is None:
            # ???
            # We can't construct default_path
            raise ValueError("stream shouldn't be None")
        self.name, self.credit = stream.getline().split()


class Group:
    def __init__(self, users):
        self._admin_id = 0
        self.users = users
        self._trs = []

    def perform(self, tr):
        print("Performing transaction {}".format(tr))
        tr.owner.credit -= tr.amount
        if tr.target is not None:
            tr.target.credit += tr.amount
        self._trs.append(tr)


now = time.gmtime()
users = [
    User("Dima"),
    User("Timur")
]
trs = [
    Transaction(now, 10, users[0]),
    Transaction(now, 10, users[0], users[1])
]
gr = Group(users)
gr.perform(trs[0])
gr.perform(trs[0])











class Product:
    def __init__(self, name, cost, date):
        self.name = str(name)
        self.cost = float(cost)
        self.date = time.date(date)


class Receipt:
    def __init__(self, products):
        self.products = tuple(products)

    @classmethod
    def from_url(cls, url):
        items, date = get_items(url)
        if not items:
            raise ValueError
        return cls((Product(x[0], x[1], date)))


class Week:
    def __init__(self, polls, answers):
        self.polls = list(polls)
        self.answers = dict(answers)


class Transaction(Product):
    def __init__(self, name, cost, date, sender, destination):
        super().__init__(name, cost, date)
        self.sender = sender
        self.destination = destination


class User:
    def __init__(self, name, credit):
        self.name = str(name)
        self.credit = float(credit)


class Group:
    v = "5.95"

    def __init__(self, users, user_api, community_api):
        self.users = users
        self.user_api = user_api
        self.community_api = community_api

    @classmethod
    def from_key(cls, key):
        user_api = vk.Api(vk.AuthSession(
            scope="wall",
            app_id=key[0],
            user_login=key[1],
            user_password=key[2]
        ))
        community_api = vk.Api(vk.Session(access_token=key[3]))
        conv = community_api.getConversations(v = cls.v)
        users = { x["peer"]["id"]: User(0) }
        return cls(users, user_api, community_api)

    def send_receipt(self, receipt):
        poll_ids = []
        answers = {}
        while i < len(receipt.products):
            part = receipt.products[i:i + 10]
            poll = self.user_api.polls.create(
                v = self.v,
                question = "Что ты используешь?" if first else "\u2800",
                is_multiple = 1,
                add_answers = json.dumps(tuple(map(
                    lambda x: "{0}) {1} {2}".format(
                        x[0],
                        ' '.join(x[1][0].split()[:2]), x[1][1]
                    ),
                    zip(range(i + 1, i + 11), part)
                )))
            )
            poll_id = poll["id"]
            poll_ids.append(poll_id)
            answers.update(zip(map(lambda x: x["id"], poll["answers"]), part))
            first = False
            i += 10
        return Week(poll_ids, answers)

    def get_answers(self, week):
        transactions = []
        for poll in week.polls:
            votes = self.user_api.polls.getVoters(
                v = self.v,
                poll_id = poll,
                answer_ids = ','.join(str(x) for x in week.answers.keys())
            )
            for vote in votes:
                product = week.answers[vote["answer_id"]]
