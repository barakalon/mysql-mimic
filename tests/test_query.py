import asyncio
import io
from contextlib import closing
from datetime import date, datetime, timedelta
from typing import Any, Callable, Awaitable, Sequence, Dict, List, Tuple, Type

import pytest
import pytest_asyncio
from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.cursor import MySQLCursorDict, MySQLCursor
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
import aiomysql
from freezegun import freeze_time

from mysql_mimic import ResultColumn, ResultSet, MysqlServer, context
from mysql_mimic.charset import CharacterSet
from mysql_mimic.results import AllowedResult
from mysql_mimic.constants import INFO_SCHEMA
from mysql_mimic.types import ColumnType
from tests.conftest import PreparedDictCursor, query, MockSession, ConnectFixture
from tests.fixtures import queries

QueryFixture = Callable[[str], Awaitable[Sequence[Dict[str, Any]]]]


@pytest_asyncio.fixture(
    params=["mysql.connector", "mysql.connector(prepared)", "aiomysql", "sqlalchemy"]
)
async def query_fixture(
    mysql_connector_conn: MySQLConnectionAbstract,
    aiomysql_conn: aiomysql.Connection,
    sqlalchemy_engine: AsyncEngine,
    request: Any,
) -> QueryFixture:
    if request.param == "mysql.connector":

        async def q1(sql: str) -> Sequence[Dict[str, Any]]:
            return await query(mysql_connector_conn, sql)

        return q1

    if request.param == "mysql.connector(prepared)":

        async def q2(sql: str) -> Sequence[Dict[str, Any]]:
            return await query(
                mysql_connector_conn, sql, cursor_class=PreparedDictCursor
            )

        return q2

    if request.param == "aiomysql":

        async def q3(sql: str) -> Sequence[Dict[str, Any]]:
            async with aiomysql_conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql)
                return await cur.fetchall()

        return q3

    if request.param == "sqlalchemy":

        async def q4(sql: str) -> Sequence[Dict[str, Any]]:
            async with sqlalchemy_engine.connect() as conn:
                cursor = await conn.execute(text(sql))
                if cursor.returns_rows:
                    return cursor.mappings().all()  # type: ignore
                return []

        return q4

    raise RuntimeError("Unexpected fixture param")


# Uncomment to make tests only use mysql-connector, which can help during debugging
# @pytest_asyncio.fixture
# async def query_fixture(
#     mysql_connector_conn: MySQLConnectionAbstract,
# ) -> QueryFixture:
#     async def q1(sql: str) -> Sequence[Dict[str, Any]]:
#         return await query(mysql_connector_conn, sql)
#
#     return q1


