import socket
import struct
import random

from tornado.gen import coroutine, Return
from tornado.concurrent import Future
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
        self.sent_count = {}

        # TODO: Make this non-blocking
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    @coroutine
    def request_connection_id(self):
        connection_id = 0x41727101980  # Magic number
        transaction_id = random.getrandbits(32)
        action = 0 # Connect

        data = struct.pack('!QII', connection_id, transaction_id, action)
        self.socket.sendto(data, (self.host, self.port))

        action2, transaction_id2, connection_id2 = struct.unpack('!IIQ', socket.recv(16))

        if transaction_id2 != transaction_id:
            raise ValueError('Transaction IDs do not match')

        if action2 != action:
            raise ValueError('Action is not CONNECT')

    @coroutine
    def send_request(self, structure, *args):
        connection_id = 0x41727101980
        transaction_id = random.getrandbits(32)

        data = struct.pack('!QI', connection_id, transaction_id)
        data += struct.pack(structure, *args)

        if transaction_id in self.sent_count:
            self.sent_count += 1

        response = self.socket

    def announce(self, peer_id, port, event='started', num_wanted=10):
        transaction_id = random.getrandbits(32)

        data = struct.pack('!QII', 0x41727101980, 0, transaction_id)
        self.socket.sendto(data, (self.host, self.port))

        action, transaction_id2, connection_id = struct.unpack('!IIQ', self.socket.recv(16))

        if transaction_id2 != transaction_id:
            raise ValueError('Transaction IDs do not match')

        if action != 0:
            raise ValueError('Action is not CONNECT')

        transaction_id = random.getrandbits(32)

        data = struct.pack('!QII20s20sQQQIIIiH',
            connection_id,
            1, # ANNOUNCE
            random.getrandbits(32),
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
        )

        future = Future()
        future.set_result(False)

        return future



    def datagramReceived(self, data):
        print 'Received', repr(data)