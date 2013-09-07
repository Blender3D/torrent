import random
import struct

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