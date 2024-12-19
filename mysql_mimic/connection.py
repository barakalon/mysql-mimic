import asyncio
import logging
from ssl import SSLContext
from typing import Optional, Dict, Any, Iterator, AsyncIterator

from mysql_mimic.auth import (
    AuthInfo,
    Forbidden,
    Success,
    AuthPlugin,
    AuthState,
    IdentityProvider,
)
from mysql_mimic.charset import CharacterSet
from mysql_mimic.constants import DEFAULT_SERVER_CAPABILITIES, KillKind
from mysql_mimic.control import Control
from mysql_mimic.errors import ErrorCode, MysqlError
from mysql_mimic.packets import (
    SSLRequest,
    parse_com_init_db,
    parse_com_field_list,
    make_column_definition_41,
)
from mysql_mimic.prepared import PreparedStatement, REGEX_PARAM
from mysql_mimic.results import ensure_result_set, ResultSet
from mysql_mimic import types, packets, context
from mysql_mimic.schema import com_field_list_to_show_statement
from mysql_mimic.session import BaseSession
from mysql_mimic.stream import MysqlStream, ConnectionClosed
from mysql_mimic.types import Capabilities
from mysql_mimic.utils import seq, aiterate, cooperative_iterate

logger = logging.getLogger(__name__)


