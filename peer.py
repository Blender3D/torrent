class Peer(object):
    def __init__(self, address, port, id=None):
        self.address = address
        self.port = port
        self.id = id

    def __repr__(self):
        return '<Peer {self.address}:{self.port}>'.format(self=self)