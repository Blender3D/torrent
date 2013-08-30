import unittest
import struct

import bencode

from protocol import KeepAlive, Choke, Have, Bitfield

class TestBencodeEncode(unittest.TestCase):
    def test_string(self):
        self.assertEqual(bencode.bencode('test'), '4:test')

    def test_int(self):
        self.assertEqual(bencode.bencode(12), 'i12e')
        self.assertEqual(bencode.bencode(-12), 'i-12e')
        self.assertEqual(bencode.bencode(-0), 'i0e')

    def test_list(self):
        self.assertEqual(bencode.bencode([]), 'le')
        self.assertEqual(bencode.bencode([
            ['test', 2], [
                ['foo'], [3]
            ]
        ]), 'll4:testi2eell3:fooeli3eeee')

    def test_dict(self):
        self.assertEqual(bencode.bencode({}), 'de')
        self.assertEqual(bencode.bencode({
            'test': 12,
            'foo': [
                'bar',
                {'test': ['again', 12]}
            ]
        }), 'd3:fool3:bard4:testl5:againi12eeee4:testi12ee')

class TestBencodeDecode(unittest.TestCase):
    def test_string(self):
        self.assertEqual(bencode.bdecode('4:test'), 'test')

    def test_int(self):
        self.assertEqual(bencode.bdecode('i12e'), 12)
        self.assertEqual(bencode.bdecode('i-12e'), -12)
        self.assertEqual(bencode.bdecode('i0e'), 0)

    def test_list(self):
        self.assertEqual(bencode.bdecode('le'), [])
        self.assertEqual(bencode.bdecode('ll4:testi2eell3:fooeli3eeee'), [
            ['test', 2], [
                ['foo'], [3]
            ]
        ])

    def test_dict(self):
        self.assertEqual(bencode.bdecode('de'), {})
        self.assertEqual(bencode.bdecode('d3:fool3:bard4:testl5:againi12eeee4:testi12ee'), {
            'test': 12,
            'foo': [
                'bar',
                {'test': ['again', 12]}
            ]
        })

        self.assertRaises(ValueError, bencode.bdecode, 'di1ei1ee')

    def test_edge_cases(self):
        self.assertRaises(ValueError, bencode.bdecode, 'i-0e')
        self.assertRaises(ValueError, bencode.bdecode, '')

class TestTorrentMetadataReader(unittest.TestCase):
    def test_read(self):
        import json

        with open('ubuntu-13.04-desktop-amd64.iso.torrent', 'rb') as handle:
            with open('ubuntu-13.04-desktop-amd64.iso.json', 'wb') as output:
                metadata = bencode.bdecode(handle.read())
                #data = json.dumps(metadata)

                output.write(repr(metadata))

class TestProtocolMessages(unittest.TestCase):
    def test_keep_alive(self):
        self.assertIsInstance(KeepAlive.unpack(''), KeepAlive)
        self.assertIsInstance(KeepAlive.unpack(KeepAlive().pack(), with_header=True), KeepAlive)

    def test_choke(self):
        self.assertIsInstance(Choke.unpack(''), Choke)
        self.assertIsInstance(Choke.unpack(Choke().pack(), with_header=True), Choke)

    def test_have(self):
        self.assertEqual(Have.unpack(Have(piece=123).pack(), with_header=True).piece, 123)
        self.assertRaises(struct.error, Have(piece=12345678910).pack)

    def test_bitfield(self):
        self.assertEqual(Bitfield.unpack(Bitfield({
            0: True,
            1: False,
            2: False,
            3: True
        }).pack(), with_header=True).bitfield, {
            0: True,
            1: False,
            2: False,
            3: True
        })

if __name__ == '__main__':
    unittest.main()