from simulation.messages import TAG_PAYLOAD, Message, ApplicationMessage
from simulation.multicast.base import SendingStrategy
from simulation.multicast.schedule import Schedule
from simulation.utils import HasSeenSet


class RollercoasterMessage(ApplicationMessage):
    """The message of the Rollercoaster layer that contains either the application payload
    or a `ACK` message as its body. It will be wrapped in `WrappedMessage`s when it's being
    sent.
    """

    ACK = "ACK"

    def __init__(self, recipient, body, group_id, source, nonce, role, sender):
        """recipient: who this message gets delivered to
        body: payload of the application layer (might be just ACK)
        source: the emitter of the original message
        nonce: uniquely identifier for each message from the same source
        role: the recipient's acting role (often itself, but different it is was reassigned)
        sender: the sender of this very message (useful for updating the last_seen_nodes field)
        """
        #opt assert recipient != sender
        #opt assert role != source

        super().__init__(recipient, TAG_PAYLOAD, body, group_id)

        self.source = source
        self.nonce = nonce
        self.sender = sender
        self.role = role

    def copy(self):
        return RollercoasterMessage(
            self.recipient, self.body, self.group_id,
            self.source, self.nonce, self.role, self.sender)

    def id(self):
        """A message is safe to ignore if we have handled it already for a particular role.
        `source` and `nonce` uniquely identify a messaging session.
        `role` uniquely identify a role.
        """
        return (self.source, self.nonce, self.role)

    def __repr__(self):
        return "RC[%s, gid=%s, src=%s, nonce=%s, role=%s, sender=%s, %s]" % (
            str(self.recipient),
            str(self.group_id),
            str(self.source),
            str(self.nonce),
            str(self.role),
            str(self.sender),
            str(self.body))


class MessagingSession(object):
    STATE_IN_PROGRESS, STATE_DELIVERED = "IN_PROGRESS", "DELIVERED"

    class TimeoutEntry():

        def __init__(self, deadline, node, role):
            #opt assert deadline >= 0
            self.deadline = deadline
            self.node = node
            self.role = role

        def __repr__(self):
            return "T[@%d,n=%s,r=%s)" % (int(self.deadline), self.node, self.role)

        def __eq__(self, o):
            #opt assert type(self) == type(o)
            return self.deadline == o.deadline and self.node == o.node and self.role == o.role

    def __init__(self, multicast, source, nonce, payload):
        self.source, self.nonce, self.payload = source, nonce, payload
        self.users, self.sim = multicast.group.users, multicast.sim

        self.state = {x: MessagingSession.STATE_IN_PROGRESS for x in self.users if x != source}
        self.timeouts = []  # list of TimeoutEntry items
        self.schedule = Schedule(self.source, self.users, multicast.k, self.nonce)

    def set_timeout(self, t_offset, node, role):
        # when setting a new timeout, there shouldn't be any existing one for this `node` and `role`
        #opt assert not any(map(lambda entry: entry.node == node and entry.role == role, self.timeouts))

        self.timeouts.append(MessagingSession.TimeoutEntry(self.sim.time + t_offset, node, role))

    def get_failed_timeouts(self, remove):
        # optimization: skip if no entry triggers their deadline
        none_failed = True
        for entry in self.timeouts:
            if entry.deadline <= self.sim.time:
                none_failed = False
                break
        if none_failed:
            return []

        result = [entry for entry in self.timeouts if entry.deadline <= self.sim.time]
        if remove:
            self.timeouts = [entry for entry in self.timeouts if entry.deadline > self.sim.time]
        return result

    def mark_acked(self, node, role):
        self.state[node] = MessagingSession.STATE_DELIVERED
        self.remove_timeout_of_node(node, role)

    def remove_timeout_of_node(self, node, role):
        # optimization: skip if there's no entry for this `node` and `role`
        if not any(map(lambda entry: entry.node == node and entry.role == role, self.timeouts)):
            return
        self.timeouts = [entry for entry in self.timeouts if entry.node != node or entry.role != role]

    def update_timeout(self, node, role, new_t_offset):
        for entry in self.timeouts:
            if entry.node == node and entry.role == role:
                entry.deadline = self.sim.time + new_t_offset

    def next_receiver(self, failed_node):
        return self.schedule.get_next_receiver(failed_node)


class LastSeen():

    def __init__(self):
        self.stack = []

    def mark_seen(self, node):
        if node in self.stack:
            self.stack.remove(node)
        self.stack.append(node)

    def mark_failed(self, node):
        if node in self.stack:
            self.stack.remove(node)

    def pop_candidate(self):
        if len(self.stack) > 0:
            return self.stack.pop()
        else:
            return None


