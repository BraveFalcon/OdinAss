from currency import Currency


class Product:
    def __init__(self, name, cost):
        self.name = name
        self.cost = Currency(cost)

    def __str__(self):
        return "{} {}".format(self.name, self.cost)

    def to_json(self):
        return [self.name, self.cost.to_json()]
