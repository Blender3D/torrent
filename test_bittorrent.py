import unittest
import struct

from tornado.testing import AsyncTestCase, gen_test

from bittorrent import utils
from bittorrent.torrent import Torrent
from bittorrent.protocol.message import KeepAlive, Choke, Have, Bitfield
from bittorrent.tracker import Tracker, HTTPTracker, UDPTracker, TrackerResponse

class TestTorrentReader(unittest.TestCase):
    def test_read(self):
        Torrent('torrents/archlinux-2013.12.01-dual.iso.torrent')

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
        b = {
            0: True,
            1: False,
            3: True
        }

        c = {
            0: True,
            1: False,
            2: False,
            3: True,
            4: False,
            5: False,
            6: False,
            7: False
        }

        self.assertEqual(
            Bitfield.unpack(Bitfield(b).pack(with_header=True), with_header=True).bitfield,
            c
        )

class TestTracker(AsyncTestCase):
    def test_autodetect(self):
        self.assertIsInstance(Tracker('udp://tracker.openbittorrent.com:80/announce', None), UDPTracker)
        self.assertIsInstance(Tracker('http://torrent.ubuntu.com:6969/announce', None), HTTPTracker)

        self.assertRaises(ValueError, Tracker, 'gopher://tracker.openbittorrent.com:80/announce', None)
        self.assertRaises(ValueError, Tracker, 'tracker.openbittorrent.com:80/announce', None)

    @gen_test
    def test_http(self):
        torrent = Torrent('torrents/archlinux-2013.12.01-dual.iso.torrent')
        tracker = Tracker('http://tracker.archlinux.org:6969/announce', torrent)

        response = yield tracker.announce(utils.peer_id(), 6881)

        self.assertIsInstance(response, TrackerResponse)

    @gen_test
    def test_udp(self):
        torrent = Torrent('torrents/archlinux-2013.12.01-dual.iso.torrent')
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
