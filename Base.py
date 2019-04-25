import io


class Base:
    INSTANCES = dict()
    DEFAULT_PATH = "{0.class_name}{0.id}.data"
    ALIASES = dict()
    DELIMITER = ', '

    @property
    def default_path(self):
        return self.DEFAULT_PATH.format(self)

    @property
    def class_name(self):
        return self.__class__.__name__

    def save(self, stream=None):
        if stream is None:
            stream = open(self.default_path, "w")
        if isinstance(stream, str):
            stream = open(stream, "w")
        stream.write(self.class_name)
        stream.write(self.DELIMITER)
        stream.write(self.DELIMITER.join(
            str(getattr(self, self.ALIASES.get(i, i))) for i in self.__slots__
        ))

    def __init__(self, id):
        self.id = id
        self.load = self.load_instance
        self.INSTANCES[self.id] = self

    def __str__(self):
        return repr(self)

    def __repr__(self):
        res = io.StringIO()
        self.save(res)
        return res.getvalue()

    def __eq__(self, other):
        if self is other:
            return True
        return all(
            getattr(self, i) == getattr(other, i) for i in self.__slots__
        )

    def load_instance(self, stream=None):
        if isinstance(stream, str):
            stream = open(stream)
        if stream is None:
            stream = open(self.default_path)
        name, id, *fields = stream.readline().split(self.DELIMITER)
        id = int(id)
        if self.class_name != name or self.id != id:
            raise ValueError(
                "Instances doesn't match {0}({1}) != {2}({3})".format(
                    self.class_name, self.id,
                    name, id
                )
            )
        self.update(**dict(zip(self.__slots__[1:], fields)))
        return self

    @classmethod
    def find_subclass(cls, name):
        found = set()
        work = [cls]
        while work:
            parent = work.pop()
            for child in parent.__subclasses__():
                if child.__name__ == name:
                    return child
                if child not in found:
                    found.add(child)
                    work.append(child)
        return None

    @classmethod
    def load(cls, stream):
        if isinstance(stream, str):
            stream = open(stream)
        if stream is None:
            raise ValueError("stream shouldn't be None in classmethod")
        name, id, *fields = stream.readline().split(cls.DELIMITER)
        id = int(id)
        klass = cls
        if cls.__name__ != name:
            klass = cls.find_subclass(name)
            if klass is None:
                raise ValueError("No such class '{}'".format(name))
        x = klass.from_id(id)
        x.update(**dict(zip(cls.__slots__[1:], fields)))
        return x

    @classmethod
    def from_id(cls, id):
        return cls.INSTANCES.get(id) or cls(id)

    @classmethod
    def test(cls, id=0, *args, **kwargs):
        x = cls(id)
        x.update(*args, **kwargs)
        print(x)
        print(repr(x))
        print(x is cls.from_id(id))
        x.save()
        print(x is cls.load(x.default_path))
        print(x is x.load())
        return x


def test():
    class A(Base):
        __slots__ = ["id", "x"]
        ALIASES = {
            "x": "hex_x"
        }

        def update(self, x):
            if isinstance(x, str):
                x = int(x, 16)
            self.x = int(x)

        @property
        def hex_x(self):
            return hex(self.x)

    A.test(x=10)


if __name__ == '__main__':
    test()
