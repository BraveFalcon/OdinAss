import vk
import json
from random import random
from functools import reduce
from taxcom_parser import get_items


class Peer:
    def __init__(self, conv):
        self.id = conv["peer"]["id"]
        self.last_read = conv["in_read"]


class Bot:
    v = "5.95"
    DEFAULT_PATH = "Bot.data"

    def __init__(self, key):
        self.key = key
        self.user_session = vk.AuthSession(
            scope="wall",
            app_id=key[0],
            user_login=key[1],
            user_password=key[2]
        )
        self.community_session = vk.Session(access_token=key[3])
        self.cached_polls = None
        self.as_community()

    def as_user(self):
        self.api = vk.API(self.user_session)

    def as_community(self):
        self.api = vk.API(self.community_session)

    def create_polls(self, receipt):
        polls = []
        self.as_user()
        first = True
        i = 0
        while i < len(receipt):
            polls.append(self.api.polls.create(
                v = self.v,
                question = "Что ты используешь?" if first else "\u2800",
                is_multiple = 1,
                add_answers = json.dumps(tuple(map(
                    lambda x: "{0}) {1} {2}".format(
                        x[0],
                        ' '.join(x[1][0].split()[:2]), x[1][1]
                    ),
                    zip(range(i + 1, i + 11), receipt[i:i + 10])
                )))
            ))
            first = False
            i += 10
        self.as_community()
        return polls

    def save(self, stream=None):
        if stream is None:
            stream = open(self.DEFAULT_PATH, "w")
        print(", ".join(str(i) for i in self.cached_polls), file=stream)

    def load(self, stream=None):
        if stream is None:
            stream = open(self.DEFAULT_PATH)
        self.cached_polls = map(int, stream.readline().split(', '))

    def process_receipt(self, fn, sum):
        receipt = get_items(fn, sum)
        polls = self.create_polls(receipt)
        res = self.api.messages.getConversations(v=self.v)
        if res["count"] > 0:
            for x in res["items"]:
                conv = x["conversation"]
                lm = x["last_message"]
                p = Peer(conv)
                for poll in polls:
                    self.send_attachment(
                        p,
                        "poll{owner_id}_{id}".format(**poll)
                    )
                self.mark_as_read(p)
        self.cached_polls = [poll["id"] for poll in polls]

    def get_answers(self):
        if self.cached_polls is not None:
            self.as_user()
            voters = []
            for poll in self.cached_polls:
                answers = self.api.polls.getById(
                    v = self.v,
                    poll_id = poll
                )["answers"]
                voters += self.api.polls.getVoters(
                    v = self.v,
                    poll_id = poll,
                    answer_ids = ','.join(str(x["id"]) for x in answers)
                )
            self.as_community()
            return voters

    def get_history(self, peer):
        return self.api.messages.get_history(
            v = self.v,
            peer_id = peer.id,
            start_message_id = -peer.last_read
        )

    def mark_as_read(self, peer):
        return self.api.messages.mark_as_read(
            v = self.v,
            peer_id = peer.id
        )

    def send(self, peer, msg):
        return self.api.messages.send(
            v = self.v,
            random_id = random(),
            peer_id = peer.id,
            message = msg
        )

    def send_attachment(self, peer, attachment):
        self.api.messages.send(
            v = self.v,
            random_id = random(),
            peer_id = peer.id,
            attachment = attachment
        )
