import utils
import bencode

from peer import Peer

from tornado.httpclient import HTTPClient
from tornado.httputil import url_concat

class Tracker(object):
    def __init__(self, url, torrent, tier=0):
        self.url = url
        self.tier = tier
        self.torrent = torrent

        self.client = HTTPClient()

    def announce(self, peer_id, port, event='started', num_wanted=10, compact=True):
        tracker_url = url_concat(self.url, {
            'info_hash': self.torrent.info_hash(),
            'peer_id': peer_id,
            'port': port,
            'uploaded': self.torrent.uploaded,
            'downloaded': self.torrent.downloaded,
            'left': self.torrent.remaining,
            'event': event,
            'num_wanted': num_wanted,
            'compact': int(compact)
        })

        response = self.client.fetch(tracker_url)

        return TrackerResponse(bencode.bdecode(response.body))

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