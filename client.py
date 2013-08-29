import logging
import socket
import struct

from torrent import Torrent
from tracker import Tracker
from protocol import Messages, KeepAlive, Choke, Unchoke, Interested, NotInterested, Have, Bitfield, Request, Piece, Cancel, Port

from tornado.ioloop import IOLoop
from tornado.iostream import IOStream
from tornado.tcpserver import TCPServer
from tornado.log import enable_pretty_logging
from tornado.gen import coroutine, Task, Return, engine

from utils import peer_id

class Client(object):
    protocol = 'BitTorrent protocol'

    def __init__(self, stream, peer, server):
        logging.info('Connected to %s', peer)

        self.stream = stream
        self.peer = peer
        self.server = server

        self.am_choking = True
        self.peer_choking = True

        self.am_interested = False
        self.peer_interested = False

        self.peer_pieces = {}

        self.handshake()

    @coroutine
    def get_message(self):
        bytes = yield Task(self.stream.read_bytes, 4)
        length = struct.unpack('!I', bytes)[0]

        if length == 0:
            raise Return(KeepAlive())

        id = ord((yield Task(self.stream.read_bytes, 1)))

        if id not in Messages:
            raise ValueError('Invalid message type')

        data = yield Task(self.stream.read_bytes, length - 1)
        result = (Messages[id], Messages[id].unpack(data))

        raise Return(result)

    @coroutine
    def message_loop(self):
        logging.info('Starting message loop')

        while True:
            message_type, message = yield self.get_message()

            print message_type, repr(message)


    @coroutine
    def handshake(self):
        message = chr(len(self.protocol))
        message += self.protocol
        message += '\x00' * 8
        message += self.server.torrent.info_hash()

        logging.info('Sending a handshake: %s', repr(message))
        result = yield Task(self.stream.write, message)

        logging.info('Listening for a handshake')

        protocol_length = yield Task(self.stream.read_bytes, 1)
        protocol_name = yield Task(self.stream.read_bytes, ord(protocol_length))
        reserved_bytes = yield Task(self.stream.read_bytes, 8)
        info_hash = yield Task(self.stream.read_bytes, 20)

        yield Task(self.stream.write, self.server.peer_id)
        peer_id = yield Task(self.stream.read_bytes, 20)

        logging.info('Shook hands with %s', repr(peer_id))

        self.message_loop()

class Server(TCPServer):
    def __init__(self, torrent):
        TCPServer.__init__(self)

        self.torrent = torrent
        self.peer_id = peer_id()

    def start(self, num_processes=1):
        TCPServer.start(self, num_processes)

        logging.info('Announcing to tracker %s', self.torrent.tracker.url)
        response = self.torrent.tracker.announce(self.peer_id, self.port, event='started', num_wanted=10, compact=True)
        self.peers = list(response.peers)

        logging.info('Got %d peers', len(self.peers))

        self.connect(self.peers[0])

    def connect(self, peer):
        logging.info('Connecting to %s', peer)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)

        stream = IOStream(sock)
        stream.connect((peer.address, peer.port))

        Client(stream, peer, self)

    def listen(self, port, address=""):
        self.port = port

        TCPServer.listen(self, port, address)

    def handle_stream(self, stream, address):
        logging.info('Got a connection from %s', address)

        Client(stream, address, self)

if __name__ == '__main__':
    enable_pretty_logging()

    torrent = Torrent('ubuntu-13.04-desktop-amd64.iso.torrent')
    
    server = Server(torrent)
    server.listen(6881)
    server.start()

    IOLoop.instance().start()