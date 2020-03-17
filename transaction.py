class Transaction:
    def __init__(self, purchaser, products, consumers, confirmers, message_id):
        self.purchaser = purchaser
        self.products = products
        self.value = sum(map(lambda x: x.cost, products))
        self.consumers = consumers
        self.confirmers = confirmers
        self.message_id = message_id

    def to_json(self):
        return {
            "purchaser": self.purchaser.id,
            "products": [p for p in self.products],
            "consumers": [u.id for u in self.consumers],
            "confirmers": [u.id for u in self.confirmers],
            "message_id": self.message_id
        }
