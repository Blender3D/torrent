import urllib
import struct

from bittorrent import bencode

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
        result = TrackerResponse(bencode.decode(body))

        defer.returnValue(result)