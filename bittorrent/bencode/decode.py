import itertools
import collections

def decode(data):
    return consume(LookaheadIterator(data))

def consume(stream):
    item = stream.next_item

    if item == 'i':
        return consume_int(stream)
    elif item == 'l':
        return consume_list(stream)
    elif item == 'd':
        return consume_dict(stream)
    elif item is not None:
        return consume_str(stream)
    else:
        raise ValueError()

class LookaheadIterator(collections.Iterator):
    def __init__(self, iterator):
        self.iterator, self.next_iterator = itertools.tee(iter(iterator))
        self._advance()

    def _advance(self):
        self.next_item = next(self.next_iterator, None)

    def next(self):
        self._advance()

        return next(self.iterator)

def consume_number(stream):
    result = ''

    while True:
        chunk = stream.next_item

        if not chunk.isdigit():
            return result

        next(stream)
        result += chunk

def consume_int(stream):
    if next(stream) != 'i':
        raise ValueError()

    negative = stream.next_item == '-'

    if negative:
        next(stream)

    result = int(consume_number(stream))

    if negative and result == 0:
        raise ValueError('Negative zero is not allowed')

    if negative:
        result *= -1

    if next(stream) != 'e':
        raise ValueError('Unterminated integer')

    return result

def consume_str(stream):
    length = int(consume_number(stream))

    if next(stream) != ':':
        raise ValueError('Malformed string')

    result = ''

    for i in range(length):
        try:
            result += next(stream)
        except StopIteration:
            raise ValueError('Invalid string length')

    return result

def consume_list(stream):
    if next(stream) != 'l':
        raise ValueError()

    l = []

    while stream.next_item != 'e':
        l.append(consume(stream))

    if next(stream) != 'e':
        raise ValueError('Unterminated list')

    return l

def consume_dict(stream):
    if next(stream) != 'd':
        raise ValueError()

    d = {}

    while stream.next_item != 'e':
        key = consume(stream)

        if not isinstance(key, basestring):
            raise ValueError('Dictionary keys must be strings')

        value = consume(stream)

        d[key] = value

    if next(stream) != 'e':
        raise ValueError('Unterminated dictionary')

    return d