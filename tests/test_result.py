import io
from typing import Any

import pytest

from mysql_mimic import ColumnType
from mysql_mimic.charset import CharacterSet
from mysql_mimic.errors import MysqlError
from mysql_mimic.packets import _read_params, make_binary_resultrow
from mysql_mimic.results import NullBitmap, ResultColumn, ensure_result_set
from mysql_mimic.types import Capabilities, str_len, uint_1


async def gen_rows() -> Any:
    yield 1, None, None
    yield None, "2", None
    yield None, None, None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "result, column_types",
    [
        (
            (gen_rows(), ["a", "b", "c"]),
            [ColumnType.LONGLONG, ColumnType.STRING, ColumnType.NULL],
        ),
    ],
)
async def test_ensure_result_set_columns(result: Any, column_types: Any) -> None:
    result_set = await ensure_result_set(result)
    assert [c.type for c in result_set.columns] == column_types


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "result",
    [
        [1, 2],
        ([[1, 2]], ["a", "b"], ["a", "b"]),
    ],
)
async def test_ensure_result_set__invalid(result: Any) -> None:
    with pytest.raises(MysqlError):
        await ensure_result_set(result)


@pytest.mark.parametrize(
    "num_bits, offset, flipped, not_flipped, expected",
    [
        (9, 0, [0, 7, 8], [1, 6], b"\x81\x01"),
        (8, 2, [0, 5, 6, 7], [1, 4], b"\x84\x03"),
    ],
)
def test_null_bitmap_handles_byte_boundaries(
    num_bits: int,
    offset: int,
    flipped: Any,
    not_flipped: Any,
    expected: bytes,
) -> None:
    bitmap = NullBitmap.new(num_bits, offset=offset)

    for bit in flipped:
        bitmap.flip(bit)

    assert bytes(bitmap) == expected

    for bit in flipped:
        assert bitmap.is_flipped(bit) is True

    for bit in not_flipped:
        assert bitmap.is_flipped(bit) is False


def test_null_bitmap_from_buffer_respects_offset_and_boundaries() -> None:
    bitmap = NullBitmap.from_buffer(io.BytesIO(b"\x84\x03"), 8, offset=2)

    assert bytes(bitmap) == b"\x84\x03"
    assert bitmap.is_flipped(0) is True
    assert bitmap.is_flipped(5) is True
    assert bitmap.is_flipped(6) is True
    assert bitmap.is_flipped(7) is True
    assert bitmap.is_flipped(1) is False
    assert bitmap.is_flipped(4) is False


def test_make_binary_resultrow_keeps_null_bitmap_encoding() -> None:
    row = (None, "a", "b", "c", "d", None, None)
    columns = [
        ResultColumn(name="a", type=ColumnType.STRING),
        ResultColumn(name="b", type=ColumnType.STRING),
        ResultColumn(name="c", type=ColumnType.STRING),
        ResultColumn(name="d", type=ColumnType.STRING),
        ResultColumn(name="e", type=ColumnType.STRING),
        ResultColumn(name="f", type=ColumnType.STRING),
        ResultColumn(name="g", type=ColumnType.STRING),
    ]

    assert make_binary_resultrow(row, columns) == b"\x00\x84\x01\x01a\x01b\x01c\x01d"


def test_read_params_keeps_null_bitmap_parsing() -> None:
    payload = b"".join(
        [
            b"\x21\x01",
            uint_1(1),
            uint_1(ColumnType.STRING),
            uint_1(0),
            uint_1(ColumnType.STRING),
            uint_1(0),
            uint_1(ColumnType.STRING),
            uint_1(0),
            uint_1(ColumnType.STRING),
            uint_1(0),
            uint_1(ColumnType.STRING),
            uint_1(0),
            uint_1(ColumnType.STRING),
            uint_1(0),
            uint_1(ColumnType.STRING),
            uint_1(0),
            uint_1(ColumnType.STRING),
            uint_1(0),
            uint_1(ColumnType.STRING),
            uint_1(0),
            str_len(b"hi"),
            str_len(b"there"),
            str_len(b"friend"),
            str_len(b"from"),
            str_len(b"the"),
            str_len(b"bitmap"),
        ]
    )

    params = _read_params(
        Capabilities(0),
        CharacterSet.utf8mb4,
        io.BytesIO(payload),
        9,
    )

    assert params == [
        ("", None),
        ("", "hi"),
        ("", "there"),
        ("", "friend"),
        ("", "from"),
        ("", None),
        ("", "the"),
        ("", "bitmap"),
        ("", None),
    ]
