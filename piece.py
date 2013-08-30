import hashlib
import mmap

class PiecedFile(object):
    def __init__(self, handle, size, pieces):
        if isinstance(handle, basestring):
            open(handle, 'w').close()
            self.handle = open(handle, 'r+b')
        else:
            self.handle = handle

        self.size = size
        self.pieces = pieces
        self.piece_size = pieces[0].size

        self.mmap = mmap.mmap(self.handle.fileno(), size)
        self.mmap.flush()

    def verify(self, lazy=True):
        for piece in self.pieces:
            if lazy and piece.complete:
                continue

            offset = piece.index * self.piece_size
            piece.complete = piece.verify(self.mmap[offset:offset + piece.size])

        return all(piece.complete for piece in self.pieces)

    def close(self):
        self.mmap.close()
        self.handle.close()

class Piece(object):
    def __init__(self, size, hash, index):
        self.hash = hash
        self.size = size
        self.index = index
        self.complete = False

    def verify(self, data):
        return len(data) == self.size and hashlib.sha1(data).digest() == self.hash

    def __repr__(self):
        return '<Piece {0} {1}>'.format(self.index, self.hash.encode('hex'))

if __name__ == '__main__':
    from torrent import Torrent

    torrent = Torrent('ubuntu-13.04-desktop-amd64.iso.torrent')
    f = PiecedFile('ubuntu-13.04-desktop-amd64.iso', torrent.size, torrent.pieces)
    print f.verify()