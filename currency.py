from decimal import Decimal


class Currency:
    def __init__(self, value=0.0):
        if isinstance(value, str):
            value = Decimal(value)
        elif isinstance(value, Currency):
            self.cents = value.cents
            return
        self.cents = int(value * 100)

    def to_json(self):
        # return "{}.{:0>2}".format(self.cents // 100, self.cents % 100)
        return "%.2f" % (self.cents / 100)

    def to_number(self):
        return self.cents / 100

    def __int__(self):
        return self.to_json()

    def __add__(self, other):
        other = Currency(other)
        other.cents += self.cents
        other.cents = int(other.cents)
        return other

    __radd__ = __add__

    def __iadd__(self, other):
        other = Currency(other)
        self.cents += other.cents
        self.cents = int(self.cents)
        return self

    def __neg__(self):
        res = Currency()
        res.cents = - self.cents
        return res

    def __sub__(self, other):
        other = Currency(other)
        other.cents = self.cents - other.cents
        return other

    def __rsub__(self, other):
        return Currency(other) - self

    def __isub__(self, other):
        other = Currency(other)
        self.cents -= other.cents
        self.cents = int(self.cents)
        return self

    def __mul__(self, other):
        res = Currency()
        res.cents = self.cents * other
        res.cents = int(res.cents)
        return res

    __rmul__ = __mul__

    def __imul__(self, other):
        self.cents *= other
        self.cents = int(self.cents)
        return self

    def __div__(self, other):
        res = Currency()
        res.cents = self.cents / other
        res.cents = int(res.cents)
        return res

    def __rdiv__(self, other):
        return other / self.to_number()

    def __idiv__(self, other):
        self.cents /= other
        self.cents = int(self.cents)
        return self

    def __truediv__(self, other):
        res = Currency()
        res.cents = self.cents / other
        res.cents = int(res.cents)
        return res

    def __rtruediv__(self, other):
        return other / self.to_number()

    def __floordiv__(self, other):
        res = Currency()
        res.cents = self.cents // other
        res.cents = int(res.cents)
        return res

    def __rfloordiv__(self, other):
        return other // self.to_number()

    def __str__(self):
        return self.to_json()

    def __float__(self):
        return self.to_number()


def test():
    x = Currency(1.05)
    y = Currency(0.5)
    print(y - x)


if __name__ == "__main__":
    test()
