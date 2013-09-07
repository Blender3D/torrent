import socket
import struct
import random
import logging

from datetime import datetime, timedelta

from tornado.gen import coroutine, Return, Task
from tornado.concurrent import Future
from tornado.ioloop import IOLoop
from tornado.iostream import IOStream

from bittorrent import bencode, utils
from bittorrent.tracker.common import TrackerResponse

class UDPTracker(object):
    events = {
        'none': 0,
        'completed': 1,
        'started': 2,
        'stopped': 3
    }

    def __init__(self, host, port, torrent, tier=0):
        self.host = host
        self.port = port

        self.torrent = torrent
        self.tier = tier

        self.connection_id = None
        self.connection_id_age = datetime.min
        self.requesting_connection_id = False

        self.pending_retries = {}
        self.pending_futures = {}
        self.pending_timers = {}

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.stream = IOStream(sock)
        self.stream.connect((self.host, self.port))
        self.stream.read_until_close(None, self.data_received)

    def data_received(self, data):
        action, transaction_id = struct.unpack('!II', data[:8])

        if transaction_id in self.pending_retries:
            del self.pending_retries[transaction_id]

        if transaction_id in self.pending_timers:
            handle = self.pending_timers[transaction_id]
            IOLoop.instance().remove_timeout(handle)
            del self.pending_timers[transaction_id]

        if action == 0:  # CONNECT
            result = self.receive_connect(data[8:])
        elif action == 1:  # ANNOUNCE
            result = self.receive_announce(data[8:])
        elif action == 2:  # SCRAPE
            result = None
        elif action == 3:  # ERROR
            raise Exception(data[8:])

        self.pending_futures[transaction_id].set_result(result)
        del self.pending_futures[transaction_id]

    def request_connection_id(self):
        self.connection_id = 0x41727101980

        return self.send_request(0)

    def receive_connect(self, data):
        self.connection_id = struct.unpack('!Q', data)[0]
        self.connection_id_age = datetime.now()

    def receive_announce(self, data):
        interval, leechers, seeders = struct.unpack('!III', data[:12])
        num_peers = seeders + leechers
        peers = []

        for chunk in utils.grouper(6, data[12:12 + 6 * num_peers]):
            peers.append(utils.unpack_peer_address(''.join(chunk)))

        return TrackerResponse(peers, interval)

    @coroutine
    def send_request(self, action, structure='', arguments=None, transaction_id=None, attempt=1):
        if action != 0 and datetime.now() - self.connection_id_age > timedelta(minutes=1):
            self.requesting_connection_id = True
            yield self.request_connection_id()

        if transaction_id is None:
            transaction_id = random.getrandbits(32)

        data = struct.pack('!QII', self.connection_id, action, transaction_id)

        if structure and arguments:
            data += struct.pack(structure, *arguments)

        if transaction_id in self.pending_retries:
            self.pending_retries[transaction_id] += 1
            count = self.sent_requests[transaction_id]

            if count > 8:
                raise ValueError('Request was retried 8 times with no response')

            retry_request = lambda: self.send_request(action, structure, arguments, transaction_id, attempt=attempt + 1)

            if transaction_id in self.pending_timers:
                handle = self.pending_timers[transaction_id]
                IOLoop.instance().remove_timeout(handle)

            handle = IOLoop.instance().add_timeout(timedelta(seconds=15 * 2 ** count), retry_request)
            self.pending_timers[transaction_id] = handle
        else:
            self.pending_futures[transaction_id] = Future()
            yield Task(self.stream.write, data)

        result = yield self.pending_futures[transaction_id]

        raise Return(result)

    @coroutine
    def announce(self, peer_id, port, event='started', num_wanted=10):
        response = yield self.send_request(1, '!20s20sQQQIIIiH', [
            self.torrent.info_hash(),
            peer_id,
            self.torrent.downloaded,
            self.torrent.remaining,
            self.torrent.uploaded,
            self.events[event],
            0,
            0,
            -1,
            port
        ])

        raise Return(response)