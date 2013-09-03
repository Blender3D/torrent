import utils
import bencode
import urllib

from peer import Peer

from twisted.web.client import Agent, readBody
from twisted.internet import defer, reactor

class HTTPTracker(object):
    def __init__(self, url, torrent, tier=0):
        self.url = url
        self.tier = tier
        self.torrent = torrent
        
        self.agent = Agent(reactor)

    @defer.inlineCallbacks
    def announce(self, peer_id, port, event='started', num_wanted=10, compact=True):
        parameters = urllib.urlencode({
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

        response = yield self.agent.request('GET', self.url + '?' + parameters)
        body = yield readBody(response)
        result = TrackerResponse(bencode.bdecode(body))

        defer.returnValue(result)

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

if __name__ == '__main__':
    def print_response(response):
        print response.peers

    from torrent import Torrent
    from utils import peer_id

    torrent = Torrent('ubuntu-13.04-desktop-amd64.iso.torrent')
    tracker = torrent.trackers[0]

    d = tracker.announce(peer_id(), 6881)
    d.addCallback(print_response)
    d.addBoth(lambda reason: reactor.stop())

    reactor.run()