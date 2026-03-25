import asyncio
import struct
from typing import Any, List, Sequence, Tuple
from ssl import SSLContext

from mysql_mimic.errors import MysqlError, ErrorCode
from mysql_mimic.results import ResultColumn
from mysql_mimic.types import ColumnType, uint_len
from mysql_mimic.utils import seq

_header_struct = struct.Struct("<I")
_pack_header = _header_struct.pack_into


class ConnectionClosed(Exception):
    pass


class MysqlStream:
    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        buffer_size: int = 2**15,
    ):
        self.reader = reader
        self.writer = writer
        self.seq = seq(256)
        self._buffer = bytearray()
        self._buffer_size = buffer_size
        self._header = bytearray(4)

    async def read(self) -> bytes:
        data = b""
        while True:
            header = await self.reader.read(4)

            if not header:
                raise ConnectionClosed()

            i = struct.unpack("<I", header)[0]
            payload_length = i & 0x00FFFFFF
            sequence_id = (i & 0xFF000000) >> 24

            expected = next(self.seq)
            if sequence_id != expected:
                raise MysqlError(
                    f"Expected seq({expected}) got seq({sequence_id})",
                    ErrorCode.MALFORMED_PACKET,
                )

            if payload_length == 0:
                return data

            data += await self.reader.readexactly(payload_length)

            if payload_length < 0xFFFFFF:
                return data

    async def write(self, data: bytes, drain: bool = True) -> None:
        if len(data) < 0xFFFFFF:
            _pack_header(self._header, 0, len(data) | (next(self.seq) << 24))
            self._buffer.extend(self._header)
            self._buffer.extend(data)
            if drain or len(self._buffer) >= self._buffer_size:
                await self.drain()
            return

        while True:
            # Grab first 0xFFFFFF bytes to send
            payload = data[:0xFFFFFF]
            data = data[0xFFFFFF:]

            _pack_header(self._header, 0, len(payload) | (next(self.seq) << 24))
            self._buffer.extend(self._header)
            self._buffer.extend(payload)
            if drain or len(self._buffer) >= self._buffer_size:
                await self.drain()

            if len(payload) != 0xFFFFFF:
                return

    def write_many(self, packets: Sequence[bytes]) -> None:
        """Frame and buffer multiple packets without awaiting."""
        header = self._header
        buf = self._buffer
        for data in packets:
            _pack_header(header, 0, len(data) | (next(self.seq) << 24))
            buf.extend(header)
            buf.extend(data)

    def write_text_rows(
        self, rows: List[Sequence[Any]], columns: List[ResultColumn]
    ) -> int:
        """Serialize and frame text result rows directly into the buffer.

        Returns the number of rows written.
        """
        buf = self._buffer
        num_cols = len(columns)
        count = 0
        seq_val = self.seq.value
        seq_size = self.seq.size or 0

        for row in rows:
            # Reserve 4 bytes for the packet header
            header_pos = len(buf)
            buf.extend(b"\x00\x00\x00\x00")

            # Serialize row directly into buf
            for i in range(num_cols):
                value = row[i]
                if value is None:
                    buf.append(0xFB)
                    continue

                col = columns[i]
                if col.use_default_text_encoder:
                    if isinstance(value, str):
                        encoded = value.encode(col.codec)
                    elif isinstance(value, bytes):
                        encoded = value
                    else:
                        encoded = str(value).encode(col.codec)
                elif col.type == ColumnType.TINY:
                    encoded = str(int(value)).encode(col.codec)
                else:
                    encoded = col.text_encoder(col, value)

                n = len(encoded)
                if n < 251:
                    buf.append(n)
                else:
                    buf.extend(uint_len(n))
                buf.extend(encoded)

            # Fill in the packet header now that we know the size
            payload_len = len(buf) - header_pos - 4
            _pack_header(buf, header_pos, payload_len | (seq_val << 24))
            seq_val += 1
            if seq_size:
                seq_val = seq_val % seq_size
            count += 1

        # Sync the sequence counter back
        self.seq.value = seq_val
        return count

    async def drain(self) -> None:
        if self._buffer:
            self.writer.write(self._buffer)
            self._buffer.clear()
        await self.writer.drain()

    def reset_seq(self) -> None:
        self.seq.reset()

    async def start_tls(self, ssl: SSLContext) -> None:
        transport = self.writer.transport
        protocol = transport.get_protocol()
        loop = asyncio.get_event_loop()
        new_transport = await loop.start_tls(
            transport=transport,
            protocol=protocol,
            sslcontext=ssl,
            server_side=True,
        )

        # This seems to be the easiest way to wrap the socket created by asyncio
        self.writer._transport = new_transport  # type: ignore # pylint: disable=protected-access
        self.reader._transport = new_transport  # type: ignore # pylint: disable=protected-access
