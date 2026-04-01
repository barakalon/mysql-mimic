from mysql_mimic.charset import CharacterSet


def test_decode_bytes():
    cs = CharacterSet.utf8mb4
    assert cs.decode(b"hello") == "hello"


def test_decode_bytearray():
    """Regression test for https://github.com/barakalon/mysql-mimic/issues/72

    CharacterSet.decode() must accept bytearray, not just bytes,
    because _read_params() in packets.py passes bytearray buffers.
    This caused mypyc builds to fail with an arg-type error.
    """
    cs = CharacterSet.utf8mb4
    assert cs.decode(bytearray(b"hello")) == "hello"
