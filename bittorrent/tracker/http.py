import urllib
import struct

from bittorrent import bencode
from bittorrent.tracker import TrackerResponse

from tornado.gen import coroutine, Return
from tornado.httpclient import AsyncHTTPClient
from tornado.httputil import url_concat

class HTTPTracker(object):
    def __init__(self, url, torrent, tier=0):
        self.url = url
        self.tier = tier
        self.torrent = torrent

        self.client = AsyncHTTPClient()

    @coroutine
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

        response = yield self.client.fetch(tracker_url)
        result = TrackerResponse(bencode.decode(response.body))

        raise Return(result)