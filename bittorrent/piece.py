import os
import hashlib

from utils import ceil_div, create_and_open, mkdirs

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
        self.blocks = [None] * self.num_blocks

    @classmethod
    def from_torrent(cls, torrent, base_path=None):
        files = []
        hashes = list(torrent.piece_hashes)
        block_size = torrent.meta['info']['piece length']

        if 'length' in torrent.meta['info']:
            path = torrent.meta['info']['name']
            size = torrent.meta['info']['length']

            if base_path is not None:
                mkdirs(base_path)
                path = os.path.join(base_path, path)

            handle = create_and_open(path, 'r+b', size=size)

            files.append(PiecedFile(handle, size))
        else:
            if base_path is not None:
                base_path = torrent.meta['info']['name']

            for info in torrent.meta['info']['files']:
                folders = [base_path] + info['path'][:-1]
                filename = info['path'][-1]
                directory = os.path.join(*folders)

                mkdirs(directory)

                size = info['length']
                handle = create_and_open(os.path.join(directory, filename), 'r+b', size=size)

                files.append(PiecedFile(handle, size))

        return cls(files, block_size, hashes)

    def get_file_by_block(self, index):
        offset = 0
        block_offset = index * self.block_size

        for file in self.files:
            if offset <= block_offset < offset + file.size:
                file.handle.seek(block_offset - offset)

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
        file.handle.seek(offset, 1)

        return file.handle.read(length)

    def write_piece(self, index, offset, data):
        if offset >= self.block_size:
            raise ValueError('Offset must be smaller than the block size')

        if offset + len(data) > self.block_size:
            raise ValueError('Cannot write across blocks')

        if index == self.num_blocks - 1 and offset + length > self.last_block_size:
            raise ValueError('Cannot write past end of last block')

        file = self.get_file_by_block(index)
        file.handle.seek(offset, 1)
        file.handle.write(data)

        self.verify_block(index, force=True)

    def read_block(self, index):
        if index == self.num_blocks - 1:
            return self.read_piece(index, 0, self.last_block_size)
        else:
            return self.read_piece(index, 0, self.block_size)

    def write_block(self, index, data):
        if len(data) != self.block_size or (index == self.num_blocks - 1 and len(data) != self.last_block_size):
            raise ValueError('Data must fill an entire block')

        self.write_piece(index, 0, data)
        self.verify_block(index, force=True)

    def verify_block(self, index, force=False):
        if not (0 <= index < self.num_blocks):
            raise ValueError('Invalid block index')

        if not force and self.blocks[index] is not None:
            return self.blocks[index]

        verified = hashlib.sha1(self.read_block(index)).digest() == self.block_hashes[index]
        self.blocks[index] = verified

        return verified

    def verify(self):
        return all(self.verify_block(index) for index in range(self.num_blocks))

    def to_bitfield(self):
        return {index: self.verify_block(index) for index in range(self.num_blocks)}

    def piece_chart(self):
        result = ''

        for index in range(self.num_blocks):
            data = self.read_block(index)
            hash = hashlib.sha1(data).digest()

            if hash == self.block_hashes[index]:
                result += '*'
            elif data.strip('\x00') != '':
                result += 'o'
            else:
                result += '.'

        return result

    def __str__(self):
        return '<PiecedFileSystem ' + self.piece_chart() + '>'

    def __del__(self):
        for file in self.files:
            file.handle.close()
            del file

if __name__ == '__main__':
    from torrent import Torrent

    torrent = Torrent('ubuntu-13.04-desktop-amd64.iso.torrent')
    f = PiecedFileSystem.from_torrent(torrent)
    print f
