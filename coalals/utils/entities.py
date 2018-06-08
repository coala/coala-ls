class LSPEntity:

    @classmethod
    def entity_name(cls):
        return cls.__name__

    def json(self):
        raise NotImplementedError()
