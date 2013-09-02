import logging
import socket
import struct
import random

from torrent import Torrent
from tracker import Tracker
from piece import PiecedFileSystem
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
        self.stream.set_close_callback(self.disconnected)

        self.peer = peer
        self.server = server

        self.am_choking = True
        self.peer_choking = True

        self.am_interested = False
        self.peer_interested = False

        self.peer_pieces = {}
        self.message_queue = []

        self.handshake()

    def read_bytes(self, bytes):
        return Task(self.stream.read_bytes, bytes)

    def write(self, data):
        return Task(self.stream.write, data)

    def send_message(self, message):
        logging.info('Sending a %s', message.__class__.__name__)
        return self.write(message.pack())

    def send_message_whenever(self, message):
        logging.info('Lazily sending a %s', message.__class__.__name__)
        self.stream.write(message.pack())

    @coroutine
    def get_message(self):
        bytes = yield self.read_bytes(4)
        length = struct.unpack('!I', bytes)[0]

        if length == 0:
            raise Return((KeepAlive, KeepAlive()))

        id = ord((yield self.read_bytes(1)))

        if id not in Messages:
            raise ValueError('Invalid message type')

        data = yield self.read_bytes(length - 1)
        result = (Messages[id], Messages[id].unpack(data))

        raise Return(result)

    @coroutine
    def message_loop(self):
        logging.info('Starting message loop')
        result = yield self.send_message(Bitfield(self.server.file.to_bitfield()))

        while True:
            while self.message_queue:
                self.send_message_whenever(self.message_queue.pop(0))

            message_type, message = yield self.get_message()
            logging.info('Client sent us a %s', message.__class__.__name__)

            if isinstance(message, Unchoke):
                self.send_message_whenever(Unchoke())
                desired_pieces = [p for p in self.peer_pieces if p]

                if not desired_pieces:
                    self.send_message_whenever(NotInterested())
                else:
                    while True:
                        piece = random.choice(desired_pieces)

                        if self.peer_pieces[piece] and not self.server.file.pieces[piece].complete:
                            break

                    for start in range(0, self.server.file.piece_size, 2**14):
                        self.send_message_whenever(Request(piece, start, 2**14))
            elif isinstance(message, Bitfield):
                self.peer_pieces = message.bitfield
            elif isinstance(message, Have):
                self.peer_pieces[message.piece] = True
            elif isinstance(message, Piece):
                self.peer.add_data_sample(len(message.block))
                done = self.server.file.write_piece(message.index, message.begin, message.block)

                if done:
                    self.server.announce_message(Have(message.index))
            elif isinstance(message, Request):
                data = self.server.file.read_piece(message.index, message.begin, message.block)
                self.send_message_whenever(Piece(message.index, message.begin, data))

            try:
                logging.info('Peer\'s average speed is %d', self.peer.average_speed)
            except Exception as e:
                print e

    @coroutine
    def handshake(self):
        message = chr(len(self.protocol))
        message += self.protocol
        message += '\x00' * 8
        message += self.server.torrent.info_hash()
        message += self.server.peer_id

        logging.info('Sending a handshake')
        result = yield self.write(message)

        logging.info('Listening for a handshake')

        protocol_length = yield self.read_bytes(1)
        protocol_name = yield self.read_bytes(ord(protocol_length))
        reserved_bytes = yield self.read_bytes(8)
        info_hash = yield self.read_bytes(20)
        peer_id = yield self.read_bytes(20)

        logging.info('Shook hands with %s', repr(peer_id))

        self.message_loop()

    def disconnected(self):
        logging.info('Peer disconnected %s', self.peer)
        self.server.disconnected(self.peer)

class Server(TCPServer):
    def __init__(self, torrent):
        TCPServer.__init__(self)

        self.torrent = torrent
        self.clients = []
        
        self.filesystem = PiecedFileSystem.from_torrent(torrent)
        print self.filesystem

        self.peer_id = peer_id()

    def start(self, num_processes=1):
        TCPServer.start(self, num_processes)

        logging.info('Announcing to tracker %s', self.torrent.tracker.url)
        response = self.torrent.tracker.announce(self.peer_id, self.port, event='started', num_wanted=50, compact=True)
        self.peers = list(response.peers)

        logging.info('Got %d peers', len(self.peers))

        for peer in self.peers:
            self.connect(peer)

    def connect(self, peer):
        logging.info('Connecting to %s', peer)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)

        stream = IOStream(sock)
        stream.connect((peer.address, peer.port))

        self.clients.append(Client(stream, peer, self))

    def disconnected(self, peer):
        return
        self.clients.remove(peer)

    def announce_message(self, message):
        for client in self.clients:
            client.message_queue.append(message)

    def listen(self, port, address=""):
        self.port = port

        TCPServer.listen(self, port, address)

    def handle_stream(self, stream, address):
        logging.info('Got a connection from %s', address)

        Client(stream, address, self)

if __name__ == '__main__':
    enable_pretty_logging()
    #logging.getLogger().setLevel(logging.ERROR)

    torrent = Torrent('ubuntu-13.04-desktop-amd64.iso.torrent')
    
    server = Server(torrent)
    server.listen(6881)
    server.start()

    IOLoop.instance().start()