class RollercoasterStrategy(SendingStrategy):

    def name(self):
        return "rollercoaster-k%d-p%d" % (self.k, self.p)

    def __init__(self, sim, user, group, app,
                 k, p=1,
                 timeout_multiplier=1.5,
                 timeouts_active=True,
                 drop_offline=False):
        """Creates a new RollercoasterStrategy for a given user.

        k: the parameter for `gen_schedule` determining how wide the messaging tree is
        timeout_multiplier: the multiplicative factor to scale the estimated timeouts
        """
        super().__init__(sim, user, group, app)
        self.k = k
        self.user.set_split(p)

        # Timeout parameters (TODO: can benefit from more analysis and optimizations)
        hops = len(self.sim.network.layers) + 1  # +1 for egress provider
        base_delay_factor = 2  # determined experimentally (can be as low as 1)
        self.msg_delay = 1_000 * base_delay_factor * hops / self.sim.config.user_rate_delay
        self.queue_delay = 1_000 / self.user.rate_payload
        self.timeout_multiplier = timeout_multiplier
        self.timeouts_active = timeouts_active
        self.drop_offline = drop_offline

        # Book keeping
        self.nonce_counter = 0
        self.sessions = dict()
        self.last_seen = LastSeen()
        self.seen_messages = HasSeenSet()

    def send_to_group(self, payload):
        #opt assert self.user.online

        # Create (and register locally) a new session to track timeouts and payload
        session = self._add_session(payload)

        # Send message to all direct children (who in turn will follow the schedule)
        rs = session.schedule.get_direct_children(self.user)
        for r in rs:
            # In the first round it holds that `recipient == role` (i.e. we start fresh and believe everyone can help)
            m = RollercoasterMessage(recipient=r, body=payload, group_id=self.group.id,
                                     source=self.user, nonce=session.nonce, role=r, sender=self.user)
            m.callback = lambda m: self._on_send_callback(m)
            self.user.schedule_for_send(m)

    def _on_send_callback(self, m):
        #opt assert isinstance(m, RollercoasterMessage)
        if m.body == RollercoasterMessage.ACK:
            return

        # No work to do if timeouts are not active
        if not self.timeouts_active:
            return

        # Only the source maintains timeouts. Therefore, we can ignore callbacks in all other cases
        if m.source != self.user:
            return
        session = self._get_session(nonce=m.nonce)

        #opt assert m.role != self.user

        # Only check the direct recipient if it is not us (this could happen e.g. if we take
        # over a role).
        if m.recipient != self.user:
            session.set_timeout(
                t_offset=self.timeout_multiplier * session.schedule.get_estimated_rtt(
                    node_id_root=m.role, node_id_final=m.role,
                    t_message=self.msg_delay, t_queue=self.queue_delay
                ),
                node=m.recipient, role=m.role
            )

        for c in session.schedule.get_recursive_children(m.role):
            #opt assert c != self.user
            session.set_timeout(
                t_offset=self.timeout_multiplier * session.schedule.get_estimated_rtt(
                    node_id_root=m.role, node_id_final=c,
                    t_message=self.msg_delay, t_queue=self.queue_delay
                ),
                node=c, role=c
            )

    def on_receive(self, m):
        #opt assert isinstance(m, RollercoasterMessage)
        #opt assert m.recipient == self.user
        #opt assert m.sender != self.user
        #opt assert self.user.online

        self.last_seen.mark_seen(m.sender)

        if m.body == RollercoasterMessage.ACK:
            self.on_ack(m)
        else:
            self.on_payload(m)

    def on_ack(self, m):
        #opt assert m.source == self.user

        session = self._get_session(nonce=m.nonce)
        session.mark_acked(m.sender, m.role)

    def on_payload(self, m):
        # Do not help if we received the message while being offline
        if self.drop_offline and m.get_delivery_online_state() == Message.DELIVERED_OFFLINE:
            self._deliver(m)
            return

        # Ignore already seen messages (but do ack)
        if self.seen_messages.check_and_insert(m.id()):
            self.send_ack(m)
            return

        # Pass to application
        self._deliver(m)

        # Send payload to children
        schedule = Schedule(m.source, self.group.users, self.k, m.nonce)
        children = schedule.get_direct_children(m.role)

        for r in children:
            if r == self.user:
                continue

            m_ = m.copy()
            m_.recipient = r
            m_.role = r
            m_.sender = self.user
            self.user.schedule_for_send(m_)

        # Send ACK to source
        self.send_ack(m)

    def send_ack(self, m):
        self.user.schedule_for_send(RollercoasterMessage(
            recipient=m.source, body=RollercoasterMessage.ACK, group_id=self.group.id,
            source=m.source, nonce=m.nonce, role=m.role, sender=self.user
        ))

    def tick(self, sim):
        if not self.timeouts_active:
            return

        # handle failed timeouts
        for session in self.sessions.values():
            failed_timeouts = session.get_failed_timeouts(remove=True)

            for failed_entry in failed_timeouts:
                failed_node, failed_role = failed_entry.node, failed_entry.role

                # This node is unlikely to be a good candidate
                self.last_seen.mark_failed(failed_node)

                # We ignore failed leaf nodes since we assume eventual delivery
                if session.schedule.is_leaf(failed_role):
                    continue

                # get a better candidate (first using last-seen nodes, then following schedule)
                new_recipient = None
                new_recipient = self.last_seen.pop_candidate()
                if not new_recipient:
                    new_recipient = session.schedule.get_next_receiver(failed_node)

                # Send the message their way
                self.user.schedule_for_send(
                    RollercoasterMessage(
                        recipient=new_recipient, body=session.payload, group_id=self.group.id,
                        source=self.user, nonce=session.nonce, role=failed_role, sender=self.user))

                # remove all timeouts of all children (will be set again when the message is sent)
                for c in session.schedule.get_recursive_children(failed_role):
                    session.remove_timeout_of_node(c, c)

    def clean(self):
        self.sessions = dict()
        self.last_seen = LastSeen()
        self.seen_messages = HasSeenSet()

    def _add_session(self, payload):
        session = MessagingSession(self, self.user, self.nonce_counter, payload)
        self.sessions[self.nonce_counter] = session
        self.nonce_counter += 1
        return session

    def _get_session(self, nonce):
        return self.sessions[nonce]
