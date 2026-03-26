from __future__ import annotations
import io
import struct

from enum import IntEnum, IntFlag, auto


class ColumnType(IntEnum):
    DECIMAL = 0x00
    TINY = 0x01
    SHORT = 0x02
    LONG = 0x03
    FLOAT = 0x04
    DOUBLE = 0x05
    NULL = 0x06
    TIMESTAMP = 0x07
    LONGLONG = 0x08
    INT24 = 0x09
    DATE = 0x0A
    TIME = 0x0B
    DATETIME = 0x0C
    YEAR = 0x0D
    NEWDATE = 0x0E
    VARCHAR = 0x0F
    BIT = 0x10
    TIMESTAMP2 = 0x11
    DATETIME2 = 0x12
    TIME2 = 0x13
    TYPED_ARRAY = 0x14
    INVALID = 0xF3
    BOOL = 0xF4
    JSON = 0xF5
    NEWDECIMAL = 0xF6
    ENUM = 0xF7
    SET = 0xF8
    TINY_BLOB = 0xF9
    MEDIUM_BLOB = 0xFA
    LONG_BLOB = 0xFB
    BLOB = 0xFC
    VAR_STRING = 0xFD
    STRING = 0xFE
    GEOMETRY = 0xFF


class Commands(IntEnum):
    COM_SLEEP = 0x00
    COM_QUIT = 0x01
    COM_INIT_DB = 0x02
    COM_QUERY = 0x03
    COM_FIELD_LIST = 0x04
    COM_CREATE_DB = 0x05
    COM_DROP_DB = 0x06
    COM_REFRESH = 0x07
    COM_SHUTDOWN = 0x08
    COM_STATISTICS = 0x09
    COM_PROCESS_INFO = 0x0A
    COM_CONNECT = 0x0B
    COM_PROCESS_KILL = 0x0C
    COM_DEBUG = 0x0D
    COM_PING = 0x0E
    COM_TIME = 0x0F
    COM_DELAYED_INSERT = 0x10
    COM_CHANGE_USER = 0x11
    COM_BINLOG_DUMP = 0x12
    COM_TABLE_DUMP = 0x13
    COM_CONNECT_OUT = 0x14
    COM_REGISTER_SLAVE = 0x15
    COM_STMT_PREPARE = 0x16
    COM_STMT_EXECUTE = 0x17
    COM_STMT_SEND_LONG_DATA = 0x18
    COM_STMT_CLOSE = 0x19
    COM_STMT_RESET = 0x1A
    COM_SET_OPTION = 0x1B
    COM_STMT_FETCH = 0x1C
    COM_DAEMON = 0x1D
    COM_BINLOG_DUMP_GTID = 0x1E
    COM_RESET_CONNECTION = 0x1F


class ColumnDefinition(IntFlag):
    NOT_NULL_FLAG = auto()
    PRI_KEY_FLAG = auto()
    UNIQUE_KEY_FLAG = auto()
    MULTIPLE_KEY_FLAG = auto()
    BLOB_FLAG = auto()
    UNSIGNED_FLAG = auto()
    ZEROFILL_FLAG = auto()
    BINARY_FLAG = auto()
    ENUM_FLAG = auto()
    AUTO_INCREMENT_FLAG = auto()
    TIMESTAMP_FLAG = auto()
    SET_FLAG = auto()
    NO_DEFAULT_VALUE_FLAG = auto()
    ON_UPDATE_NOW_FLAG = auto()
    NUM_FLAG = auto()
    PART_KEY_FLAG = auto()
    GROUP_FLAG = auto()
    UNIQUE_FLAG = auto()
    BINCMP_FLAG = auto()
    GET_FIXED_FIELDS_FLAG = auto()
    FIELD_IN_PART_FUNC_FLAG = auto()
    FIELD_IN_ADD_INDEX = auto()
    FIELD_IS_RENAMED = auto()
    FIELD_FLAGS_STORAGE_MEDIA = auto()
    FIELD_FLAGS_STORAGE_MEDIA_MASK = auto()
    FIELD_FLAGS_COLUMN_FORMAT = auto()
    FIELD_FLAGS_COLUMN_FORMAT_MASK = auto()
    FIELD_IS_DROPPED = auto()
    EXPLICIT_NULL_FLAG = auto()
    NOT_SECONDARY_FLAG = auto()
    FIELD_IS_INVISIBLE = auto()


