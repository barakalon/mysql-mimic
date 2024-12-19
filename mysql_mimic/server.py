from __future__ import annotations

import asyncio
import inspect
import logging
from ssl import SSLContext
from socket import socket
from typing import Callable, Any, Optional, Sequence, Awaitable

from mysql_mimic import packets
from mysql_mimic.auth import IdentityProvider, SimpleIdentityProvider
from mysql_mimic.connection import Connection
from mysql_mimic.control import Control, LocalControl, TooManyConnections
from mysql_mimic.errors import ErrorCode
from mysql_mimic.session import Session, BaseSession
from mysql_mimic.constants import DEFAULT_SERVER_CAPABILITIES
from mysql_mimic.stream import MysqlStream
from mysql_mimic.types import Capabilities


logger = logging.getLogger(__name__)


class MaxConnectionsExceeded(Exception):
    pass


class MysqlServer:
    """
    MySQL mimic server.

    Args:
        session_factory: Callable that takes no arguments and returns a session
        capabilities: server capability flags
        control: Control instance to use. Defaults to a LocalControl instance.
        identity_provider: Authentication plugins to register. Defaults to `SimpleIdentityProvider`,
            which just blindly accepts whatever `username` is given by the client.
        ssl: SSLContext instance if this server should enable TLS over connections

        **kwargs: extra keyword args passed to the asyncio start server command
    """

    def __init__(
        self,
        session_factory: Callable[[], BaseSession | Awaitable[BaseSession]] = Session,
        capabilities: Capabilities = DEFAULT_SERVER_CAPABILITIES,
        control: Control | None = None,
        identity_provider: IdentityProvider | None = None,
        ssl: SSLContext | None = None,
        **serve_kwargs: Any,
    ):
        self.session_factory = session_factory
        self.capabilities = capabilities
        self.identity_provider = identity_provider or SimpleIdentityProvider()
        self.ssl = ssl

        self.control = control or LocalControl()
        self._serve_kwargs = serve_kwargs
        self._server: Optional[asyncio.base_events.Server] = None

    async def _client_connected_cb(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        stream = MysqlStream(reader, writer)

        try:
            if inspect.iscoroutinefunction(self.session_factory):
                session = await self.session_factory()
            else:
                session = self.session_factory()

            connection = Connection(
                stream=stream,
                session=session,
                control=self.control,
                server_capabilities=self.capabilities,
                identity_provider=self.identity_provider,
                ssl=self.ssl,
            )

        except Exception:  # pylint: disable=broad-except
            logger.exception("Failed to create connection")
            await stream.write(
                # Return an error so clients don't freeze
                packets.make_error(capabilities=self.capabilities)
            )
            return

        try:
            connection_id = await self.control.add(connection)
            connection.connection_id = connection_id
        except TooManyConnections:
            await stream.write(
                connection.error(
                    msg="Too many connections",
                    code=ErrorCode.CON_COUNT_ERROR,
                )
            )
            return
        except Exception:  # pylint: disable=broad-except
            logger.exception("Failed to register connection")
            await stream.write(connection.error(msg="Failed to register connection"))
            return

        try:
            return await connection.start()
        finally:
            writer.close()
            await self.control.remove(connection_id)

    async def start_server(self, **kwargs: Any) -> None:
        """
        Start an asyncio socket server.

        Args:
            **kwargs: keyword args passed to `asyncio.start_server`
        """
        kw = {}
        kw.update(self._serve_kwargs)
        kw.update(kwargs)
        if "port" not in kw:
            kw["port"] = 3306
        self._server = await asyncio.start_server(self._client_connected_cb, **kw)

    async def start_unix_server(self, **kwargs: Any) -> None:
        """
        Start an asyncio unix socket server.

        Args:
            **kwargs: keyword args passed to `asyncio.start_unix_server`
        """
        kw = {}
        kw.update(self._serve_kwargs)
        kw.update(kwargs)
        self._server = await asyncio.start_unix_server(self._client_connected_cb, **kw)

    async def serve_forever(self, **kwargs: Any) -> None:
        """
        Start accepting connections until the coroutine is cancelled.

        If a server isn't running, this starts a server with `start_server`.

        Args:
            **kwargs: keyword args passed to `start_server`
        """
        if not self._server:
            await self.start_server(**kwargs)
        assert self._server is not None
        await self._server.serve_forever()

    def close(self) -> None:
        """
        Stop serving.

        The server is closed asynchronously -
        use the `wait_closed` coroutine to wait until the server is closed.
        """
        if self._server:
            self._server.close()

    async def wait_closed(self) -> None:
        """Wait until the `close` method completes."""
        if self._server:
            await self._server.wait_closed()

    def sockets(self) -> Sequence[socket]:
        """Get sockets the server is listening on."""
        if self._server:
            return self._server.sockets
        return ()