class Connection:
    _MAX_PREPARED_STMT_ID = 2**32

    def __init__(
        self,
        stream: MysqlStream,
        session: BaseSession,
        control: Control,
        identity_provider: IdentityProvider,
        server_capabilities: Capabilities = DEFAULT_SERVER_CAPABILITIES,
        ssl: Optional[SSLContext] = None,
    ):
        self.stream = stream
        self.session = session
        self.control = control
        self.identity_provider = identity_provider
        self.ssl = ssl

        # Authentication plugins can reuse the initial handshake data.
        # This let's clients reuse the nonce when performing COM_CHANGE_USER, skipping a round trip.
        self.handshake_auth_data: Optional[bytes] = None
        self.handshake_auth_plugin: Optional[str] = None

        self.server_capabilities = server_capabilities
        if ssl:
            self.server_capabilities |= Capabilities.CLIENT_SSL

        self.capabilities = Capabilities(0)
        self.status_flags = types.ServerStatus(0)

        self.max_packet_size = 0
        self.client_plugin_name: Optional[str] = None
        self.client_connect_attrs: Dict[str, str] = {}
        self.zstd_compression_level = 0

        self.prepared_stmt_seq = seq(self._MAX_PREPARED_STMT_ID)
        self.prepared_stmts: Dict[int, PreparedStatement] = {}

        self.connection_id: int = 0
        self._kill: Optional[KillKind] = None
        self._task: Optional[asyncio.Task] = None

    @property
    def server_charset(self) -> CharacterSet:
        return CharacterSet[self.session.variables.get("character_set_results")]

    @property
    def client_charset(self) -> CharacterSet:
        return CharacterSet[self.session.variables.get("character_set_client")]

    async def start(self) -> None:
        self._task = asyncio.create_task(self._start())
        try:
            await self._task
        finally:
            self._task = None

    async def _start(self) -> None:
        context.connection_id.set(self.connection_id)
        logger.info("Started new connection: %s", self.connection_id)
        try:
            await self.connection_phase()
            await self.session.init(self)
        except Exception as e:
            await self.stream.write(self.error(msg=e, code=ErrorCode.HANDSHAKE_ERROR))
            raise

        try:
            await self.command_phase()
        except asyncio.CancelledError:
            if self._kill == KillKind.CONNECTION:
                logger.info("Connection %s killed", self.connection_id)
                await self.stream.write(
                    self.error(
                        msg="Session was killed", code=ErrorCode.SESSION_WAS_KILLED
                    )
                )
                self._kill = None
            else:
                raise
        finally:
            await self.session.close()

    def kill(self, kind: KillKind = KillKind.CONNECTION) -> None:
        if self._task:
            self._kill = kind
            self._task.cancel()

    async def connection_phase(self) -> None:
        default_auth_plugin = self.identity_provider.get_default_plugin()
        auth_data, auth_state = await default_auth_plugin.start()
        assert isinstance(auth_data, bytes)
        self.handshake_auth_data = auth_data
        self.handshake_auth_plugin = default_auth_plugin.name

        handshake_v10 = packets.make_handshake_v10(
            capabilities=self.server_capabilities,
            server_charset=self.server_charset,
            server_version=self.session.variables.get("version"),
            connection_id=self.connection_id,
            auth_data=auth_data,
            status_flags=self.status_flags,
            auth_plugin_name=default_auth_plugin.name,
        )
        await self.stream.write(handshake_v10)
        response = packets.parse_handshake_response(
            capabilities=self.server_capabilities,
            data=await self.stream.read(),
        )
        if isinstance(response, SSLRequest):
            assert self.ssl is not None
            await self.stream.start_tls(self.ssl)
            response = packets.parse_handshake_response_41(
                capabilities=self.server_capabilities,
                data=await self.stream.read(),
            )

        self.capabilities = response.capabilities
        self.max_packet_size = response.max_packet_size
        self.session.variables.set("character_set_client", response.client_charset.name)
        self.session.database = response.database
        self.client_plugin_name = response.client_plugin
        self.client_connect_attrs = response.connect_attrs
        self.zstd_compression_level = response.zstd_compression_level
        self.session.variables.set("external_user", response.username, force=True)

        await self.authenticate(
            auth_state=auth_state,
            server_plugin=default_auth_plugin,
            username=response.username,
            client_plugin_name=response.client_plugin,
            auth_response=response.auth_response,
            connect_attrs=response.connect_attrs,
        )
        self.stream.reset_seq()

    async def handle_change_user(self, data: bytes) -> None:
        com_change_user = packets.parse_com_change_user(
            capabilities=self.capabilities,
            client_charset=self.client_charset,
            data=data,
        )

        self.session.database = com_change_user.database
        self.session.variables.set(
            "external_user", com_change_user.username, force=True
        )
        if com_change_user.client_charset:
            self.session.variables.set(
                "character_set_client", com_change_user.client_charset.name
            )
        if com_change_user.connect_attrs:
            self.client_connect_attrs = com_change_user.connect_attrs

        await self.authenticate(
            username=com_change_user.username,
            auth_response=com_change_user.auth_response,
            client_plugin_name=com_change_user.client_plugin,
            connect_attrs=com_change_user.connect_attrs,
        )

        await self.session.reset()

    async def authenticate(
        self,
        username: str,
        auth_response: bytes,
        client_plugin_name: Optional[str],
        connect_attrs: Dict[str, str],
        auth_state: Optional[AuthState] = None,
        server_plugin: Optional[AuthPlugin] = None,
    ) -> None:
        user = await self.identity_provider.get_user(username)

        if not user:
            await self.stream.write(
                self.error(
                    msg=f"User {username} does not exist",
                    code=ErrorCode.USER_DOES_NOT_EXIST,
                )
            )
            return

        user_plugin = (
            self.identity_provider.get_plugin(user.auth_plugin or "")
            or self.identity_provider.get_default_plugin()
        )
        assert self.handshake_auth_plugin is not None
        auth_info = AuthInfo(
            username=username,
            data=auth_response,
            connect_attrs=connect_attrs,
            user=user,
            client_plugin_name=client_plugin_name,
            handshake_auth_data=self.handshake_auth_data,
            handshake_plugin_name=self.handshake_auth_plugin,
        )

        if (
            server_plugin
            and (
                server_plugin.client_plugin_name is None
                or server_plugin.client_plugin_name == client_plugin_name
            )
            and server_plugin.name == user_plugin.name
        ):
            # Optimistic match during handshake
            assert auth_state is not None
            decision = await auth_state.asend(auth_info)
        elif (
            user_plugin.client_plugin_name is None
            or user_plugin.client_plugin_name == client_plugin_name
        ):
            # Continue with provided client plugin
            decision, auth_state = await user_plugin.start(auth_info)
        else:
            # Mismatch - switch authentication method
            decision, auth_state = await user_plugin.start()
            if user_plugin.client_plugin_name and isinstance(decision, bytes):
                await self.stream.write(
                    packets.make_auth_switch_request(
                        server_charset=self.server_charset,
                        plugin_name=user_plugin.client_plugin_name,
                        plugin_provided_data=decision,
                    )
                )
                auth_response = await self.stream.read()
                auth_info = auth_info.copy(auth_response)
                decision = await auth_state.asend(auth_info)

        while not isinstance(decision, (Success, Forbidden)):
            await self.stream.write(packets.make_auth_more_data(decision))
            auth_response = await self.stream.read()
            auth_info = auth_info.copy(auth_response)
            decision = await auth_state.asend(auth_info)

        if isinstance(decision, Success):
            self.session.username = decision.authenticated_as
            await self.stream.write(self.ok())
        else:
            logger.info(
                "Access denied for user '%s' with plugin '%s'",
                auth_info.user.name,
                user_plugin.name,
            )
            await self.stream.write(
                self.error(
                    msg=decision.msg or f"Access denied for user {auth_info.user.name}",
                    code=ErrorCode.ACCESS_DENIED_ERROR,
                )
            )

    async def command_phase(self) -> None:
        """https://dev.mysql.com/doc/internals/en/command-phase.html"""
        while True:
            try:
                data = await self.stream.read()
            except ConnectionClosed:
                logger.info("Connection closed")
                return
            try:
                command = data[0]
                rest = data[1:]

                if command == types.Commands.COM_QUERY:
                    await self.handle_query(rest)
                elif command == types.Commands.COM_STMT_PREPARE:
                    await self.handle_stmt_prepare(rest)
                elif command == types.Commands.COM_STMT_SEND_LONG_DATA:
                    await self.handle_stmt_send_long_data(rest)
                elif command == types.Commands.COM_STMT_EXECUTE:
                    await self.handle_stmt_execute(rest)
                elif command == types.Commands.COM_STMT_FETCH:
                    await self.handle_stmt_fetch(rest)
                elif command == types.Commands.COM_STMT_RESET:
                    await self.handle_stmt_reset(rest)
                elif command == types.Commands.COM_STMT_CLOSE:
                    await self.handle_stmt_close(rest)
                elif command == types.Commands.COM_PING:
                    await self.handle_ping(rest)
                elif command == types.Commands.COM_CHANGE_USER:
                    await self.handle_change_user(rest)
                elif command == types.Commands.COM_RESET_CONNECTION:
                    await self.handle_reset_connection(rest)
                elif command == types.Commands.COM_DEBUG:
                    await self.handle_debug(rest)
                elif command == types.Commands.COM_QUIT:
                    return
                elif command == types.Commands.COM_INIT_DB:
                    await self.handle_init_db(rest)
                elif command == types.Commands.COM_FIELD_LIST:
                    await self.handle_field_list(rest)
                else:
                    raise MysqlError(
                        f"Unsupported Command: {hex(command)}",
                        ErrorCode.UNKNOWN_COM_ERROR,
                    )

            except MysqlError as e:
                logger.error(e)
                await self.stream.write(self.error(msg=e.msg, code=e.code))
            except asyncio.CancelledError:
                if self._kill == KillKind.QUERY:
                    logger.info("Query killed on connection %s", self.connection_id)
                    if self._task and hasattr(self._task, "uncancel"):  # python >=3.11
                        self._task.uncancel()
                    await self.stream.write(
                        self.error(
                            msg="Query was killed", code=ErrorCode.SESSION_WAS_KILLED
                        )
                    )
                    self._kill = None
                else:
                    raise
            except Exception as e:  # pylint: disable=broad-except
                logger.exception(e)
                await self.stream.write(self.error(msg=e))
            finally:
                self.stream.reset_seq()

    async def handle_ping(self, data: bytes) -> None:  # pylint: disable=unused-argument
        """
        https://dev.mysql.com/doc/internals/en/com-ping.html

        COM_PING check if the server is alive.
        """
        await self.stream.write(self.ok())

    async def handle_reset_connection(
        self, data: bytes
    ) -> None:  # pylint: disable=unused-argument
        """
        https://dev.mysql.com/doc/internals/en/com-reset-connection.html

        COM_RESET_CONNECTION Resets the session state.

        For now, we're just treating this like a no-op.
        """
        await self.stream.write(self.ok())

    async def handle_debug(
        self, data: bytes
    ) -> None:  # pylint: disable=unused-argument
        """
        https://dev.mysql.com/doc/internals/en/com-debug.html

        COM_DEBUG triggers a dump on internal debug info to stdout of the mysql-server.

        For now, we're just treating this like a no-op.
        """
        await self.stream.write(self.ok())

    async def handle_init_db(self, data: bytes) -> None:
        await self.session.use(parse_com_init_db(self.client_charset, data))
        await self.stream.write(self.ok())

    async def handle_field_list(self, data: bytes) -> None:
        com_field_list = parse_com_field_list(self.client_charset, data)
        sql = com_field_list_to_show_statement(com_field_list)
        result = await self.query(sql=sql, query_attrs={})
        columns = b"".join(
            [
                make_column_definition_41(
                    server_charset=self.server_charset,
                    table=com_field_list.table,
                    name=row[0],
                    is_com_field_list=True,
                    default=row[4],
                )
                async for row in aiterate(result.rows)
            ]
        )
        await self.stream.write(columns)
        await self.stream.write(self.ok_or_eof())

    async def handle_query(self, data: bytes) -> None:
        """
        https://dev.mysql.com/doc/internals/en/com-query.html

        COM_QUERY is used to send the server a text-based query that is executed immediately.
        """

        com_query = packets.parse_com_query(
            capabilities=self.capabilities,
            client_charset=self.client_charset,
            data=data,
        )

        result_set = await self.query(com_query.sql, com_query.query_attrs)

        if not result_set:
            await self.stream.write(self.ok())
            return

        async for packet in self.text_resultset(result_set):
            await self.stream.write(packet, drain=False)
        await self.stream.drain()

    async def handle_stmt_prepare(self, data: bytes) -> None:
        """
        https://dev.mysql.com/doc/internals/en/com-stmt-prepare.html

        COM_STMT_PREPARE creates a prepared statement from the passed query string.
        """
        sql = self.client_charset.decode(data)

        stmt_id = next(self.prepared_stmt_seq)
        num_params = len(REGEX_PARAM.findall(sql))

        stmt = PreparedStatement(
            stmt_id=stmt_id,
            sql=sql,
            num_params=num_params,
        )
        self.prepared_stmts[stmt_id] = stmt

        for packet in self.com_stmt_prepare_response(stmt):
            await self.stream.write(packet, drain=False)
        await self.stream.drain()

    async def handle_stmt_send_long_data(self, data: bytes) -> None:
        """
        https://dev.mysql.com/doc/internals/en/com-stmt-send-long-data.html

        COM_STMT_SEND_LONG_DATA sends the data for a column.
        """
        com_stmt_send_long_data = packets.parse_com_stmt_send_long_data(data)
        stmt = self.get_stmt(com_stmt_send_long_data.stmt_id)
        if stmt.param_buffers is None:
            stmt.param_buffers = {}
        buffer = stmt.param_buffers.setdefault(
            com_stmt_send_long_data.param_id, bytearray()
        )
        buffer.extend(com_stmt_send_long_data.data)

    async def handle_stmt_execute(self, data: bytes) -> None:
        """
        https://dev.mysql.com/doc/internals/en/com-stmt-execute.html

        COM_STMT_EXECUTE asks the server to execute a prepared statement as identified by stmt-id.
        """
        com_stmt_execute = packets.parse_com_stmt_execute(
            capabilities=self.capabilities,
            client_charset=self.client_charset,
            data=data,
            get_stmt=self.get_stmt,
        )

        com_stmt_execute.stmt.param_buffers = None

        result_set = await self.query(
            com_stmt_execute.sql, com_stmt_execute.query_attrs
        )

        if not result_set:
            await self.stream.write(self.ok())
            return

        await self.stream.write(types.uint_len(len(result_set.columns)))

        for column in result_set.columns:
            await self.stream.write(
                packets.make_column_definition_41(
                    server_charset=self.server_charset,
                    name=column.name,
                    column_type=column.type,
                    character_set=column.character_set,
                )
            )

        async def gen_rows() -> AsyncIterator[bytes]:
            async for r in cooperative_iterate(aiterate(result_set.rows)):
                yield packets.make_binary_resultrow(r, result_set.columns)

        rows = gen_rows()

        if com_stmt_execute.use_cursor:
            com_stmt_execute.stmt.cursor = rows
            await self.stream.write(
                self.ok_or_eof(flags=types.ServerStatus.SERVER_STATUS_CURSOR_EXISTS)
            )
        else:
            if not self.deprecate_eof():
                await self.stream.write(self.eof())
            async for row in rows:
                await self.stream.write(row)
            await self.stream.write(self.ok_or_eof())

    async def handle_stmt_fetch(self, data: bytes) -> None:
        """
        https://dev.mysql.com/doc/internals/en/com-stmt-fetch.html

        COM_STMT_FETCH fetches rows from an existing resultset after a COM_STMT_EXECUTE.
        """
        com_stmt_fetch = packets.parse_handle_stmt_fetch(data)

        stmt = self.get_stmt(com_stmt_fetch.stmt_id)
        assert stmt.cursor is not None
        count = 0

        async for packet in cooperative_iterate(stmt.cursor):
            if count >= com_stmt_fetch.num_rows:
                break
            await self.stream.write(packet, drain=False)
            count += 1
        await self.stream.drain()

        done = count < com_stmt_fetch.num_rows

        await self.stream.write(
            self.ok_or_eof(
                flags=(
                    types.ServerStatus.SERVER_STATUS_LAST_ROW_SENT
                    if done
                    else types.ServerStatus.SERVER_STATUS_CURSOR_EXISTS
                )
            )
        )

    async def handle_stmt_reset(self, data: bytes) -> None:
        """
        https://dev.mysql.com/doc/internals/en/com-stmt-reset.html

        COM_STMT_RESET resets the data of a prepared statement which was accumulated with COM_STMT_SEND_LONG_DATA
        commands and closes the cursor if it was opened with COM_STMT_EXECUTE.
        """
        com_stmt_reset = packets.parse_com_stmt_reset(data)
        stmt = self.get_stmt(com_stmt_reset.stmt_id)
        stmt.param_buffers = None
        stmt.cursor = None
        await self.session.reset()
        await self.stream.write(self.ok())

    async def handle_stmt_close(self, data: bytes) -> None:
        """
        https://dev.mysql.com/doc/internals/en/com-stmt-close.html

        COM_STMT_CLOSE deallocates a prepared statement.
        """
        com_stmt_close = packets.parse_com_stmt_close(data)
        self.prepared_stmts.pop(com_stmt_close.stmt_id, None)

    def get_stmt(self, stmt_id: int) -> PreparedStatement:
        if stmt_id in self.prepared_stmts:
            return self.prepared_stmts[stmt_id]
        raise MysqlError(f"Unknown statement: {stmt_id}", ErrorCode.UNKNOWN_PROCEDURE)

    async def query(self, sql: str, query_attrs: Dict[str, str]) -> ResultSet:
        logger.debug("Received query: %s", sql)

        result_set = await ensure_result_set(
            await self.session.handle_query(sql, query_attrs)
        )
        return result_set

    def ok(self, **kwargs: Any) -> bytes:
        return packets.make_ok(
            capabilities=self.capabilities,
            status_flags=self.status_flags,
            **kwargs,
        )

    def eof(self, **kwargs: Any) -> bytes:
        return packets.make_eof(
            capabilities=self.capabilities,
            status_flags=self.status_flags,
            **kwargs,
        )

    def ok_or_eof(
        self,
        affected_rows: int = 0,
        last_insert_id: int = 0,
        warnings: int = 0,
        flags: int = 0,
    ) -> bytes:
        if self.deprecate_eof():
            return self.ok(
                eof=True,
                affected_rows=affected_rows,
                last_insert_id=last_insert_id,
                warnings=warnings,
                flags=flags,
            )
        return self.eof(warnings=warnings, flags=flags)

    def error(self, **kwargs: Any) -> bytes:
        return packets.make_error(
            capabilities=self.capabilities, server_charset=self.server_charset, **kwargs
        )

    def deprecate_eof(self) -> bool:
        return Capabilities.CLIENT_DEPRECATE_EOF in self.capabilities

    async def text_resultset(self, result_set: ResultSet) -> AsyncIterator[bytes]:
        yield packets.make_column_count(
            capabilities=self.capabilities, column_count=len(result_set.columns)
        )

        for column in result_set.columns:
            yield packets.make_column_definition_41(
                server_charset=self.server_charset,
                name=column.name,
                column_type=column.type,
                character_set=column.character_set,
            )

        if not self.deprecate_eof():
            yield self.eof()

        affected_rows = 0

        async for row in cooperative_iterate(aiterate(result_set.rows)):
            affected_rows += 1
            yield packets.make_text_resultset_row(row, result_set.columns)

        yield self.ok_or_eof(affected_rows=affected_rows)

    def com_stmt_prepare_response(
        self, statement: PreparedStatement
    ) -> Iterator[bytes]:
        yield packets.make_com_stmt_prepare_ok(statement)
        if statement.num_params:
            for _ in range(statement.num_params):
                yield packets.make_column_definition_41(
                    server_charset=self.server_charset, name="?"
                )
            yield self.eof()
