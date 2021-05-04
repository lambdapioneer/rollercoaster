from math import log, ceil
from simulation.utils import reorder_inplace_with_seed


def _flatten_schedule(schedule):
    return [x for r, xs in schedule for x in xs]


class Graph:
    """A simple graph abstraction that allows retrieving the internal node respresentation
    via the references provided in the schedule.
    """

    class Node:
        def __init__(self, id, parent=None):
            self.id = id
            self.children = []
            self.parent = parent
            if self.parent:
                self.parent.children.append(self)

        def preorder_traversal(self):
            """Returns the subtree excluding the root item"""
            for x in self.children:
                yield x
                yield from x.preorder_traversal()

        def __repr__(self):
            return "N(%s)" % str(self.id)

    def __init__(self, schedule):
        flat_schedule = _flatten_schedule(schedule)
        source = flat_schedule[0][0]

        self.nodes = {source: Graph.Node(source)}
        for sender, receiver in _flatten_schedule(schedule):
            self.nodes[receiver] = Graph.Node(receiver, parent=self.nodes[sender])

    def get_parents(self, node):
        """Returns all parents of the given `node` up-to-and-including the source node"""
        if node.parent:
            yield node.parent
            yield from self.get_parents(node.parent)

    def get_hops_between(self, root, node):
        """Returns the number of hops between `node` to `root` assuming that `node`
        is in the subtree of `root`.
        """
        count = 0
        while node != root:
            count += 1
            node = node.parent
            #opt assert node != None
        return count

    def __getitem__(self, node_id):
        return self.nodes[node_id]


class Schedule:
    """Creates the schedule from the defining elements (i.e. the list of all users,
    the source node, the nonce, parameter k). Then two representations are offered: `S`
    which is the list-based scheduled as presented in the paper, and `G` which is a graph
    based representation.
    """

    def __init__(self, source, all_users, k, nonce=0):
        users_sorted = [source] + [x for x in all_users if x != source]
        self.S = self._gen_schedule(users_sorted, k, nonce)
        self.G = Graph(self.S)

    def _order_randomised(self, users, nonce):
        receivers = users[1:]
        reorder_inplace_with_seed(receivers, nonce)
        return [users[0]] + receivers

    def _gen_schedule(self, users, k, nonce):
        users = users if nonce == 0 else self._order_randomised(users, nonce)

        T = ceil(log(len(users), k+1))
        rounds = []
        for t in range(T):
            p = (k+1)**t  # knowing users
            w = min(k*p, len(users) - p)  # number of messages this round
            R = []
            for idx in range(w):
                a = users[int(idx / k)]
                b = users[p + idx]
                R.append((a, b))
            rounds.append((t, R))

        return rounds

    def get_next_receiver(self, failed_receiver):
        recv_order = [self.S[0][1][0][0]]  # start with source as ultimate fallback
        for _, R in self.S:
            for _, receiver in R:
                if receiver not in recv_order:
                    recv_order.append(receiver)
        pos = recv_order.index(failed_receiver)
        return recv_order[(pos + 1) % len(recv_order)]

    def get_direct_children(self, node_id):
        return [x.id for x in self.G[node_id].children]

    def get_recursive_children(self, node_id):
        return [x.id for x in self.G[node_id].preorder_traversal()]

    def get_parents(self, node_id):
        return [x.id for x in self.G.get_parents(self.G[node_id])]

    def get_hops_between(self, node_id_root, node_id_child):
        return self.G.get_hops_between(self.G[node_id_root], self.G[node_id_child])

    def get_estimated_rtt(self, node_id_root, node_id_final, t_message, t_queue):
        """Estimates the time from sending the message to the root, to the arrival of the
        ACK message from the final node. The node_root and node_final might be the same.

        In particular it accounts for the following steps:
        * message delay source->node_root [A]
        * foreach node != node_final:
            * queueing delay at node [B.1]
            * message delay to next node [B.2]
        * at node_final queueing delay for the ACK message [C]
        * message delay for the response [D]
        """
        node_final, node_root = self.G[node_id_final], self.G[node_id_root]

        total = t_message  # [A]

        # [C,D] (first iteration) + [B.1,B.2] (optional, following iterations)
        while True:
            # The extra +1 is for the queueing of the ACK message
            total += t_message + t_queue * (1 + len(node_final.children))
            if node_final == node_root:
                break
            else:
                node_final = node_final.parent

        return total

    def is_leaf(self, node_id):
        return len(self.G[node_id].children) == 0