class Capabilities(IntFlag):
    CLIENT_LONG_PASSWORD = auto()
    CLIENT_FOUND_ROWS = auto()
    CLIENT_LONG_FLAG = auto()
    CLIENT_CONNECT_WITH_DB = auto()
    CLIENT_NO_SCHEMA = auto()
    CLIENT_COMPRESS = auto()
    CLIENT_ODBC = auto()
    CLIENT_LOCAL_FILES = auto()
    CLIENT_IGNORE_SPACE = auto()
    CLIENT_PROTOCOL_41 = auto()
    CLIENT_INTERACTIVE = auto()
    CLIENT_SSL = auto()
    CLIENT_IGNORE_SIGPIPE = auto()
    CLIENT_TRANSACTIONS = auto()
    CLIENT_RESERVED = auto()
    CLIENT_SECURE_CONNECTION = auto()
    CLIENT_MULTI_STATEMENTS = auto()
    CLIENT_MULTI_RESULTS = auto()
    CLIENT_PS_MULTI_RESULTS = auto()
    CLIENT_PLUGIN_AUTH = auto()
    CLIENT_CONNECT_ATTRS = auto()
    CLIENT_PLUGIN_AUTH_LENENC_CLIENT_DATA = auto()
    CLIENT_CAN_HANDLE_EXPIRED_PASSWORDS = auto()
    CLIENT_SESSION_TRACK = auto()
    CLIENT_DEPRECATE_EOF = auto()
    CLIENT_OPTIONAL_RESULTSET_METADATA = auto()
    CLIENT_ZSTD_COMPRESSION_ALGORITHM = auto()
    CLIENT_QUERY_ATTRIBUTES = auto()
    MULTI_FACTOR_AUTHENTICATION = auto()
    CLIENT_CAPABILITY_EXTENSION = auto()
    CLIENT_SSL_VERIFY_SERVER_CERT = auto()
    CLIENT_REMEMBER_OPTIONS = auto()


class ServerStatus(IntFlag):
    SERVER_STATUS_IN_TRANS = 0x0001
    SERVER_STATUS_AUTOCOMMIT = 0x0002
    SERVER_MORE_RESULTS_EXISTS = 0x0008
    SERVER_STATUS_NO_GOOD_INDEX_USED = 0x0010
    SERVER_STATUS_NO_INDEX_USED = 0x0020
    SERVER_STATUS_CURSOR_EXISTS = 0x0040
    SERVER_STATUS_LAST_ROW_SENT = 0x0080
    SERVER_STATUS_DB_DROPPED = 0x0100
    SERVER_STATUS_NO_BACKSLASH_ESCAPES = 0x0200
    SERVER_STATUS_METADATA_CHANGED = 0x0400
    SERVER_QUERY_WAS_SLOW = 0x0800
    SERVER_PS_OUT_PARAMS = 0x1000
    SERVER_STATUS_IN_TRANS_READONLY = 0x2000
    SERVER_SESSION_STATE_CHANGED = 0x4000


class ResultsetMetadata(IntEnum):
    RESULTSET_METADATA_NONE = 0
    RESULTSET_METADATA_FULL = 1


class ComStmtExecuteFlags(IntFlag):
    CURSOR_TYPE_NO_CURSOR = 0x00
    CURSOR_TYPE_READ_ONLY = 0x01
    CURSOR_TYPE_FOR_UPDATE = 0x02
    CURSOR_TYPE_SCROLLABLE = 0x04
    PARAMETER_COUNT_AVAILABLE = 0x08


