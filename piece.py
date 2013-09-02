import os
import errno
import hashlib

from utils import ceil_div, create_and_open

class PiecedFile(object):
    def __init__(self, handle, size):
        self.handle = handle
        self.size = size

class PiecedFileSystem(object):
    def __init__(self, files, block_size, block_hashes):
        self.files = []
        self.size = 0

        for file in files:
            self.size += file.size
            self.files.append(file)

        self.block_size = block_size

        self.num_blocks = ceil_div(self.size, block_size)
        self.last_block_size = self.size - self.block_size * self.num_blocks

        self.block_hashes = block_hashes

    @classmethod
    def from_torrent(cls, torrent):
        files = []
        hashes = list(torrent.piece_hashes)
        block_size = torrent.meta['info']['piece length']

        if 'length' in torrent.meta['info']:
            path = torrent.meta['info']['name']
            size = torrent.meta['info']['length']
            handle = create_and_open(path, 'r+b')
            handle.truncate(size)

            files.append(PiecedFile(handle, size))
        else:
            base_path = torrent.meta['info']['name']

            for info in torrent.meta['info']['files']:
                folders = [base_path] + info['path'][:-1]
                filename = info['path'][-1]
                path = os.path.join(*folders)

                try:
                    os.makedirs(path)
                except OSError as e:
                    if e.errno == errno.EEXIST and os.path.isdir(path):
                        pass
                    else:
                        raise

                path = os.path.join(*(folders + [filename]))
                size = info['length']
                handle = create_and_open(path, 'r+b')
                handle.truncate(size)

                files.append(PiecedFile(handle, size))

        return cls(files, block_size, hashes)

    def get_file_by_block(self, index):
        offset = 0
        block_offset = index * self.block_size

        for file in self.files:
            if offset <= block_offset < offset + file.size:
                return file
            else:
                offset += file.size

        raise ValueError('Invalid block index')

    def read_piece(self, index, offset, length):
        if offset >= self.block_size:
            raise ValueError('Offset must be smaller than the block size')

        if offset + length > self.block_size:
            raise ValueError('Cannot read across blocks')

        if index == self.num_blocks - 1 and offset + length > self.last_block_size:
            raise ValueError('Cannot read past end of last block')

        file = self.get_file_by_block(index)
        file.handle.seek(offset)

        return file.handle.read(length)

    def write_piece(self, index, offset, data):
        if offset >= self.block_size:
            raise ValueError('Offset must be smaller than the block size')

        if offset + len(data) > self.block_size:
            raise ValueError('Cannot write across blocks')

        if index == self.num_blocks - 1 and offset + length > self.last_block_size:
            raise ValueError('Cannot write past end of last block')

        file = self.get_file_by_block(index)
        file.handle.seek(offset)
        file.handle.write(data)

    def read_block(self, index):
        if index == self.num_blocks - 1:
            return self.read_piece(index, 0, self.last_block_size)
        else:
            return self.read_piece(index, 0, self.block_size)

    def write_block(self, index, data):
        if len(data) != self.block_size or (index == self.num_blocks - 1 and len(data) != self.last_block_size):
            raise ValueError('Data must fill an entire block')

        return self.write_piece(index, 0, data)

    def verify_block(self, index):
        if not (0 <= index < self.num_blocks):
            raise ValueError('Invalid block index')

        return hashlib.sha1(self.read_block(index)).digest() == self.block_hashes[index]

    def verify(self):
        return all(self.verify_block(index) for index in range(self.num_blocks))

    def piece_chart(self):
        return ''.join('*' if self.verify_block(index) else '.' for index in range(self.num_blocks))

    def __str__(self):
        return '<PiecedFileSystem ' + self.piece_chart() + '>'

if __name__ == '__main__':
    from torrent import Torrent

    torrent = Torrent('ubuntu-13.04-desktop-amd64.iso.torrent')
    f = PiecedFileSystem.from_torrent(torrent)
    print f
