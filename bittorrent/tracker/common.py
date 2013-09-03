import urlparse

from bittorrent.tracker.http import HTTPTracker
from bittorrent.tracker.udp import UDPTracker

from bittorrent.peer import Peer

def Tracker(url, torrent, tier=0):
    o = urlparse.urlsplit(url)

    if o.scheme == 'http':
        return HTTPTracker(url, torrent, tier)
    elif o.scheme == 'udp':
        return UDPTracker(o.hostname, o.port, torrent, tier)
    else:
        raise ValueError('Unsupported tracker protocol: ' + o.scheme)

class TrackerResponse(object):
    def __init__(self, data):
        self.data = data
        self.peers = list(self._get_peers(data))
        self.request_interval = data['interval']

    def _get_peers(self, data):
        peers = data['peers']

        if isinstance(peers, list):
            for peer_dict in peers:
                yield Peer(peer_dict['ip'], peer_dict['port'], peer_dict['peer_id'])
        else:
            for index in range(0, len(peers), 6):
                yield Peer(*utils.unpack_peer_address(peers[index:index + 6]))