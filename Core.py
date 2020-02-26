class Product:
    def __init__(self, name, time, price, amount = 1):
        self.name = name
        self.time = time
        self.price = price
        self.amount = amount
    
    @property
    def cost(self):
        return self.price * self.amount


class Group:
    def __init__(self, users = None):
        if users is None:
            users = []
        self.users = users
    
    def bought(self, user, products, users):
        user.balance += products.cost
        
        self.propagate(products, users)
    
    def propagate(self, products, users = None):
        m = []

        if users is None:
            m = self.users
        else:
            for u in self.users:
                if u.name in users:
                    m.append(u)
        
        cost = products.cost / len(m)
        for u in m:
            u.balance -= cost


class User:
    def __init__(self, group, name, balance = 0):
        self.group = group
        self.group.users.append(self)
        self.name = name
        self.balance = balance
    
    def bought(self, products, users):
        self.group.bought(self, products, users)
        