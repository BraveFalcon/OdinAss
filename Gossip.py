class Gossip:
    @classmethod
    def Ask(cls, *args, **kwargs):
        return ("Ask", args, kwargs)
    
    @classmethod
    def Wait(cls, *args, **kwargs):
        return ("Wait", args, kwargs)

