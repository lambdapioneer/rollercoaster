from simulation import simrandom

TAG_PAYLOAD, TAG_DROP, TAG_LOOP, TAG_MULTI = "payload", "drop", "loop", "multi"
VALID_TAGS = (TAG_PAYLOAD, TAG_DROP, TAG_LOOP, TAG_MULTI)


def nop(*args, **kwargs):
    """A no-operation callback implementation"""
    pass


class Message():
    """Generic (abstract) message specifying a recipient, a tracking 
    tag, a body, and a size in bytes. One will generally want to use
    the sub-classes such as ApplicationMessage or WrappedMessage.

    The callback is called when it is send to the first hop from the client.
    """

    DELIVERED_ONLINE = True
    DELIVERED_OFFLINE = False

    def __init__(self, recipient, tag, body, callback=nop):
        #opt assert tag in VALID_TAGS

        self.recipient = recipient
        self.tag = tag  # this might be a single tag or None
        self.body = body
        self.callback = callback
        self._delivery_online_state = None


    def __repr__(self):
        return "[%s, %s, %s]" % (self.recipient, self.tag, self.body)

    def __getstate__(self):
        """Exclude the callback from being "pickled" as the normal pickle cannot handle
        local lambda objects."""
        return {'recipient': self.recipient, 'tag': self.tag, 'body': self.body}

    def __setstate__(self, d):
        self.__dict__ = d
        self.callback = nop

    def fire_callback_and_reset(self):
        self.callback(self)
        self.callback = nop

    def set_deliver_online_state(self, state):
        #opt assert state in (Message.DELIVERED_ONLINE, Message.DELIVERED_OFFLINE,)
        self._delivery_online_state = state

    def get_delivery_online_state(self):
        #opt assert self._delivery_online_state != None
        return self._delivery_online_state


class WrappedMessage(Message):
    """A wrapped message usually has another message as their body and
    they specify a delay $mu$ by which the message forwarding is delayed
    by mix nodes.
    """

    def __init__(self, recipient, tag, body, delay=0):
        super().__init__(recipient, tag, body)
        self.delay = delay

    def unwrap(self):
        return self.body

    def __repr__(self):
        return "[%s, %.2fs, %s]" % (self.recipient, self.delay / 1000, self.body)

    def set_deliver_online_state(self, state):
        super().set_deliver_online_state(state)

        if isinstance(self.body, Message):
            self.body.set_deliver_online_state(state)


class WrappedMultiMessage(WrappedMessage):
    """A wrapped message containing multiple messages as its body."""

    def __init__(self, recipient, tags, messages, delay=0):
        super().__init__(recipient, tags, body=messages, delay=delay)

    def unwrap(self):
        return self.body


class ApplicationMessage(Message):
    """Sub class for marking application messages"""

    def __init__(self, recipient, tag, body, group_id):
        super().__init__(recipient, tag, body)
        self.group_id = group_id


def create_wrapped_message(tag, body, chain, rate_delay_per_seconds, sim):
    """Creates a chain of `WrappedMessage(WrappedMessage( ...))` following the provided
    chain. The most inner message will be addressed to `chain[-1]` and contains the
    `body`. All messages share the same `tag`.
    """
    message = WrappedMessage(chain[-1], tag, body)
    for recipient in chain[-2::-1]:
        message = WrappedMessage(
            recipient=recipient,
            tag=tag,
            body=message,
            delay=sim.rnd.poisson_delay(rate_delay_per_seconds))
    return message


def create_wrapped_multi_message_multiple(chain_prefix, chain_suffixes, tags, bodies, rate_delay_per_seconds, sim):
    """The resulting 'logical' messages $m_i$ have the chains $c_i = chain_prefix + chain_suffixes$.
    It is assumed that the message 'multiplies' at the last node of the chain_prefix.
    The messages of the prefix path have the `tags` list as their tag.
    The messages of the suffix path have their individual `tag`.
    """
    #opt assert len(bodies) == len(chain_suffixes)
    #opt assert len(tags) == len(chain_suffixes)

    # different suffix parts are reduced to a normal wrapped message
    messages = [
        create_wrapped_message(tag, body, chain, rate_delay_per_seconds, sim)
        for body, tag, chain in zip(bodies, tags, chain_suffixes)
    ]

    # bundle all messages at the 'multiplier' node
    multiplier_node = chain_prefix[-1]
    message = WrappedMultiMessage(
        recipient=multiplier_node,
        tags=TAG_MULTI,
        messages=messages,
        delay=sim.rnd.poisson_delay(rate_delay_per_seconds))

    # attach remaining prefix
    for recipient in chain_prefix[-2::-1]:
        message = WrappedMessage(
            recipient=recipient,
            tag=TAG_MULTI,
            body=message,
            delay=sim.rnd.poisson_delay(rate_delay_per_seconds))

    return message


def wrap_messages_in_multi_message(sender, messages, sim, multiplier_layer=2):
    """Takes the given messages and wraps them in a multi message that splits at `multiplier_layer`.
    The prefix is randomly chosen from the network.
    """
    network = sender.mix_network  # This currently assumes a network layer depth of 3

    # Build a randomly chosen common chain "prefix"
    chain_prefix_mixes = [
        sim.rnd.choice(layer) for layer in network.layers[:multiplier_layer]
    ]
    chain_prefix = [sender.provider] + chain_prefix_mixes

    # Build independent chain "suffixes" and for each message/recipient
    chain_suffixes = []
    for m in messages:
        chain_suffix_mixes = [
            sim.rnd.choice(layer) for layer in network.layers[multiplier_layer:]
        ]

        last_mile = [m.recipient.provider] if hasattr(m.recipient, 'provider') else []

        chain_suffix = chain_suffix_mixes + last_mile
        chain_suffixes.append(chain_suffix)

    return create_wrapped_multi_message_multiple(
        tags=[m.tag for m in messages],
        bodies=messages,
        chain_prefix=chain_prefix,
        chain_suffixes=chain_suffixes,
        rate_delay_per_seconds=sender.rate_delay,
        sim=sim,
    )
