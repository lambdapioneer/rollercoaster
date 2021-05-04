from simulation.messages import TAG_PAYLOAD


class Group(object):

    def __init__(self, id, users):
        self.id = id
        self.users = users


def create_factory(cls, **p_kwargs):
    # So, basically a factory-factory. I might have had
    # too much exposure to Java in early years...
    return lambda *args, **kwargs: cls(
        *args,
        **(dict(kwargs, **p_kwargs))
    )


class SendingStrategy(object):

    def __init__(self, sim, user, group, app):
        self.sim = sim
        self.user = user
        self.group = group
        self.app = app

    def _deliver(self, msg):
        self.app.on_payload(self.user, msg, msg.body)

    def name(self):  # pragma: no cover
        raise NotImplementedError("Not implemented")

    def on_receive(self, msg):  # pragma: no cover
        raise NotImplementedError("Not implemented")

    def send_to_group(self, payload):  # pragma: no cover
        raise NotImplementedError("Not implemented")

    def tick(self, sim):  # pragma: no cover
        raise NotImplementedError("Not implemented")

    def clean(self):
        # optional: clean temporary state before pickleing
        pass