EXPLICIT_TYPE_TESTS = [
    (
        ResultSet(
            rows=[(input_,)],
            columns=[
                ResultColumn(
                    name="b",
                    character_set=CharacterSet.utf8mb4,
                    type=type_,
                )
            ],
        ),
        [{"b": output}],
    )
    for input_, type_, output in [
        ("♥".encode("utf-8"), ColumnType.VARCHAR, "♥"),
        ("♥".encode("utf-8"), ColumnType.BLOB, "♥"),
        (b"\xe2\x99\xa5", ColumnType.BLOB, "♥"),
        (1, ColumnType.TINY, True),
        (2, ColumnType.SHORT, 2),
        (2, ColumnType.INT24, 2),
        (2, ColumnType.LONG, 2),
        (2, ColumnType.LONGLONG, 2),
        (1.0, ColumnType.FLOAT, 1.0),
        (1.0, ColumnType.DOUBLE, 1.0),
    ]
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "rv, expected",
    [
        (((("x",),), ("b",)), [{"b": "x"}]),
        (([["1"]], ["b"]), [{"b": "1"}]),
        (([(1,)], ("b",)), [{"b": 1}]),
        (([(1.0,)], ("b",)), [{"b": 1.0}]),
        (([(b"x",)], ("b",)), [{"b": "x"}]),
        (([(True,)], ("b",)), [{"b": True}]),
        (([(date(2021, 1, 1),)], ("b",)), [{"b": date(2021, 1, 1)}]),
        (
            ([(datetime(2021, 1, 1, 1, 1, 1),)], ("b",)),
            [{"b": datetime(2021, 1, 1, 1, 1, 1)}],
        ),
        (([(timedelta(seconds=60),)], ("b",)), [{"b": timedelta(seconds=60)}]),
        (([(None,)], ["b"]), [{"b": None}]),
        (([(None, 1, 1)], ["a", "b", "c"]), [{"a": None, "b": 1, "c": 1}]),
        (([(1, None, 1)], ["a", "b", "c"]), [{"a": 1, "b": None, "c": 1}]),
        (([(1, 1, None)], ["a", "b", "c"]), [{"a": 1, "b": 1, "c": None}]),
        (([[None], [1]], ["b"]), [{"b": None}, {"b": 1}]),
        (
            ResultSet(
                rows=[("hello",)],
                columns=[
                    ResultColumn(
                        name="b",
                        character_set=CharacterSet.utf8mb4,
                        type=ColumnType.VARCHAR,
                        text_encoder=lambda col, val: b"world",
                        binary_encoder=lambda col, val: b"\x05world",
                    )
                ],
            ),
            [{"b": "world"}],
        ),
        *EXPLICIT_TYPE_TESTS,
    ],
)
async def test_query(
    session: MockSession,
    rv: AllowedResult,
    expected: List[Dict[str, Any]],
    query_fixture: QueryFixture,
) -> None:
    session.return_value = rv
    result = await query_fixture("SELECT b FROM a")
    assert expected == result


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "sql, params, expected",
    [
        ("SELECT ? FROM x", ("1",), "SELECT '1' FROM x"),
        ("SELECT '?' FROM x", (), "SELECT '?' FROM x"),
        ("SELECT ? FROM x", (1,), "SELECT 1 FROM x"),
        ("SELECT ? FROM x", (0,), "SELECT 0 FROM x"),
        ("SELECT ? FROM x", (-1,), "SELECT -1 FROM x"),
        ("SELECT ? FROM x", (255,), "SELECT 255 FROM x"),
        ("SELECT ? FROM x", (-128,), "SELECT -128 FROM x"),
        ("SELECT ? FROM x", (65535,), "SELECT 65535 FROM x"),
        ("SELECT ? FROM x", (-32767,), "SELECT -32767 FROM x"),
        ("SELECT ? FROM x", (4294967295,), "SELECT 4294967295 FROM x"),
        ("SELECT ? FROM x", (-2147483648,), "SELECT -2147483648 FROM x"),
        (
            "SELECT ? FROM x",
            (18446744073709551615,),
            "SELECT 18446744073709551615 FROM x",
        ),
        (
            "SELECT ? FROM x",
            (-9223372036854775808,),
            "SELECT -9223372036854775808 FROM x",
        ),
        ("SELECT ? FROM x", (1.1,), "SELECT 1.1 FROM x"),
        ("SELECT ? FROM x", (1.7e308,), "SELECT 1.7e+308 FROM x"),
        ("SELECT ? FROM x", (None,), "SELECT NULL FROM x"),
        ("SELECT ? FROM x", (b"hello",), "SELECT 'hello' FROM x"),
        ("SELECT ? FROM x", (io.BytesIO(b"hello"),), "SELECT 'hello' FROM x"),
        ("SELECT ?, ? FROM x", ("1", "1"), "SELECT '1', '1' FROM x"),
        (
            "SELECT ?, ?, ?, ? FROM x",
            ("1", None, io.BytesIO(b"hello"), 1),
            "SELECT '1', NULL, 'hello', 1 FROM x",
        ),
    ],
)
async def test_prepared_stmt(
    session: MockSession,
    mysql_connector_conn: MySQLConnectionAbstract,
    sql: str,
    params: Tuple[Any],
    expected: str,
) -> None:
    session.echo = True
    result = await query(
        conn=mysql_connector_conn,
        sql=sql,
        cursor_class=PreparedDictCursor,
        params=params,
    )
    assert expected == result[0]["sql"]


@pytest.mark.asyncio
async def test_init(port: int, session: MockSession, server: MysqlServer) -> None:
    async with aiomysql.connect(
        port=port, user="levon_helm", db="db", program_name="test"
    ):
        connection = session.connection
        assert connection is not None
        assert connection.session.username == "levon_helm"
        assert connection.client_connect_attrs["program_name"] == "test"
        assert connection.session.database == "db"


