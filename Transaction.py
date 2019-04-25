import time as Time
from Base import Base


class Transaction(Base):
    __slots__ = ["id", "time", "amount", "info"]
    TIME_FORMAT = "%d.%b.%Y %H:%M"
    ALIASES = {
        "time": "time_str"
    }

    @property
    def time_str(self):
        return Time.strftime(self.TIME_FORMAT, self.time)

    def update(self, time, amount, info=None):
        if isinstance(time, str):
            time = Time.strptime(time, self.TIME_FORMAT)
        self.time = time

        self.amount = int(amount)

        if info is None:
            info = ""

        self.info = info


def test():
    now = Time.gmtime()
    Transaction.test(20, now, 10, "some info")


if __name__ == '__main__':
    test()
