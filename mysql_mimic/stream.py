import asyncio
import struct
from typing import Sequence
from ssl import SSLContext

from mysql_mimic.errors import MysqlError, ErrorCode
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