@pytest.mark.asyncio
async def test_connection_id(
    port: int, session: MockSession, server: MysqlServer
) -> None:
    async with aiomysql.connect(port=port) as conn1:
        async with aiomysql.connect(port=port) as conn2:
            assert conn1.server_thread_id[0] + 1 == conn2.server_thread_id[0]

    assert session.ctx is not None
    assert session.ctx.get(context.connection_id) is not None


@pytest.mark.asyncio
async def test_replace_function(
    session: MockSession, server: MysqlServer, connect: ConnectFixture
) -> None:
    session.echo = True

    with closing(await connect(user="levon_helm", database="db")) as conn:
        result = await query(conn, "SELECT CONNECTION_ID()")
        assert result[0]["CONNECTION_ID()"] is not None

        result = await query(conn, "SELECT CURRENT_USER")
        assert result[0]["CURRENT_USER()"] == "levon_helm"

        result = await query(conn, "SELECT USER()")
        assert result[0]["USER()"] == "levon_helm"

        result = await query(conn, "SELECT DATABASE()")
        assert result[0]["DATABASE()"] == "db"

        result = await query(conn, "SELECT schema()")
        assert result[0]["SCHEMA()"] == "db"


@pytest.mark.asyncio
@pytest.mark.parametrize("cursor_class", [MySQLCursorDict, PreparedDictCursor])
async def test_query_attributes(
    session: MockSession,
    server: MysqlServer,
    mysql_connector_conn: MySQLConnectionAbstract,
    cursor_class: Type[MySQLCursor],
) -> None:
    session.echo = True

    sql = "SELECT 1 FROM x"
    query_attrs = {
        "id": cursor_class.__name__,
        "str": "foo",
        "int": 1,
        "float": 1.1,
    }
    await query(
        sql=sql,
        conn=mysql_connector_conn,
        query_attributes=query_attrs,  # type: ignore
        cursor_class=cursor_class,
    )
    assert session.last_query_attrs == query_attrs


@pytest.mark.asyncio
async def test_describe_select(
    session: MockSession,
    server: MysqlServer,
    query_fixture: QueryFixture,
) -> None:
    session.echo = True
    sql = "DESCRIBE SELECT b from a"
    with freeze_time("2023-01-01"):
        result = await query_fixture(sql)
        assert [{"sql": "DESCRIBE SELECT b from a"}] == list(result)


