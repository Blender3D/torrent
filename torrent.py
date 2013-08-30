import hashlib
import bencode

from itertools import islice

from tracker import Tracker
from piece import Piece
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
                    raise TypeError('handle must be a file, a dict, a path, or a bencoded string. Got: {0}'.format(type(handle)))
        elif hasattr(handle, 'read'):
            self.meta = bencode.bdecode(handle.read())
        else:
            self.meta = {}

        self.uploaded = 100000
        self.downloaded = 1000000
        self.remaining = 7000000

        self.pieces = list(self._pieces())

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
    def size(self):
        return self.meta['info']['length']

    def _pieces(self):
        torrent_length = self.meta['info']['length']
        piece_length = self.meta['info']['piece length']

        num_pieces, incomplete_piece_length = divmod(torrent_length, piece_length)
        hashes = grouper(20, self.meta['info']['pieces'])

        for index, hash in enumerate(hashes):
            length = incomplete_piece_length if index == num_pieces else piece_length

            yield Piece(length, ''.join(hash), index)


if __name__ == '__main__':
    torrent = Torrent('ubuntu-13.04-desktop-amd64.iso.torrent')

    for piece in torrent.pieces:
        print piece