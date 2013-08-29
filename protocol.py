import struct
import inspect

class Message(object):
    id = None
    structure = None

    @classmethod
    def _pack(cls, *args):
        return struct.pack(cls.structure, *args)

    @classmethod
    def _unpack(cls, data):
        result = struct.unpack(cls.structure, data)

        return result[0] if len(result) == 1 else result

    @classmethod
    def pack(cls, *args):
        data = cls._pack(*args) if cls.structure else ''

        return struct.pack('!I', len(data)) + data

    @classmethod
    def unpack(cls, data):
        return cls._unpack(data)

class KeepAlive(Message):
    pass

class Choke(Message):
    id = 0

class Unchoke(Message):
    id = 1

class Interested(Message):
    id = 2

class NotInterested(Message):
    id = 3

class Have(Message):
    id = 4
    structure = '!I'

class Bitfield(Message):
    id = 5

    @classmethod
    def _pack(cls, bitfield):
        data = ''

        bits = ''.join(str(int(bitfield[i])) for i in range(max(bitfield) + 1))
        bits += '0' * (len(bits) % 8)

        for index in range(0, len(bits), 8):
            data += chr(int(bits[index:index + 8], 2))

        return data

    @classmethod
    def _unpack(cls, data):
        d = {}
        index = 0

        for char in data:
            ordinal = bin(ord(char))[2:].zfill(8)

            for bit in ordinal:
                d[index] = bool(int(bit))
                index += 1

        return d

class Request(Message):
    id = 6
    structure = '!III'

class Piece(Message):
    id = 7

    @classmethod
    def _pack(cls, index, begin, block):
        return struct.pack('!II', index, begin) + block

    @classmethod
    def _unpack(cls, data):
        index, begin = struct.unpack('!II', data[:8])

        return index, begin, data[8:]

class Cancel(Message):
    id = 8
    structure = '!III'

class Port(Message):
    id = 9
    structure = '!I'

Messages = {cls.id: cls for name, cls in locals().items() if inspect.isclass(cls) and issubclass(cls, Message)}