# pylint: disable=trailing-whitespace
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "sql, expected",
    [
        # SET session variable
        (
            "SET SESSION sql_mode = 'TRADITIONAL'; SELECT @@sql_mode",
            [{"@@sql_mode": "TRADITIONAL"}],
        ),
        (
            "SET LOCAL sql_mode = 'TRADITIONAL'; SELECT @@sql_mode",
            [{"@@sql_mode": "TRADITIONAL"}],
        ),
        (
            "SET @@SESSION.sql_mode = 'TRADITIONAL'; SELECT @@sql_mode",
            [{"@@sql_mode": "TRADITIONAL"}],
        ),
        (
            "SET @@LOCAL.sql_mode = 'TRADITIONAL'; SELECT @@sql_mode",
            [{"@@sql_mode": "TRADITIONAL"}],
        ),
        (
            "SET @@sql_mode = 'TRADITIONAL'; SELECT @@sql_mode",
            [{"@@sql_mode": "TRADITIONAL"}],
        ),
        (
            "SET sql_mode = 'TRADITIONAL'; SELECT @@sql_mode",
            [{"@@sql_mode": "TRADITIONAL"}],
        ),
        (
            "select @@version_comment limit 1",
            [{"@@version_comment": "mysql-mimic"}],
        ),
        (
            "SET character_set_results = NULL; SELECT @@character_set_results",
            [{"@@character_set_results": "utf8mb4"}],
        ),
        (
            "SET SQL_AUTO_IS_NULL = 0; SELECT @@sql_auto_is_null",
            [{"@@sql_auto_is_null": False}],
        ),
        (
            "set @@sql_select_limit=DEFAULT; SELECT @@sql_select_limit",
            [{"@@sql_select_limit": None}],
        ),
        # SET referencing other parameters
        (
            """
            SET character_set_connection = 'big5';
            SET character_set_client = @@character_set_connection; SELECT @@character_set_client""",
            [{"@@character_set_client": "big5"}],
        ),
        # SET multiple variables at once
        (
            "SET autocommit = OFF, sql_mode = 'TRADITIONAL'; SELECT @@autocommit, @@sql_mode",
            [{"@@autocommit": False, "@@sql_mode": "TRADITIONAL"}],
        ),
        # SET_VAR
        (
            "SELECT @@max_execution_time",
            [{"@@max_execution_time": 0}],
        ),
        (
            "SELECT /*+ SET_VAR(max_execution_time=1) */ @@max_execution_time",
            [{"@@max_execution_time": 1}],
        ),
        (
            "SELECT /*+ SET_VAR(max_execution_time=1, sql_mode = 'foo') */ @@max_execution_time, @@sql_mode",
            [{"@@max_execution_time": 1, "@@sql_mode": "foo"}],
        ),
        (
            "SELECT /*+ SET_VAR(max_execution_time=1, sql_mode = 'foo') EXECUTE_AS('barak_alon') */ @@max_execution_time, @@sql_mode",
            [{"@@max_execution_time": 1, "@@sql_mode": "foo"}],
        ),
        (
            """
            SELECT
              /*+ SET_VAR(max_execution_time=2) */
              x
            FROM (
              SELECT
                /*+ SET_VAR(max_execution_time=1) */
                @@max_execution_time AS x
            ) AS a
            """,
            [{"x": 2}],
        ),
        # SET names
        (
            """
            SET NAMES utf8;
            SELECT @@character_set_client, @@SESSION.character_set_connection, @@character_set_results, @@collation_connection""",
            [
                {
                    "@@character_set_client": "utf8",
                    "@@SESSION.character_set_connection": "utf8",
                    "@@character_set_results": "utf8",
                    "@@collation_connection": "utf8_general_ci",
                }
            ],
        ),
        (
            """
            SET NAMES big5; SET NAMES DEFAULT;
            SELECT @@character_set_client, @@SESSION.character_set_connection, @@character_set_results, @@collation_connection""",
            [
                {
                    "@@character_set_client": "utf8mb4",
                    "@@SESSION.character_set_connection": "utf8mb4",
                    "@@character_set_results": "utf8mb4",
                    "@@collation_connection": "utf8mb4_general_ci",
                }
            ],
        ),
        (
            """
            SET NAMES utf8 COLLATE utf8mb4_bin;
            SELECT @@character_set_client, @@SESSION.character_set_connection, @@character_set_results, @@collation_connection""",
            [
                {
                    "@@character_set_client": "utf8",
                    "@@SESSION.character_set_connection": "utf8",
                    "@@character_set_results": "utf8",
                    "@@collation_connection": "utf8mb4_bin",
                }
            ],
        ),
        (
            """
            set names 'big5' collate 'big5_chinese_ci';
            SELECT @@character_set_client, @@SESSION.character_set_connection, @@character_set_results, @@collation_connection""",
            [
                {
                    "@@character_set_client": "big5",
                    "@@SESSION.character_set_connection": "big5",
                    "@@character_set_results": "big5",
                    "@@collation_connection": "big5_chinese_ci",
                }
            ],
        ),
        # SET character set
        (
            """
            SET CHARSET 'utf8';
            SELECT @@character_set_client, @@SESSION.character_set_connection, @@character_set_results""",
            [
                {
                    "@@character_set_client": "utf8",
                    "@@SESSION.character_set_connection": "utf8mb4",
                    "@@character_set_results": "utf8",
                }
            ],
        ),
        (
            """
            SET CHARSET utf8;
            SELECT @@character_set_client, @@SESSION.character_set_connection, @@character_set_results""",
            [
                {
                    "@@character_set_client": "utf8",
                    "@@SESSION.character_set_connection": "utf8mb4",
                    "@@character_set_results": "utf8",
                }
            ],
        ),
        (
            """
            SET CHARSET utf8; SET CHARSET DEFAULT;
            SELECT @@character_set_client, @@SESSION.character_set_connection, @@character_set_results""",
            [
                {
                    "@@character_set_client": "utf8mb4",
                    "@@SESSION.character_set_connection": "utf8mb4",
                    "@@character_set_results": "utf8mb4",
                }
            ],
        ),
        # SET transaction
        (
            """
            set session transaction read only;
            SELECT @@session.transaction_read_only""",
            [
                {
                    "@@session.transaction_read_only": True,
                }
            ],
        ),
        (
            """
            SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ WRITE;
            SELECT @@transaction_isolation, @@transaction_read_only""",
            [
                {
                    "@@transaction_isolation": "REPEATABLE-READ",
                    "@@transaction_read_only": False,
                }
            ],
        ),
        # Types
        ("SET autocommit = OFF; SELECT @@autocommit AS x", [{"x": False}]),
        ("SET autocommit = ON; SELECT @@autocommit AS x", [{"x": True}]),
        ("SET autocommit = 1; SELECT @@autocommit AS x", [{"x": True}]),
        ("SET autocommit = 0; SELECT @@autocommit AS x", [{"x": False}]),
        (
            "SET lower_case_table_names = 1; SELECT @@lower_case_table_names AS x",
            [{"x": 1}],
        ),
        # Simple queries
        ("SELECT 1, 2", [{"1": 1, "2": 2}]),
        ("SELECT '1' AS Hello", [{"hello": "1"}]),
        # USE
        ("USE db2; SELECT DATABASE()", [{"DATABASE()": "db2"}]),
        # INFORMATION_SCHEMA
        (
            """
        SELECT
          *
        FROM information_schema.schemata
        ORDER BY schema_name""",
            [
                {
                    "catalog_name": "def",
                    "schema_name": schema_name,
                    "default_character_set_name": "utf8mb4",
                    "default_collation_name": "utf8mb4_general_ci",
                    "sql_path": None,
                }
                for schema_name in ["db", "information_schema", "mysql"]
            ],
        ),
        (
            """
        SELECT
          *
        FROM information_schema.tables
        ORDER BY table_schema, table_name""",
            [
                {
                    "auto_increment": None,
                    "avg_row_length": None,
                    "check_time": None,
                    "checksum": None,
                    "create_options": None,
                    "create_time": None,
                    "data_free": None,
                    "data_length": None,
                    "engine": "MinervaSQL",
                    "index_length": None,
                    "max_data_length": None,
                    "row_format": None,
                    "table_catalog": "def",
                    "table_collation": "utf8mb4_general_ci ",
                    "table_comment": None,
                    "table_name": table_name,
                    "table_rows": None,
                    "table_schema": table_schema,
                    "table_type": table_type,
                    "update_time": None,
                    "version": "1.0",
                }
                for table_schema, table_name, table_type in sorted(
                    [
                        ("db", "x", "BASE TABLE"),
                        ("db", "y", "BASE TABLE"),
                        *[
                            ("information_schema", name, "SYSTEM TABLE")
                            for name in INFO_SCHEMA["information_schema"]
                        ],
                        *[
                            ("mysql", name, "SYSTEM TABLE")
                            for name in INFO_SCHEMA["mysql"]
                        ],
                    ]
                )
            ],
        ),
        (
            """
        SELECT
          table_catalog,
          table_schema,
          table_name,
          column_name,
          ordinal_position,
          data_type
        FROM information_schema.columns
        WHERE table_schema = 'db' AND table_name LIKE 'x' AND column_name NOT LIKE 'a'
        ORDER BY table_schema, table_name, column_name""",
            [
                {
                    "table_catalog": "def",
                    "table_schema": "db",
                    "table_name": "x",
                    "column_name": "b",
                    "ordinal_position": 1,
                    "data_type": "TEXT",
                }
            ],
        ),
        (
            """
        SELECT
          *
        FROM information_schema.key_column_usage""",
            [],
        ),
        (
            queries.TABLEAU_SCHEMATA,
            [
                {
                    "_col_0": None,
                    "_col_1": None,
                    "_col_2": None,
                    "schema_name": schema_name,
                }
                for schema_name in ["db", "information_schema", "mysql"]
            ],
        ),
        (
            queries.TABLEAU_TABLES,
            [
                {
                    "_col_2": "TABLE",
                    "table_comment": None,
                    "table_name": table_name,
                    "table_schema": "db",
                }
                for table_name in ["x", "y"]
            ],
        ),
        (
            queries.TABLEAU_COLUMNS,
            [],
        ),
        (
            queries.TABLEAU_INDEXES_2,
            [],
        ),
        (
            queries.TABLEAU_INDEXES_1,
            [],
        ),
        (
            "SELECT CATALOG_NAME AS CatalogName FROM INFORMATION_SCHEMA.SCHEMATA LIMIT 1",
            [{"catalogname": "def"}],
        ),
        # SHOW
        (
            "show variables",
            [
                {"Value": "1", "Variable_name": "auto_increment_increment"},
                {"Value": "False", "Variable_name": "autocommit"},
                {"Value": "utf8mb4", "Variable_name": "character_set_client"},
                {"Value": "utf8mb4", "Variable_name": "character_set_connection"},
                {"Value": "utf8mb4", "Variable_name": "character_set_database"},
                {"Value": "utf8mb4", "Variable_name": "character_set_results"},
                {"Value": "utf8mb4", "Variable_name": "character_set_server"},
                {
                    "Value": "utf8mb4_general_ci",
                    "Variable_name": "collation_connection",
                },
                {"Value": "utf8mb4_general_ci", "Variable_name": "collation_database"},
                {"Value": "utf8mb4_general_ci", "Variable_name": "collation_server"},
                {"Value": "mysql-mimic", "Variable_name": "default_storage_engine"},
                {"Value": "mysql-mimic", "Variable_name": "default_tmp_storage_engine"},
                {"Value": "OFF", "Variable_name": "event_scheduler"},
                {"Value": "levon_helm", "Variable_name": "external_user"},
                {"Value": "", "Variable_name": "init_connect"},
                {"Value": "28800", "Variable_name": "interactive_timeout"},
                {"Value": "MIT", "Variable_name": "license"},
                {"Value": "0", "Variable_name": "lower_case_table_names"},
                {"Value": "67108864", "Variable_name": "max_allowed_packet"},
                {"Value": "0", "Variable_name": "max_execution_time"},
                {"Value": "16384", "Variable_name": "net_buffer_length"},
                {"Value": "28800", "Variable_name": "net_write_timeout"},
                {"Value": "False", "Variable_name": "performance_schema"},
                {"Value": "False", "Variable_name": "sql_auto_is_null"},
                {"Value": "ANSI", "Variable_name": "sql_mode"},
                {"Value": None, "Variable_name": "sql_select_limit"},
                {"Value": "UTC", "Variable_name": "system_time_zone"},
                {"Value": "UTC", "Variable_name": "time_zone"},
                {"Value": "READ-COMMITTED", "Variable_name": "transaction_isolation"},
                {"Value": "False", "Variable_name": "transaction_read_only"},
                {"Value": "8.0.29", "Variable_name": "version"},
                {"Value": "mysql-mimic", "Variable_name": "version_comment"},
                {"Value": "28800", "Variable_name": "wait_timeout"},
            ],
        ),
        (
            "SHOW  SESSION  VARIABLES  LIKE 'version_%'",
            [{"Value": "mysql-mimic", "Variable_name": "version_comment"}],
        ),
        ("show index from x", []),
        (
            "show columns from x like '%'",
            [
                {
                    "Default": None,
                    "Extra": None,
                    "Field": "a",
                    "Key": None,
                    "Null": "YES",
                    "Type": "TEXT",
                },
                {
                    "Default": None,
                    "Extra": None,
                    "Field": "b",
                    "Key": None,
                    "Null": "YES",
                    "Type": "TEXT",
                },
            ],
        ),
        (
            "describe x",
            [
                {
                    "Default": None,
                    "Extra": None,
                    "Field": "a",
                    "Key": None,
                    "Null": "YES",
                    "Type": "TEXT",
                },
                {
                    "Default": None,
                    "Extra": None,
                    "Field": "b",
                    "Key": None,
                    "Null": "YES",
                    "Type": "TEXT",
                },
            ],
        ),
        (
            "show tables from information_schema like 'k%'",
            [
                {"Table_name": "key_column_usage"},
            ],
        ),
        (
            "show full tables from db like 'x'",
            [{"Table_name": "x", "Table_type": "BASE TABLE"}],
        ),
        ("show databases like '_n%'", [{"Database": "information_schema"}]),
        # DataGrip
        (
            queries.DATA_GRIP_VARIABLES,
            [
                {
                    "auto_increment_increment": 1,
                    "character_set_client": "utf8mb4",
                    "character_set_connection": "utf8mb4",
                    "character_set_results": "utf8mb4",
                    "character_set_server": "utf8mb4",
                    "collation_connection": "utf8mb4_general_ci",
                    "collation_server": "utf8mb4_general_ci",
                    "init_connect": "",
                    "interactive_timeout": 28800,
                    "license": "MIT",
                    "lower_case_table_names": 0,
                    "max_allowed_packet": 67108864,
                    "net_write_timeout": 28800,
                    "performance_schema": 0,
                    "sql_mode": "ANSI",
                    "system_time_zone": "UTC",
                    "time_zone": "UTC",
                    "transaction_isolation": "READ-COMMITTED",
                    "wait_timeout": 28800,
                }
            ],
        ),
        (
            "select database(), schema(), left(user(),instr(concat(user(),'@'), '@')-1)",
            [{"DATABASE()": None, "SCHEMA()": None, "_col_2": "levon_helm"}],
        ),
        (queries.DATA_GRIP_PARAMETERS, []),
        (
            queries.DATA_GRIP_TABLES,
            [
                {
                    "ref_generation": None,
                    "remarks": None,
                    "self_referencing_col_name": None,
                    "table_cat": "db",
                    "table_name": "x",
                    "table_schem": None,
                    "table_type": "TABLE",
                    "type_cat": None,
                    "type_name": None,
                    "type_schem": None,
                },
                {
                    "ref_generation": None,
                    "remarks": None,
                    "self_referencing_col_name": None,
                    "table_cat": "db",
                    "table_name": "y",
                    "table_schem": None,
                    "table_type": "TABLE",
                    "type_cat": None,
                    "type_name": None,
                    "type_schem": None,
                },
            ],
        ),
        # Timestamps
        (
            "select now(), curtime(), curdate(), current_time",
            [
                {
                    "NOW()": "2023-01-01 00:00:00",
                    "CURTIME()": "00:00:00",
                    "CURDATE()": "2023-01-01",
                    "CURRENT_TIME()": "00:00:00",
                }
            ],
        ),
    ],
)
async def test_commands(
    session: MockSession,
    server: MysqlServer,
    query_fixture: QueryFixture,
    sql: str,
    expected: List[Dict[str, Any]],
) -> None:
    session.execute = True
    with freeze_time("2023-01-01"):
        result = await query_fixture(sql)
        assert expected == list(result)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "sql,  msg",
    [
        (
            "SET GLOBAL sql_mode = 'TRADITIONAL'",
            "Cannot SET variable sql_mode with scope GLOBAL",
        ),
        ("SET @foo = 'bar'", "User-defined variables not supported yet"),
        ("KILL 'abc'", "Invalid KILL connection ID"),
        (
            # pick a dynamic string session var
            "SET init_connect='abc' in xyz",
            "Complex expressions in variables not supported yet",
        ),
    ],
)
async def test_unsupported_commands(
    session: MockSession,
    server: MysqlServer,
    query_fixture: QueryFixture,
    sql: str,
    msg: str,
) -> None:
    with pytest.raises(Exception) as ctx:
        await query_fixture(sql)
    assert msg in str(ctx.value)


@pytest.mark.asyncio
async def test_async_iterator(
    session: MockSession,
    server: MysqlServer,
    query_fixture: QueryFixture,
) -> None:
    async def generate_rows() -> Any:
        yield 1, None, None
        await asyncio.sleep(0)
        yield None, "2", None
        await asyncio.sleep(0)
        yield None, None, None

    session.return_value = (generate_rows(), ["a", "b", "c"])

    result = await query_fixture("SELECT * FROM x")
    assert [
        {"a": 1, "b": None, "c": None},
        {"a": None, "b": "2", "c": None},
        {"a": None, "b": None, "c": None},
    ] == result


@pytest.mark.asyncio
async def test_sqlalchemy_session(
    server: MysqlServer,
    sqlalchemy_engine: AsyncEngine,
) -> None:
    Session = async_sessionmaker(sqlalchemy_engine)
    async with Session() as session:
        async with session.begin():
            result = await session.execute(text("SELECT 1"))
            assert result.scalars().one() == 1
            await session.commit()
