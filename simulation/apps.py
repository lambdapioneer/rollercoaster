from simulation.simulation import SimulationObject
from simulation.utils import HasSeenSet


class App(SimulationObject):

    class Payload:
        def __init__(self, nonce, created_at):
            self.nonce = nonce
            self.created_at = created_at

        def __repr__(self) -> str:
            return "payload<%d@T%d>" % (self.nonce, self.created_at)

    def __init__(self, name, sim, group, multicast_factory):
        super().__init__(name)
        self.sim = sim
        self.group = group
        self.output = self.sim.output

        if multicast_factory:
            for user in self.group.users:
                user.add_multicast(multicast_factory(sim=sim, user=user, group=group, app=self))

        # these payload indicators are used to prevent counting re-transmitted
        # messages twice for E2E delay
        self.payload_nonce = 0
        self.seen_deliveries = HasSeenSet()  # elements are tuples (receiver, counter)

    def on_payload(self, recipient, msg, payload):
        if not self.seen_deliveries.check_and_insert((recipient, payload.nonce)):
            self.output.log_e2e_delay(
                sim=self.sim,
                msg=msg,
                app=self,
                delay=self.sim.time - payload.created_at,
            )
        else:
            self.sim.output.log_already_seen(self)

    def send_payload_to_group(self, sender, payload):
        sender.multicast[self.group.id].send_to_group(payload)

    def _create_payload(self):
        self.payload_nonce += 1
        return App.Payload(nonce=self.payload_nonce, created_at=self.sim.time)

    def tick(self, sim):
        pass  # can be optionally overridden

    def clean(self):
        self.seen_deliveries = set()


class InteractiveApp(App):

    def __init__(self, name, sim, group, multicast_factory,
                 init_rate_per_second, heavy_user_percentage=0, heavy_user_weight=1):
        super().__init__(name, sim, group, multicast_factory)

        #opt assert len(group.users) >= 2

        # Rate at which any user would spontaneously send a message
        self.init_rate_per_second = init_rate_per_second

        # A `heavy_user_percentage`% of users sends `heavy_user_weight` times more
        # often than other users.
        users = group.users
        self.user_to_weight = {u: 1.0 for u in users}
        for heavy_user in users[:int(heavy_user_percentage/100*len(users))]:
            self.user_to_weight[heavy_user] = heavy_user_weight

    def tick(self, sim):
        if self.sim.rnd.poisson_event(self.init_rate_per_second):
            sender = self._choose_online_sender()
            if sender and sender.online:
                self.send_a_message(sender=sender)

    def send_a_message(self, sender):
        self.send_payload_to_group(sender, self._create_payload())

    def _choose_online_sender(self):
        online_users = [u for u in self.group.users if u.online]
        if len(online_users) == 0:
            return None

        online_users = self.sim.rnd.shuffle(online_users)
        online_users_weights = [self.user_to_weight[u] for u in online_users]

        sender = self.sim.rnd.choice_with_weights(online_users, online_users_weights)
        return sender


class InteractiveMultimessageApp(InteractiveApp):

    def __init__(self, name, sim, group, multicast_factory,
                 init_rate_per_second, multi_message=1,
                 heavy_user_percentage=0, heavy_user_weight=1):
        super().__init__(
            name, sim, group,
            multicast_factory=multicast_factory,
            init_rate_per_second=init_rate_per_second,
            heavy_user_percentage=heavy_user_percentage,
            heavy_user_weight=heavy_user_weight)
        self.multi_message = multi_message

    def send_a_message(self, sender):
        for _ in range(self.multi_message):
            self.send_payload_to_group(sender, self._create_payload())


class NoOperationApp(App):

    def __init__(self, name, sim, group, multicast_factory):
        super().__init__(name, sim, group, multicast_factory)

    def tick(self, sim):
        super().tick()
