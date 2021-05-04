from simulation.messages import Message, WrappedMessage, WrappedMultiMessage

import gzip
import heapq


def chunkify(ll, s):
    """Splits the given list ll into chunks of size s"""
    for idx in range(0, len(ll), s):
        yield ll[idx:idx+s]


def map_any_or_all(func, iterable_or_not):
    """Executes `func` on the argument whether it is iterable or a
    single object. In case of an iterable object `func` is executed
    for all its elements. In case of a single object `func` is executed once.
    """
    try:
        iter(iterable_or_not)  # throws `TypeError` if not iterable
        for x in iterable_or_not:
            func(x)
    except TypeError:
        func(iterable_or_not)


def traverse_message(m):
    while isinstance(m, Message):
        yield m
        if isinstance(m, WrappedMultiMessage):
            for m_ in m.body:
                yield from traverse_message(m_)
            return
        elif isinstance(m, WrappedMessage):
            m = m.unwrap()
        else:
            return


def reorder_inplace_with_seed(list, seed):
    import random
    r = random.Random(seed)
    r.shuffle(list)


class HasSeenSet:

    def __init__(self):
        self.set = set()

    def check_and_insert(self, o):
        if o in self.set:
            return True
        else:
            self.set.add(o)
            return False

    def clear(self):
        self.set = set()


class MessageDelayingBox:
    class TimedEntry(object):

        def __init__(self, deadline, msg):
            self.deadline = deadline
            self.msg = msg

        def __lt__(self, other):
            return self.deadline < other.deadline

    def __init__(self):
        self.pq = [] # [TimedEntry]

    def add(self, sim, m):
        #opt assert isinstance(m, WrappedMessage)
        heapq.heappush(self.pq, MessageDelayingBox.TimedEntry(sim.time + m.delay, m))

    def tick(self, sim):
        pass # do nothing

    def pop_current_round(self, sim):
        if len(self.pq) == 0 or self.pq[0].deadline > sim.time:
            return []

        this_round = []
        while len(self.pq) > 0 and self.pq[0].deadline <= sim.time:
            entry = heapq.heappop(self.pq)
            this_round.append(entry.msg)

        return this_round


def read_compressed_int_schedules(filename):
    with gzip.open(filename, 'r') as f:
        lines = f.read().decode().split('\n')
        return [s.strip() for s in lines if len(s) > 1]


def write_compressed_int_schedules(int_schedules, filename):
    with gzip.open(filename, 'w') as f:
        f.write("\n".join(int_schedules).encode())


def read_compressed_bool_schedules(filename):
    int_schedules = read_compressed_int_schedules(filename)
    bool_schedules = [[c == '1' for c in line] for line in int_schedules]
    return bool_schedules


def write_compressed_bool_schedules(bool_schedules, filename):
    int_schedules = ["".join(['1' if x else '0' for x in schedule]) for schedule in bool_schedules]
    write_compressed_int_schedules(int_schedules, filename)
