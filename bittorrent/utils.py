import os
import struct
import itertools
import errno

from functools import wraps

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

def fill(handle, size):
    block_size = 2**18
    zeroes = '\x00' * block_size

    for chunk in range(0, size // block_size):
        handle.write(zeroes)

    # XXX: This is too complcated. What am I missing?
    handle.write('\x00' * (size - block_size * (size // block_size)))
    handle.seek(0)

def create_and_open(name, mode='r', size=None):
    try:
        return open(name, mode)
    except IOError:
        with open(name, 'wb') as handle:
            fill(handle, size)
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

def gen_debuggable(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as e:
            if isinstance(e, Return):
                raise e
            else:
                import traceback
                print traceback.print_exc()

    return wrapper