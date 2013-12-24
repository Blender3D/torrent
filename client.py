import logging
import socket
import struct
import random
import functools

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
        want = [p for p in self.peer_pieces if not self.server.filesystem.blocks[p]]
        have = [p for p in self.peer_pieces if self.server.filesystem.blocks[p]]

        logging.debug('I have %s', repr(have))
        logging.debug('I want %s', repr(want))

        return want

    def maybe_express_interest(self):
        if self.am_interested:
            return

        if self.is_endgame:
            logging.debug('It\'s the endgame, so we\'re always interested')

            self.am_interested = True
            self.send_message(Interested())

            return

        if self.desired_pieces():
            logging.debug('Peer has something good. I am interested.')
            self.am_interested = True
            self.send_message(Interested())
        else:
            logging.debug('Nope, peer\'s got nothin\': %s', repr(self.desired_pieces()))
            self.am_interested = False
            self.send_message(NotInterested())

    def send_keepalive(self):
        self.send_message(KeepAlive())

    @property
    def missing_pieces(self):
        return [i for i in range(self.server.filesystem.num_blocks) if not self.server.filesystem.blocks[i]]

    @property
    def is_endgame(self):
        return len(self.missing_pieces) / float(self.server.filesystem.num_blocks) < 0.05

    @coroutine
    @gen_debuggable
    def message_loop(self, _=None):
        PeriodicCallback(self.send_keepalive, 30 * 1000).start()

        bitfield = Bitfield(self.server.filesystem.to_bitfield())

        if bitfield:
            self.send_message(bitfield)

        while True:
            while self.message_queue:
                self.send_message(self.message_queue.pop(0))

            message_type, message = yield self.get_message()

            logging.debug('Client sent us a %s', message.__class__.__name__)

            if isinstance(message, Unchoke):
                self.maybe_express_interest()
                piece = random.choice(self.desired_pieces())

                for start in range(0, self.server.filesystem.block_size, 2**14):
                    self.send_message(Request(piece, start, 2**14))
            elif isinstance(message, Bitfield):
                truncated = {key: value for key, value in message.bitfield.items() if key < self.server.filesystem.num_blocks}

                self.peer_pieces = truncated
                self.maybe_express_interest()
            elif isinstance(message, Have):
                self.peer_pieces[message.piece] = True
                self.maybe_express_interest()
            elif isinstance(message, Piece):
                logging.debug('Piece info: %d, %d, %d', message.index, message.begin, len(message.block))
                #self.peer.add_data_sample(len(message.block))
                self.server.filesystem.write_piece(message.index, message.begin, message.block)

                if self.server.filesystem.verify_block(message.index):
                    logging.info('Got a complete piece!')
                    logging.critical(self.server.filesystem)

                    if self.server.filesystem.verify():
                        logging.info('We got the file!')
                        IOLoop.instance().stop()

                    self.server.announce_message(Have(message.index))
            elif isinstance(message, Request):
                if message.length > 2**15:
                    raise ValueError('Requested too much data')

                data = self.server.filesystem.read_piece(message.index, message.begin, message.length)
                self.send_message(Piece(message.index, message.begin, data))
            else:
                logging.error('Invalid message received %s', repr(message))

            if self.is_endgame:
                if self.server.filesystem.verify():
                    logging.info('We got the file!')
                    IOLoop.instance().stop()

                for piece in self.missing_pieces:
                    for start in range(0, self.server.filesystem.block_size, 2**14):
                        self.server.announce_message(Request(piece, start, 2**14))

    def read_bytes(self, bytes):
        return Task(self.stream.read_bytes, bytes)

    def write(self, data):
        return Task(self.stream.write, data)

    @coroutine
    @gen_debuggable
    def send_message(self, message):
        logging.debug('Sending a %s', message.__class__.__name__)
        yield Task(self.stream.write, message.pack())
        logging.debug('Sent a %s', message.__class__.__name__)

    @coroutine
    @gen_debuggable
    def handshake(self):
        message = chr(len(self.protocol))
        message += self.protocol
        message += '\0' * 8
        message += self.server.torrent.info_hash()
        message += self.server.peer_id

        logging.debug('Sending a handshake')
        logging.debug(repr(message))

        yield self.write(message)

        logging.debug('Listening for a handshake')

        protocol_length = yield self.read_bytes(1)
        protocol_name = yield self.read_bytes(ord(protocol_length))
        reserved_bytes = yield self.read_bytes(8)
        info_hash = yield self.read_bytes(20)
        peer_id = yield self.read_bytes(20)

        logging.debug('Shook hands with %s', repr(peer_id))

        self.message_loop()

    def disconnected(self, result=None):
        logging.info('Peer disconnected %s', self.peer)
        self.server.peer_disconnected(self.peer)



