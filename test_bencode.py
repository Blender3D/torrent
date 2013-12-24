import unittest

from bittorrent import bencode, utils

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


if __name__ == '__main__':
    unittest.main()
