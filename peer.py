import time

from collections import defaultdict, namedtuple
from operator import attrgetter

DataSample = namedtuple('DataSample', 'time data')

class Peer(object):
    def __init__(self, address, port, id=None):
        self.address = address
        self.port = port
        self.id = id

        self.speeds = deque([], maxlen=60)

    def add_data_sample(self, size):
        t = int(time.time())

        while self.speeds and t - self.speeds[0].time > 60:
            self.speeds.popleft()

        if not self.speeds:
            self.speeds.append(DataSample(t, size))
            return

        self.speeds[self.speeds[0].time

    @property
    def average_speed(self):
        if not self.speeds:
            return -1.0
        else:
            return sum(speed for t, speed in self.speeds) / float(len(self.speeds))

    def __repr__(self):
        return '<Peer {self.address}:{self.port}>'.format(self=self)