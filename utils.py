import os
import struct
import itertools
import operator

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

def accumulate(iterable, func=operator.add):
    it = iter(iterable)
    total = next(it)

    yield total

    for element in it:
        total = func(total, element)
        yield total

def ceil_div(a, b):
    return a // b + int(bool(a % b))

def create_and_open(name, mode='r'):
    try:
        return open(name, mode)
    except IOError:
        open(name, 'w').close()
    finally:
        return open(name, mode)