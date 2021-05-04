from simulation.multicast.base import SendingStrategy
from simulation.messages import TAG_PAYLOAD, TAG_DROP, TAG_LOOP, create_wrapped_message, WrappedMessage, Message, wrap_messages_in_multi_message
from simulation.simulation import SimulationObject, RecursiveSimulationObject, Simulation, SimulationOutput
from simulation.utils import MessageDelayingBox, map_any_or_all


class LoopixConfiguration():
    """All rates are expressed as expected events per second"""

    def __init__(
        self,
        user_rate_pull=1,
        user_rate_payload=2,
        user_rate_drop=2,
        user_rate_loop=2,
        user_rate_delay=3,
        mix_rate_loop=2,
        mix_rate_loop_delay=3,
    ):
        self.mix_rate_loop = mix_rate_loop
        self.mix_rate_loop_delay = mix_rate_loop_delay
        self.user_rate_pull = user_rate_pull
        self.user_rate_payload = user_rate_payload
        self.user_rate_drop = user_rate_drop
        self.user_rate_loop = user_rate_loop
        self.user_rate_delay = user_rate_delay

        if not(user_rate_payload + user_rate_drop + user_rate_loop >= 2 * user_rate_delay):
            print("For secure configuration it should hold that: lambda/mu > 2")


class MixNode(SimulationObject):
    """Mix nodes inject loop traffic (at `rate_loop` w/ `rate_loop_delay`). All
    incoming messages are hold according to their `delay` field and then forwarded.
    """

    def __init__(self, name, layer_id, config):
        super().__init__(name)
        self.inbox = MessageDelayingBox()
        self.layer_id = layer_id

        self.rate_loop = config.mix_rate_loop
        self.rate_delay = config.mix_rate_loop_delay

    def deliver(self, sim, m):
        self.inbox.add(sim, m)

    def tick(self, sim):
        if sim.rnd.poisson_event(self.rate_loop):
            self._send_loop(sim)
            # continue as loops are independent of forwarding

        self.inbox.tick(sim)
        this_round = self.inbox.pop_current_round(sim)

        for m in this_round:
            if isinstance(m, WrappedMessage):
                map_any_or_all(
                    lambda m: sim.send(self, m),
                    m.unwrap()
                )

    def _send_loop(self, sim):
        # The mixes cannot reuse the `MixNetwork` random path method as
        # they need to route through the providers layer
        network = sim.network
        providers = sim.providers

        path = []
        for idx in range(self.layer_id + 1, len(network.layers)):
            path.append(sim.rnd.choice(network.layers[idx]))

        path.append(sim.rnd.choice(providers))

        for idx in range(0, self.layer_id):
            path.append(sim.rnd.choice(network.layers[idx]))
        path.append(self)

        m = create_wrapped_message(TAG_LOOP, "", path, self.rate_delay, sim)
        sim.send(self, m)


class Provider(SimulationObject):

    def __init__(self, name):
        super().__init__(name)
        self.inbox = MessageDelayingBox()
        self.postboxes = {}  # user -> (time, message)

    def deliver(self, sim, m):
        if m.tag == TAG_DROP:
            return  # ignore drop messages early on

        self.inbox.add(sim, m)

    def tick(self, sim):
        self.inbox.tick(sim)
        this_round = self.inbox.pop_current_round(sim)

        for m in this_round:
            m = m.unwrap()

            u = m.recipient
            if isinstance(u, User):
                self.postboxes[u].append((sim.time, m))

            else:
                # message to a mix node
                sim.send(self, m)


_SECONDS_IN_DAY = 24*60*60


class User(SimulationObject):

    def __init__(self, name, provider, mix_network, config, online_schedule=None):
        super().__init__(name)
        self.provider = provider
        self.provider.postboxes[self] = []
        self.mix_network = mix_network

        # app will add a new multicast strategy for their group id; the User object
        # will use the `message.group_id` to route the message to the right multicast
        # instance and hence to the right application
        self.multicast = dict()

        # sending properties
        self.out_buffer = []
        self.rate_payload = config.user_rate_payload
        self.rate_drop = config.user_rate_drop
        self.rate_loop = config.user_rate_loop
        self.rate_delay = config.user_rate_delay

        # note that this is a fixed rate expressed in checks per second
        self.time_between_pulls = 1_000 / config.user_rate_pull
        self.time_until_pull = self.time_between_pulls

        # for p-restricted multicast
        self.waiting_for_split = []
        self.split = 1  # might get updated from the sending strategy

        # online schedule
        self.online = True
        self.online_schedule = online_schedule
        if self.online_schedule:
            #opt assert len(self.online_schedule) == _SECONDS_IN_DAY
            self.online = self.online_schedule[0]

    def add_multicast(self, multicast):
        self.multicast[multicast.group.id] = multicast

    def set_split(self, split):
        if self.split == split:
            return

        self.rate_drop *= split / self.split
        self.rate_loop *= split / self.split
        self.rate_payload *= split / self.split
        self.split = split

    def schedule_for_send(self, application_message):
        #opt assert application_message.tag == TAG_PAYLOAD
        self.out_buffer.append(application_message)

    def tick(self, sim):
        # Skip all actions if we are offline
        if self.online_schedule:
            ss = (sim.time // 1_000) % _SECONDS_IN_DAY  # seconds since midnight
            self.online = self.online_schedule[ss]
            if self.online == False:
                return  # zZzZ

        # DUTY: check inbox for messages
        if self.time_until_pull <= 0:
            self.time_until_pull = self.time_between_pulls
            #opt assert sim.delta_ms <= self.time_between_pulls

            self._process_inbox(sim, self.provider.postboxes[self])
            self.provider.postboxes[self] = []
            # continue as pull is independent of the other processes
        self.time_until_pull -= sim.delta_ms

        # DUTY: send payload/drop message if any
        if sim.rnd.poisson_event(self.rate_payload):
            if len(self.out_buffer) > 0:
                self._send_payload(sim, self.out_buffer.pop(0))
            else:
                self._send_drop(sim)

        # DUTY: send drop message if any
        if sim.rnd.poisson_event(self.rate_drop):
            self._send_drop(sim)

        # DUTY: send loop message if any
        if sim.rnd.poisson_event(self.rate_loop):
            self._send_loop(sim)

        # DUTY: actually send out if we have at least `p` messages
        if len(self.waiting_for_split) >= self.split:
            self._send_waiting_split_messages(sim)

        for multicast in self.multicast.values():
            multicast.tick(sim)

    def _process_inbox(self, sim, inbox):
        for delivery_time, m in inbox:
            m.set_deliver_online_state(Message.DELIVERED_ONLINE if delivery_time >
                                       sim.time - self.time_between_pulls else Message.DELIVERED_OFFLINE)
            if m.tag == TAG_PAYLOAD:
                self.multicast[m.group_id].on_receive(m)
            else:
                pass  # ignore DROP and LOOP messages

    def _send_loop(self, sim):
        m = Message(recipient=self, tag=TAG_LOOP, body="",)
        self.waiting_for_split.append(m)

    def _send_drop(self, sim):
        provider = sim.rnd.choice(sim.providers)
        m = Message(recipient=provider, tag=TAG_DROP, body="",)
        self.waiting_for_split.append(m)

    def _send_payload(self, sim, m):
        self.waiting_for_split.append(m)

    def _send_waiting_split_messages(self, sim):
        # Pop top `split` messages of the list
        messages = self.waiting_for_split[:self.split]
        self.waiting_for_split = self.waiting_for_split[self.split:]

        for m in messages:
            m.fire_callback_and_reset()

        multi_message = wrap_messages_in_multi_message(self, messages, sim)

        sim.send(
            sender=self,
            m=multi_message
        )

    def output_buffer_level(self):
        return len(self.out_buffer)

    def clean(self):
        """Clear temporary state data"""
        self.out_buffer = []
        self.waiting_for_split = []

        self.online_schedule = None
        self.online = True

        for multicast in self.multicast.values():
            multicast.clean()


class LayeredMixNetwork(RecursiveSimulationObject):

    def __init__(self, num_layers, mix_per_layer, config):
        super().__init__("Layered_Mix_Network")
        self.layers = [[] for _ in range(num_layers)]

        for l in range(num_layers):
            for m in range(mix_per_layer):
                self.layers[l].append(MixNode("Mix_%01d_%02d" % (l, m), l, config))
            self.objects += self.layers[l]

    def tick(self, sim):
        for layer in self.layers:
            for mix in layer:
                mix.tick(sim)

    def gen_random_path(self, sim):
        return [sim.rnd.choice(layer) for layer in self.layers]


def create_provider_with_users(provider_name, network, num_users, config, online_schedules=None):
    provider = Provider(provider_name)
    online_schedules = online_schedules[:] if online_schedules else None  # copy for pop() below
    users = []
    for i in range(num_users):
        name = "%s_U%d" % (provider_name, i)
        users.append(
            User(
                name,
                provider,
                network,
                config,
                online_schedules.pop(0) if online_schedules else None
            ))

    return (provider, users)


class LoopixSimulation(Simulation):

    def __init__(self, network, providers, users, output, delta_ms, config=None):
        super().__init__(
            "LOOPIX_SIM",
            [network] + providers + users,
            output,
            delta_ms
        )
        self.network = network
        self.providers = providers
        self.users = users
        self.apps = []
        self.config = config

    def add_app(self, app):
        self.add_apps([app])

    def add_apps(self, apps):
        self.apps += apps
        self.objects += apps


def create_loopix_simulation(
        providers=4,
        users_per_provider=(2, 4),
        mix_layers=3,
        mix_scale=3,
        output=SimulationOutput(),
        seed=0,
        config=LoopixConfiguration(),
        online_schedules=[],
        delta_ms=1):
    """Creates a 'random' loopix simulation including a network and providers with users.

    Keyword arguments:
    providers -- Number of providers to generate
    users_per_provider -- Range for users per provider (inclusive)
    mix_layers -- Number of mix layers in the network
    mix_scale -- Number of mix nodes per layer
    output -- The gathering SimulationOutput object
    seed -- Seed for the PRNG to allow for reproducible generation
    config -- Wrapping object for the different rates of this Loopix deployment
    online_schedules -- If set these online/offline schedules are each assigned to a user
    delta_ms -- The delta time used by the simulation
    """
    import random as _pr
    random = _pr.Random(seed)

    network = LayeredMixNetwork(mix_layers, mix_scale, config)
    providers_and_users = [
        create_provider_with_users(
            "P%d" % x,
            network,
            random.randint(*users_per_provider),
            config,
            online_schedules)
        for x in range(providers)
    ]

    providers, users = [], []
    for _p, _uu in providers_and_users:
        providers.append(_p)
        users += _uu

    sim = LoopixSimulation(network, providers, users, output, delta_ms, config)

    return sim
