import socket
import struct
import random

from datetime import datetime, timedelta

from tornado.gen import coroutine, Return, Task
from tornado.concurrent import Future
from tornado.ioloop import IOLoop
from tornado.iostream import IOStream

from bittorrent import bencode
from bittorrent.udpstream import UDPStream

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

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.stream = IOStream(sock)
        self.stream.connect((self.host, self.port))

    @coroutine
    def receive_response(self):
        data = yield Task(self.stream.read_bytes, 4)

        action, transaction_id, connection_id = struct.unpack('!IIQ', data)
        result = (action, transaction_id, connection_id)

        if action == 0:
            raise Return(result)

    @coroutine
    def request_connection_id(self):
        self.connection_id = 0x41727101980
        yield self.send_request(0)
        response = yield Task(self.stream.read_bytes, 4)

        print '\n\n', repr(response), '\n\n'

    @coroutine
    def send_request(self, action, structure='', transaction_id=None, arguments=None, attempt=1):
        if action != 0 and datetime.now() - self.connection_id_age > timedelta(minutes=1):
            self.requesting_connection_id = True
            yield self.request_connection_id()

        transaction_id = transaction_id or random.getrandbits(32)
        data = struct.pack('!QII', self.connection_id, action, transaction_id)

        if structure and arguments:
            data += struct.pack(structure, *arguments)

        if transaction_id in self.pending_retries:
            self.pending_retries[transaction_id] += 1
            count = self.sent_requests[transaction_id]

            if count > 8:
                raise ValueError('Request was retried 8 times with no response')

            retry_request = lambda: self.send_request(action, structure, transaction_id, arguments, attempt=attempt + 1)
            IOLoop.instance().add_timeout(timedelta(seconds=15 * 2 ** count), retry_request)
        else:
            yield Task(self.stream.write, data)

    @coroutine
    def announce(self, peer_id, port, event='started', num_wanted=10):
        yield self.request_connection_id()

        return
        yield self.send_request(1, '!QII20s20sQQQIIIiH', [
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