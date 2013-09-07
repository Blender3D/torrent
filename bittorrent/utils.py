import os
import struct
import itertools
import errno

peer_address_struct = struct.Struct('!BBBBH')

def peer_id():
    client_id = '-PT0000-'

    return client_id + os.urandom(20 - len(client_id))

def unpack_peer_address(data):
    address = peer_address_struct.unpack(data)

    return '.'.join(map(str, address[:4])), address[4]

def grouper(n, iterable, fillvalue=None):
    args = [iter(iterable)] * n

    return itertools.izip_longest(fillvalue=fillvalue, *args)

def ceil_div(a, b):
    return a // b + int(bool(a % b))

def create_and_open(name, mode='r', size=None):
    try:
        return open(name, mode)
    except IOError:
        with open(name, 'w') as handle:
            if size is not None:
                handle.truncate(size)
    finally:
        return open(name, mode)

def mkdirs(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise