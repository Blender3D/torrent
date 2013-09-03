def encode(obj):
    if isinstance(obj, basestring):
        return '{0}:{1}'.format(len(obj), obj)
    elif isinstance(obj, int):
        return 'i{0}e'.format(obj)
    elif isinstance(obj, list):
        values = ''.join([encode(o) for o in obj])

        return 'l{0}e'.format(values)
    elif isinstance(obj, dict):
        items = sorted(obj.items())
        values = ''.join([encode(str(key)) + encode(value) for key, value in items])

        return 'd{0}e'.format(values)
    else:
        raise TypeError('Unsupported type: {0}'.format(type(obj)))