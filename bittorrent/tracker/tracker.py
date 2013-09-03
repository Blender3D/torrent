import urlparse

from bittorrent.tracker.http import HTTPTracker
from bittorrent.tracker.udp import UDPTracker

def Tracker(url, torrent, tier=0):
    o = urlparse.urlsplit(url)

    if o.scheme == 'http':
        return HTTPTracker(url, torrent, tier)
    elif o.scheme == 'udp':
        return UDPTracker(o.hostname, o.port, torrent, tier)
    else:
        raise ValueError('Unsupported tracker protocol: ' + o.scheme)