import struct
import random

from bittorrent import bencode

from twisted.internet import defer, reactor
from twisted.internet.protocol import DatagramProtocol

class UDPTrackerProtocol(DatagramProtocol):
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def startProtocol(self):
        self.transport.connect(self.host, self.port)
        self.sendConnect()

    def sendConnect(self):
        self.transaction_id = random.getrandbits(32)

        data = struct.pack('!QII', 0x41727101980, 0, self.transaction_id)
        self.transport.write(data)

    def datagramReceived(self, data):
        print 'Received', repr(data)

class UDPTracker(object):
    protocol = UDPTrackerProtocol

    def __init__(self, host, port, torrent, tier=0):
        self.host = host
        self.port = port

        self.torrent = torrent
        self.tier = tier

    @defer.inlineCallbacks
    def announce(self, peer_id, port, event='started', num_wanted=10):
        self.host = yield reactor.resolve(self.host)

        protocol = self.protocol(self.host, self.port)
        protocol.factory = self

        reactor.listenUDP(0, protocol)

if __name__ == '__main__':
    def success(*args, **kwargs):
        print args, kwargs

    def failure(failure):
        failure.printTraceback()

    from torrent.torrent import Torrent
    from torrent.utils import peer_id

    torrent = Torrent('[kickass.to]pixies.where.is.my.mind.torrent')
    tracker = torrent.tracker

    d = tracker.announce(peer_id(), 6881)
    d.addCallbacks(success, failure)
    d.addBoth(lambda reason: reactor.stop())

    reactor.run()