def uint_len(i: int) -> bytes:
    if i < 251:
        return struct.pack("<B", i)
    if i < 2**16:
        return struct.pack("<BH", 0xFC, i)
    if i < 2**24:
        return struct.pack("<BL", 0xFD, i)[:-1]

    return struct.pack("<BQ", 0xFE, i)


def uint_1(i: int) -> bytes:
    return struct.pack("<B", i)


def uint_2(i: int) -> bytes:
    return struct.pack("<H", i)


def uint_3(i: int) -> bytes:
    return struct.pack("<HB", i & 0xFFFF, i >> 16)


def uint_4(i: int) -> bytes:
    return struct.pack("<I", i)


def uint_6(i: int) -> bytes:
    return struct.pack("<IH", i & 0xFFFFFFFF, i >> 32)


def uint_8(i: int) -> bytes:
    return struct.pack("<Q", i)


def str_fixed(l: int, s: bytes) -> bytes:
    return struct.pack(f"<{l}s", s)


def str_null(s: bytes) -> bytes:
    l = len(s)
    return struct.pack(f"<{l}sB", s, 0)


def str_len(s: bytes) -> bytes:
    return uint_len(len(s)) + s


def str_rest(s: bytes) -> bytes:
    return s


def read_int_1(reader: io.BytesIO) -> int:
    data = reader.read(1)
    return struct.unpack("<b", data)[0]


def read_uint_1(reader: io.BytesIO) -> int:
    data = reader.read(1)
    return struct.unpack("<B", data)[0]


def read_int_2(reader: io.BytesIO) -> int:
    data = reader.read(2)
    return struct.unpack("<h", data)[0]


def read_uint_2(reader: io.BytesIO) -> int:
    data = reader.read(2)
    return struct.unpack("<H", data)[0]


def read_uint_3(reader: io.BytesIO) -> int:
    data = reader.read(3)
    t = struct.unpack("<HB", data)
    return t[0] + (t[1] << 16)


def read_int_4(reader: io.BytesIO) -> int:
    data = reader.read(4)
    return struct.unpack("<i", data)[0]


def read_uint_4(reader: io.BytesIO) -> int:
    data = reader.read(4)
    return struct.unpack("<I", data)[0]


def read_uint_6(reader: io.BytesIO) -> int:
    data = reader.read(6)
    t = struct.unpack("<IH", data)
    return t[0] + (t[1] << 32)


def read_int_8(reader: io.BytesIO) -> int:
    data = reader.read(8)
    return struct.unpack("<q", data)[0]


def read_uint_8(reader: io.BytesIO) -> int:
    data = reader.read(8)
    return struct.unpack("<Q", data)[0]


def read_float(reader: io.BytesIO) -> float:
    data = reader.read(4)
    return struct.unpack("<f", data)[0]


def read_double(reader: io.BytesIO) -> float:
    data = reader.read(8)
    return struct.unpack("<d", data)[0]


def read_uint_len(reader: io.BytesIO) -> int:
    i = read_uint_1(reader)

    if i == 0xFE:
        return read_uint_8(reader)

    if i == 0xFD:
        return read_uint_3(reader)

    if i == 0xFC:
        return read_uint_2(reader)

    return i


def read_str_fixed(reader: io.BytesIO, l: int) -> bytes:
    return reader.read(l)


def read_str_null(reader: io.BytesIO) -> bytes:
    data = b""
    while True:
        b = reader.read(1)
        if b == b"\x00":
            return data
        data += b


def read_str_len(reader: io.BytesIO) -> bytes:
    l = read_uint_len(reader)
    return read_str_fixed(reader, l)


def read_str_rest(reader: io.BytesIO) -> bytes:
    return reader.read()


def peek(reader: io.BytesIO, num_bytes: int = 1) -> bytes:
    pos = reader.tell()
    val = reader.read(num_bytes)
    reader.seek(pos)
    return val
