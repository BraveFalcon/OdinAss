from Base import Base


class User(Base):
    __slots__ = ["id", "name", "credit"]

    def update(self, name, credit):
        self.name = name
        self.credit = int(credit)


def test():
    User.test(200, "Dmitry", 100)


if __name__ == '__main__':
    test()
