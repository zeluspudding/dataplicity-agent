from __future__ import print_function
from __future__ import unicode_literals
import six

"""
Encode / Decode Bencode (http://en.wikipedia.org/wiki/Bencode)

"""

import io
import sys

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY3:
    number_types = (int,)
    text_type = str
else:
    number_types = (long, int)
    text_type = unicode


class EncodingError(ValueError):
    pass


class DecodeError(Exception):
    pass


class DecoderError(Exception):
    """Exception occurred with the data being decoded"""
    (
        PRECEDING_ZERO_IN_SIZE,
        MAX_SIZE_REACHED,
        ILLEGAL_DIGIT_IN_SIZE,
        ILLEGAL_DIGIT
    ) = range(4)

    error_text = {
        PRECEDING_ZERO_IN_SIZE: "PRECEDING_ZERO_IN_SIZE",
        MAX_SIZE_REACHED: "MAX_SIZE_REACHED",
        ILLEGAL_DIGIT_IN_SIZE: "ILLEGAL_DIGIT_IN_SIZE",
        ILLEGAL_DIGIT: "ILLEGAL_DIGIT"
    }

    def __init__(self, code, text):
        self.code = code
        self.text = text
        super(DecoderError, self).__init__()

    def __str__(self):
        return "{} (#{}), {}".format(DecoderError.error_text[self.code], self.code, self.text)


def encode(obj):
    """Encode to Bencode, return bytes"""
    binary = []
    append = binary.append

    def add_encode(obj):
        if isinstance(obj, bytes):
            append(u"{}:".format(len(obj)).encode())
            append(obj)
        elif isinstance(obj, text_type):
            add_encode(obj.encode('utf-8'))
        elif isinstance(obj, number_types):
            # please note: because of unicode_literals being used, we can't use
            # six.b, for the simple reason that the python2 implementation of
            # b is as following:
            # def b(v):
            #     return v
            # this, combined with the unicode literals means that a string
            # (like "41" - after formatting a number) would actually turn into
            # an unicode.. and thus, a number after encoding would turn into
            # unicode object. This is not what we want. However, because these
            # are only digits, they can be safely encoded which would produce
            # bytes (in both python2 and 3)
            append(u"i{}e".format(obj).encode())
        elif isinstance(obj, (list, tuple)):
            append(b"l")
            for item in obj:
                add_encode(item)
            append(b'e')
        elif isinstance(obj, dict):
            append(b'd')
            keys = sorted(obj.keys())
            for k in keys:
                if not isinstance(k, bytes):
                    raise EncodingError("dict keys must be bytes")
                add_encode(k)
                add_encode(obj[k])
            append(b'e')
        else:
            raise EncodingError('value {!r} can not be encoded in Bencode'.format(obj))

    add_encode(obj)
    return b''.join(binary)


def decode(data):
    """Decode Bencode, return an object."""
    assert isinstance(data, bytes), "decode takes bytes"
    return _decode(io.BytesIO(data).read)


def _decode(read):
    """Decode bebcode, `read` should be a callable that returns number of bytes."""
    # TODO: Some input validation
    obj_type = read(1)
    if obj_type == b'':
        raise DecodeError('invalid input')
    if obj_type == b'e':
        return None
    if obj_type == b'i':
        number_bytes = b''
        while 1:
            c = read(1)
            if not c.isdigit() and c != b'-':
                if c != b'e':
                    raise DecodeError('illegal digit in size')
                break
            number_bytes += c
        number = int(number_bytes)
        return number
    elif obj_type == b'l':
        l = []
        while 1:
            i = _decode(read)
            if i is None:
                break
            l.append(i)
        return l
    elif obj_type == b'd':
        kv = []
        while 1:
            k = _decode(read)
            if k is None:
                break
            v = _decode(read)
            kv.append((k, v))
        return dict(kv)
    else:
        size_bytes = obj_type
        while 1:
            c = read(1)
            if c == b':':
                break
            size_bytes += c
        size = int(size_bytes)
        return read(size)
