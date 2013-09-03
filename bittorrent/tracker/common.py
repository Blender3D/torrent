from bittorrent import utils
from bittorrent.peer import Peer

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
            for chunk in utils.grouper(6, peers):
                yield Peer(*utils.unpack_peer_address(''.join(chunk)))
