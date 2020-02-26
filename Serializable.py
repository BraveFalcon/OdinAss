class Serializable:
    @classmethod
    def read(self, stream):
        pass
    
    def write(self, stream):
        stream.write(
            self.__class__.__name__ + " { " + ", ".join([
                getattr(self, attr)
                for attr in dir(self)
                if not attr.startswith('_')
            ]) + " }\n"
        )
