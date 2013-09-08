import unittest
import struct

from tornado.testing import AsyncTestCase, gen_test

from bittorrent import bencode, utils
from bittorrent.torrent import Torrent
from bittorrent.protocol.message import KeepAlive, Choke, Have, Bitfield
from bittorrent.tracker import Tracker, HTTPTracker, UDPTracker, TrackerResponse

class TestBencode(unittest.TestCase):
    def test_string(self):
        self.assertEqual(bencode.encode('test'), '4:test')

    def test_int(self):
        self.assertEqual(bencode.encode(12), 'i12e')
        self.assertEqual(bencode.encode(-12), 'i-12e')
        self.assertEqual(bencode.encode(-0), 'i0e')

    def test_list(self):
        self.assertEqual(bencode.encode([]), 'le')
        self.assertEqual(bencode.encode([
            ['test', 2], [
                ['foo'], [3]
            ]
        ]), 'll4:testi2eell3:fooeli3eeee')

    def test_dict(self):
        self.assertEqual(bencode.encode({}), 'de')
        self.assertEqual(bencode.encode({
            'test': 12,
            'foo': [
                'bar',
                {'test': ['again', 12]}
            ]
        }), 'd3:fool3:bard4:testl5:againi12eeee4:testi12ee')

class TestBdecode(unittest.TestCase):
    def test_string(self):
        self.assertEqual(bencode.decode('4:test'), 'test')

    def test_int(self):
        self.assertEqual(bencode.decode('i12e'), 12)
        self.assertEqual(bencode.decode('i-12e'), -12)
        self.assertEqual(bencode.decode('i0e'), 0)

    def test_list(self):
        self.assertEqual(bencode.decode('le'), [])
        self.assertEqual(bencode.decode('ll4:testi2eell3:fooeli3eeee'), [
            ['test', 2], [
                ['foo'], [3]
            ]
        ])

    def test_dict(self):
        self.assertEqual(bencode.decode('de'), {})
        self.assertEqual(bencode.decode('d3:fool3:bard4:testl5:againi12eeee4:testi12ee'), {
            'test': 12,
            'foo': [
                'bar',
                {'test': ['again', 12]}
            ]
        })

        self.assertRaises(ValueError, bencode.decode, 'di1ei1ee')

    def test_edge_cases(self):
        self.assertRaises(ValueError, bencode.decode, 'i-0e')
        self.assertRaises(ValueError, bencode.decode, '')

class TestTorrentReader(unittest.TestCase):
    def test_read(self):
        Torrent('torrents/ubuntu-13.04-desktop-amd64.iso.torrent')

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

class TestTracker(AsyncTestCase):
    def test_autodetect(self):
        self.assertIsInstance(Tracker('udp://tracker.openbittorrent.com:80/announce', None), UDPTracker)
        self.assertIsInstance(Tracker('http://torrent.ubuntu.com:6969/announce', None), HTTPTracker)

        self.assertRaises(ValueError, Tracker, 'gopher://tracker.openbittorrent.com:80/announce', None)
        self.assertRaises(ValueError, Tracker, 'tracker.openbittorrent.com:80/announce', None)

    @gen_test
    def test_http(self):
        torrent = Torrent('torrents/ubuntu-13.04-desktop-amd64.iso.torrent')
        tracker = Tracker('http://torrent.ubuntu.com:6969/announce', torrent)

        response = yield tracker.announce(utils.peer_id(), 6881)

        self.assertIsInstance(response, TrackerResponse)

    @gen_test
    def test_udp(self):
        torrent = Torrent('torrents/ubuntu-13.04-desktop-amd64.iso.torrent')
        tracker = Tracker('udp://tracker.openbittorrent.com:80/announce', torrent)

        response = yield tracker.announce(utils.peer_id(), 6881)

        self.assertIsInstance(response, TrackerResponse)

class TestUtils(unittest.TestCase):
    def test_fill(self):
        class FakeFile(object):
            def __init__(self):
                self.content = ''

            def write(self, data):
                self.content += data

            def seek(self, index):
                pass

        handle = FakeFile()
        utils.fill(handle, 1024)
        self.assertEquals(handle.content, '\x00' * 1024)


if __name__ == '__main__':
    unittest.main()