class Server(TCPServer):
    def __init__(self, torrent, max_peers=20, download_path='downloads'):
        TCPServer.__init__(self)

        self.peer_id = peer_id()
        self.torrent = torrent

        self.max_peers = max_peers
        self.connected_peers = set()
        self.connecting_peers = set()
        self.unconnected_peers = set()

        self.filesystem = PiecedFileSystem.from_torrent(torrent, base_path=download_path)

    @coroutine
    @gen_debuggable
    def start(self, num_processes=1):
        TCPServer.start(self, num_processes)

        self.connect_to_peers()

    @coroutine
    @gen_debuggable
    def scrape_trackers(self):
        yield [self.scrape_tracker(tracker) for tracker in self.torrent.trackers]

    @coroutine
    @gen_debuggable
    def scrape_tracker(self, tracker):
        logging.info('Announcing to tracker %s', tracker.url)

        seen_peers = self.connected_peers & self.connecting_peers
        tracker_response = yield tracker.announce(self.peer_id, self.port, event='started', num_wanted=50)
        logging.info('Announced to tracker %s', tracker.url)

        self.unconnected_peers.update(set(tracker_response.peers) - seen_peers)

    @coroutine
    @gen_debuggable
    def connect_to_peers(self):
        if not self.unconnected_peers:
            yield self.scrape_trackers()

        if not self.unconnected_peers:
            logging.warning('Trackers did not respond with any new peers!')
            return

        num_active = self.max_peers - len(self.connected_peers) - len(self.connecting_peers)

        for i in range(min(len(self.unconnected_peers), num_active)):
            self.connect(self.unconnected_peers.pop())

    def connect(self, peer):
        logging.info('Connecting to %s', peer)
        self.connecting_peers.append(peer)

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)

        stream = IOStream(sock)
        client = Client(stream, peer, self)
        stream.set_close_callback(lambda: self.peer_disconnected(client))
        stream.connect((peer.address, peer.port), callback=lambda: self.peer_connected(client))

    def peer_not_connected(self, client):
        if client in self.connecting_peers:
            logging.error('Could not connnect to %s', client)
            self.connecting_peers.remove(client)
        elif client in self.connected_peers:
            logging.error('Peer disconnected: %s', client)
            self.connected_peers.remove(client)

        self.connect_to_peers()


    def peer_connected(self, client):
        logging.info('Connnected to %s', client)

        self.connecting_peers.remove(client)
        self.connected_peers.add(client)

    def announce_message(self, message):
        for client in self.connected_peers:
            client.message_queue.append(message)

    def listen(self, port, address=""):
        self.port = port

        TCPServer.listen(self, port, address)



if __name__ == '__main__':
    enable_pretty_logging()
    #IOLoop.instance().set_blocking_log_threshold(0.1)
    logging.getLogger().setLevel(logging.DEBUG)

    torrent = Torrent('torrents/[kickass.to]pixies.where.is.my.mind.torrent')
    
    server = Server(torrent)
    server.listen(6881)
    server.start()

    IOLoop.instance().start()
