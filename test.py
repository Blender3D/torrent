import unittest
import bencode

class TestBencodeEncode(unittest.TestCase):
    def test_string(self):
        self.assertEquals(bencode.bencode('test'), '4:test')
        self.assertRaises(UnicodeEncodeError, bencode.bencode, u'\u041c\u043e\u0441\u043a\u0432\u0430')

    def test_int(self):
        self.assertEquals(bencode.bencode(12), 'i12e')
        self.assertEquals(bencode.bencode(-12), 'i-12e')
        self.assertEquals(bencode.bencode(-0), 'i0e')

    def test_list(self):
        self.assertEquals(bencode.bencode([]), 'le')
        self.assertEquals(bencode.bencode([
            ['test', 2], [
                ['foo'], [3]
            ]
        ]), 'll4:testi2eell3:fooeli3eeee')

    def test_dict(self):
        self.assertEquals(bencode.bencode({}), 'de')
        self.assertEquals(bencode.bencode({
            'test': 12,
            'foo': [
                'bar',
                {'test': ['again', 12]}
            ]
        }), 'd3:fool3:bard4:testl5:againi12eeee4:testi12ee')

class TestBencodeDecode(unittest.TestCase):
    def test_string(self):
        self.assertEquals(bencode.bdecode('4:test'), 'test')

    def test_int(self):
        self.assertEquals(bencode.bdecode('i12e'), 12)
        self.assertEquals(bencode.bdecode('i-12e'), -12)
        self.assertEquals(bencode.bdecode('i0e'), 0)

    def test_list(self):
        self.assertEquals(bencode.bdecode('le'), [])
        self.assertEquals(bencode.bdecode('ll4:testi2eell3:fooeli3eeee'), [
            ['test', 2], [
                ['foo'], [3]
            ]
        ])

    def test_dict(self):
        self.assertEquals(bencode.bdecode('de'), {})
        self.assertEquals(bencode.bdecode('d3:fool3:bard4:testl5:againi12eeee4:testi12ee'), {
            'test': 12,
            'foo': [
                'bar',
                {'test': ['again', 12]}
            ]
        })

        self.assertRaises(ValueError, bencode.bdecode, 'di1ei1ee')

    def test_edge_cases(self):
        self.assertRaises(ValueError, bencode.bdecode, '04:test')
        self.assertRaises(ValueError, bencode.bdecode, 'i-0e')
        self.assertRaises(ValueError, bencode.bdecode, 'i01e')
        self.assertRaises(ValueError, bencode.bdecode, '')


if __name__ == '__main__':
    unittest.main()