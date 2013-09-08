import logging
import socket
import struct
import random

from bittorrent.torrent import Torrent
from bittorrent.tracker import Tracker
from bittorrent.piece import PiecedFileSystem
from bittorrent.protocol.message import (Messages, KeepAlive, Choke,
                                         Unchoke, Interested, NotInterested,
                                         Have, Bitfield, Request, Piece, Cancel, Port)

from tornado.ioloop import IOLoop, PeriodicCallback
from tornado.iostream import IOStream
from tornado.tcpserver import TCPServer
from tornado.log import enable_pretty_logging
from tornado.gen import coroutine, Task, Return, engine

from bittorrent.utils import peer_id, gen_debuggable

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

    @coroutine
    @gen_debuggable
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

    @gen_debuggable
    def desired_pieces(self):
        logging.info('Let\'s see...')
        try:
            result = [p for p in self.peer_pieces if not self.server.filesystem.blocks[p]]
        except:
            print '**********************'
            import traceback
            print traceback.print_exc()

            print p, len(self.server.filesystem.blocks)

        logging.info('I want %s', repr(result))

        return result

    def maybe_express_interest(self):
        logging.info('Am I interested?')

        if self.am_interested:
            logging.info('I am already interested')
            return

        if self.desired_pieces():
            logging.info('Peer has something good. I am.')
            self.am_interested = True
            self.send_message(Interested())
        else:
            logging.info('Nope, peer\'s got nothin\': %s', repr(self.desired_pieces()))
            self.am_interested = False
            self.send_message(NotInterested())

    def send_keepalive(self):
        self.send_message(KeepAlive())

    @coroutine
    @gen_debuggable
    def message_loop(self):
        PeriodicCallback(self.send_keepalive, 30 * 1000).start()

        logging.info('Starting message loop')
        self.send_message(Bitfield(self.server.filesystem.to_bitfield()))

        while True:
            while self.message_queue:
                self.send_message(self.message_queue.pop(0))

            result = yield self.get_message()

            message_type, message = result

            logging.info('Client sent us a %s', message.__class__.__name__)

            if isinstance(message, Unchoke):
                self.maybe_express_interest()
                piece = random.choice(self.desired_pieces())

                for start in range(0, self.server.filesystem.block_size, 2**14):
                    self.send_message(Request(piece, start, 2**14))
            elif isinstance(message, Bitfield):
                self.peer_pieces = message.bitfield
                self.maybe_express_interest()
            elif isinstance(message, Have):
                self.peer_pieces[message.piece] = True
                self.maybe_express_interest()
            elif isinstance(message, Piece):
                logging.info('Piece info: %d, %d, %d', message.index, message.begin, len(message.block))
                #self.peer.add_data_sample(len(message.block))
                self.server.filesystem.write_piece(message.index, message.begin, message.block)

                if self.server.filesystem.verify_block(message.index):
                    logging.info('Got a complete piece!')
                    print self.filesystem

                    self.server.announce_message(Have(message.index))
            elif isinstance(message, Request):
                if message.length > 2**15:
                    raise ValueError('Requested too much data')

                data = self.server.filesystem.read_piece(message.index, message.begin, message.length)
                self.send_message(Piece(message.index, message.begin, data))
            else:
                logging.info('Invalid message received!!')
                logging.info('Invalid message received!!')
                logging.info('Invalid message received!!')
                logging.info('Invalid message received!!')
                logging.info('Invalid message received!!')
                logging.info('Invalid message received!!')
                logging.info('Invalid message received!!')
                logging.info('Invalid message received!!')
                logging.info('Invalid message received!!')
                logging.info('Invalid message received!!')
                logging.info('Invalid message received!!')
                logging.info('Invalid message received!!')
                logging.info('Invalid message received!!')
                logging.info('Invalid message received!!')
                logging.info('Invalid message received!!')
                logging.info('Invalid message received!!')

    def read_bytes(self, bytes):
        return Task(self.stream.read_bytes, bytes)

    def write(self, data):
        return Task(self.stream.write, data)

    def send_message(self, message):
        logging.info('Sending a %s', message.__class__.__name__)
        self.stream.write(message.pack())
        logging.info('Sent a %s', message.__class__.__name__)

    @coroutine
    @gen_debuggable
    def handshake(self):
        message = chr(len(self.protocol))
        message += self.protocol
        message += '\x00' * 8
        message += self.server.torrent.info_hash()
        message += self.server.peer_id

        logging.info('Sending a handshake')
        logging.info(repr(message))

        yield self.write(message)

        logging.info('Listening for a handshake')

        protocol_length = yield self.read_bytes(1)
        protocol_name = yield self.read_bytes(ord(protocol_length))
        reserved_bytes = yield self.read_bytes(8)
        info_hash = yield self.read_bytes(20)
        peer_id = yield self.read_bytes(20)

        logging.info('Shook hands with %s', repr(peer_id))
        self.message_loop()

    def received_keepalive(self):
        logging.info('Got a keepalive')

    def received_bitfield(self, bitfield):
        logging.info('Got a bitfield')

    def disconnected(self, result=None):
        logging.info('Peer disconnected %s', self.peer)
        self.server.disconnected(self)

class Server(TCPServer):
    def __init__(self, torrent):
        TCPServer.__init__(self)

        self.torrent = torrent
        self.clients = []
        
        self.filesystem = PiecedFileSystem.from_torrent(torrent, base_path='downloads')
        print self.filesystem

        self.peer_id = peer_id()

    @coroutine
    @gen_debuggable
    def start(self, num_processes=1):
        TCPServer.start(self, num_processes)

        self.peers = yield self.get_peers()
        logging.info('Got %d peers', len(self.peers))

        for peer in self.peers:
            self.connect(peer)

    @coroutine
    @gen_debuggable
    def get_peers(self):
        for tracker in self.torrent.trackers:
            try:
                logging.info('Announcing to tracker %s', tracker.url)
                
                response = yield tracker.announce(self.peer_id, self.port, event='started', num_wanted=50, compact=True)
                raise Return(response.peers)
            except Exception as e:
                print repr(e)
                if isinstance(e, Return):
                    raise e

                logging.info('Announce failed: %s', tracker.url)

    def connect(self, peer):
        logging.info('Connecting to %s', peer)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)

        stream = IOStream(sock)
        stream.connect((peer.address, peer.port))

        self.clients.append(Client(stream, peer, self))

    @coroutine
    @gen_debuggable
    def disconnected(self, client):
        self.clients.remove(client)
        
        try:
            self.peers.remove(client.peer)
        except IndexError:
            self.peers = yield self.get_peers()
            self.connect(self.peers[-1])

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
    IOLoop.instance().set_blocking_log_threshold(0.5)
    #logging.getLogger().setLevel(logging.ERROR)

    torrent = Torrent('torrents/[kickass.to]pixies.where.is.my.mind.torrent')
    
    server = Server(torrent)
    server.listen(6882)
    server.start()

    IOLoop.instance().start()