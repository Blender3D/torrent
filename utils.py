import os
import struct

peer_address_struct = struct.Struct('!BBBBH')

def peer_id():
    client_id = '-PT0000-'

    return client_id + os.urandom(20 - len(client_id))

def unpack_peer_address(data):
    address = peer_address_struct.unpack(data)

    return '.'.join(map(str, address[:4])), address[4]