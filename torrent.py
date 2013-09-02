import hashlib
import bencode

from tracker import Tracker
from utils import grouper

class Torrent(object):
    def __init__(self, handle=None):
        if isinstance(handle, dict):
            self.meta = handle
        elif isinstance(handle, basestring):
            try:
                with open(handle, 'rb') as input_file:
                    self.meta = bencode.bdecode(input_file.read())
            except IOError:
                try:
                    self.meta = bencode.bdecode(handle)
                except ValueError:
                    raise TypeError('handle must be a file, dict, path, or bencoded string. Got: {0}'.format(type(handle)))
        elif hasattr(handle, 'read'):
            self.meta = bencode.bdecode(handle.read())
        else:
            self.meta = {}

        self.uploaded = 1000000
        self.downloaded = 1000000
        self.remaining = 10000000

    def bencode(self):
        return bencode.bencode(self.meta)

    def save(self, filename):
        with open(filename, 'wb') as handle:
            handle.write(self.bencode())

    def info_hash(self, hex=False):
        hash = hashlib.sha1(bencode.bencode(self.meta['info']))

        if hex:
            return hash.hexdigest()
        else:
            return hash.digest()

    @property
    def trackers(self):
        trackers = self.meta.get('announce-list', [[self.meta['announce']]])
        result = []

        for tier, urls in enumerate(trackers):
            for url in urls:
                if url.startswith('http'):
                    tracker = Tracker(url, torrent=self, tier=tier)
                    result.append(tracker)

        return result

    @property
    def tracker(self):
        return self.trackers[0]

    @property
    def piece_hashes(self):
        hashes = grouper(20, self.meta['info']['pieces'])

        for index, hash in enumerate(hashes):
            yield ''.join(hash)