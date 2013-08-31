import hashlib
import mmap

class PiecedFileSystem(object):
    def __init__(self):
        self.files = l

class PiecedFile(object):
    def __init__(self, handle, size, pieces):
        if isinstance(handle, basestring):
            try:
                self.handle = open(handle, 'r+')
            except IOError:
                open(handle, 'w').close()
            finally:
                self.handle = open(handle, 'r+')
        else:
            self.handle = handle

        self.size = size
        self.pieces = pieces
        self.piece_size = pieces[0].size

        self.mmap = mmap.mmap(self.handle.fileno(), size)

    def has_piece(self, index):
        return self.pieces[index].completed

    def verify(self, lazy=True):
        for piece in self.pieces:
            if lazy and piece.complete:
                continue

            piece.complete = piece.verify(self.read_piece(piece.index))

        return all(piece.complete for piece in self.pieces)

    def read_piece(self, index, offset=0, length=None):
        piece = self.pieces[index]
        length = length or piece.size
        start = index * self.piece_size + offset

        return self.mmap[start:start + length]

    def write_piece(self, index, offset, data):
        piece = self.pieces[index]
        
        if piece.complete:
            return

        start = index * self.piece_size + offset

        self.mmap[start:start + len(data)] = data

        if piece.verify(self.read_piece(index)):
            piece.complete = True
            self.mmap.flush()
            self.handle.flush()

            print self.percent_done()

            return True

    def percent_done(self):
        return '{:0.2f}%'.format(100 * float(sum(piece.complete for piece in self.pieces)) / len(self.pieces))

    def progress(self):
        return ''.join(str(int(piece.complete)) for piece in self.pieces)

    def to_bitfield(self):
        return {piece.index: piece.complete for piece in self.pieces}

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
    print f.progress()