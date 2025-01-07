from contextlib import closing
from typing import Optional, Tuple, Dict

import pytest
from mysql.connector import DatabaseError
from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.plugins.mysql_clear_password import MySQLClearPasswordAuthPlugin

from mysql_mimic import User
from mysql_mimic.auth import (
    NativePasswordAuthPlugin,
    AbstractClearPasswordAuthPlugin,
    NoLoginAuthPlugin,
)
from tests.conftest import query, to_thread, ConnectFixture

# mysql.connector throws an error if you try to use mysql_clear_password without SSL.
# That's silly, since SSL termination doesn't have to be handled by MySQL.
# But it's extra silly in tests.
MySQLClearPasswordAuthPlugin.requires_ssl = False  # type: ignore
MySQLConnectionAbstract.is_secure = True  # type: ignore

SIMPLE_AUTH_USER = "levon_helm"

PASSWORD_AUTH_USER = "rick_danko"
PASSWORD_AUTH_PASSWORD = "nazareth"
PASSWORD_AUTH_OLD_PASSWORD = "cannonball"
PASSWORD_AUTH_PLUGIN = NativePasswordAuthPlugin.client_plugin_name


class TestPlugin(AbstractClearPasswordAuthPlugin):
    name = "mysql_clear_password"

    async def check(self, username: str, password: str) -> Optional[str]:
        return username if username == password else None


TEST_PLUGIN_AUTH_USER = "garth_hudson"
TEST_PLUGIN_AUTH_PASSWORD = TEST_PLUGIN_AUTH_USER
TEST_PLUGIN_AUTH_PLUGIN = TestPlugin.client_plugin_name

NO_LOGIN_USER = "carmen_and_the_devil"
NO_LOGIN_PLUGIN = NoLoginAuthPlugin.name

UNKNOWN_PLUGIN_USER = "richard_manuel"
NO_PLUGIN_USER = "miss_moses"


@pytest.fixture(autouse=True)
def users() -> Dict[str, User]:
    return {
        SIMPLE_AUTH_USER: User(
            name=SIMPLE_AUTH_USER,
            auth_string=None,
            auth_plugin=NativePasswordAuthPlugin.name,
        ),
        PASSWORD_AUTH_USER: User(
            name=PASSWORD_AUTH_USER,
            auth_string=NativePasswordAuthPlugin.create_auth_string(
                PASSWORD_AUTH_PASSWORD
            ),
            old_auth_string=NativePasswordAuthPlugin.create_auth_string(
                PASSWORD_AUTH_OLD_PASSWORD
            ),
            auth_plugin=NativePasswordAuthPlugin.name,
        ),
        TEST_PLUGIN_AUTH_USER: User(
            name=TEST_PLUGIN_AUTH_USER,
            auth_string=TEST_PLUGIN_AUTH_PASSWORD,
            auth_plugin=TestPlugin.name,
        ),
        UNKNOWN_PLUGIN_USER: User(name=UNKNOWN_PLUGIN_USER, auth_plugin="unknown"),
        NO_PLUGIN_USER: User(name=NO_PLUGIN_USER, auth_plugin=NO_LOGIN_PLUGIN),
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "auth_plugins,username,password,auth_plugin",
    [
        (
            [NativePasswordAuthPlugin()],
            PASSWORD_AUTH_USER,
            PASSWORD_AUTH_PASSWORD,
            PASSWORD_AUTH_PLUGIN,
        ),
        (
            [TestPlugin()],
            TEST_PLUGIN_AUTH_USER,
            TEST_PLUGIN_AUTH_PASSWORD,
            TEST_PLUGIN_AUTH_PLUGIN,
        ),
        ([NativePasswordAuthPlugin()], SIMPLE_AUTH_USER, None, None),
        ([TestPlugin(), NativePasswordAuthPlugin()], SIMPLE_AUTH_USER, None, None),
        (None, SIMPLE_AUTH_USER, None, None),
    ],
)
async def test_auth(
    connect: ConnectFixture,
    username: str,
    password: Optional[str],
    auth_plugin: Optional[str],
) -> None:
    kwargs = {"user": username, "password": password, "auth_plugin": auth_plugin}
    kwargs = {k: v for k, v in kwargs.items() if v is not None}
    with closing(await connect(**kwargs)) as conn:
        assert await query(conn=conn, sql="SELECT USER() AS a") == [{"a": username}]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "auth_plugins",
    [
        [NativePasswordAuthPlugin()],
    ],
)
async def test_auth_secondary_password(
    connect: ConnectFixture,
) -> None:
    with closing(
        await connect(
            user=PASSWORD_AUTH_USER,
            password=PASSWORD_AUTH_OLD_PASSWORD,
            auth_plugin=PASSWORD_AUTH_PLUGIN,
        )
    ) as conn:
        assert await query(conn=conn, sql="SELECT USER() AS a") == [
            {"a": PASSWORD_AUTH_USER}
        ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "auth_plugins,user1,user2",
    [
        (
            [NativePasswordAuthPlugin(), TestPlugin()],
            (PASSWORD_AUTH_USER, PASSWORD_AUTH_PASSWORD, PASSWORD_AUTH_PLUGIN),
            (TEST_PLUGIN_AUTH_USER, TEST_PLUGIN_AUTH_PASSWORD, TEST_PLUGIN_AUTH_PLUGIN),
        ),
        (
            [NativePasswordAuthPlugin()],
            (PASSWORD_AUTH_USER, PASSWORD_AUTH_PASSWORD, PASSWORD_AUTH_PLUGIN),
            (PASSWORD_AUTH_USER, PASSWORD_AUTH_PASSWORD, PASSWORD_AUTH_PLUGIN),
        ),
    ],
)
async def test_change_user(
    connect: ConnectFixture,
    user1: Tuple[str, str, str],
    user2: Tuple[str, str, str],
) -> None:
    kwargs1 = {"user": user1[0], "password": user1[1], "auth_plugin": user1[2]}
    kwargs1 = {k: v for k, v in kwargs1.items() if v is not None}

    with closing(await connect(**kwargs1)) as conn:
        # mysql.connector doesn't have great support for COM_CHANGE_USER
        # Here, we have to manually override the auth plugin to use
        conn._auth_plugin = user2[2]  # pylint: disable=protected-access

        await to_thread(conn.cmd_change_user, username=user2[0], password=user2[1])
        assert await query(conn=conn, sql="SELECT USER() AS a") == [{"a": user2[0]}]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "auth_plugins,username,password,auth_plugin,msg",
    [
        ([NativePasswordAuthPlugin()], None, None, None, "User  does not exist"),
        (
            [TestPlugin()],
            PASSWORD_AUTH_USER,
            PASSWORD_AUTH_PASSWORD,
            PASSWORD_AUTH_PLUGIN,
            "Access denied",
        ),
        # This test doesn't work with newer versions of mysql-connector-python.
        # ([NoLoginAuthPlugin()], NO_PLUGIN_USER, None, None, "Access denied"),
        (
            [NativePasswordAuthPlugin(), NoLoginAuthPlugin()],
            NO_PLUGIN_USER,
            None,
            None,
            "Access denied",
        ),
    ],
)
async def test_access_denied(
    connect: ConnectFixture,
    username: Optional[str],
    password: Optional[str],
    auth_plugin: Optional[str],
    msg: str,
) -> None:
    kwargs = {"user": username, "password": password, "auth_plugin": auth_plugin}
    kwargs = {k: v for k, v in kwargs.items() if v is not None}

    with pytest.raises(DatabaseError) as ctx:
        await connect(**kwargs)

    assert msg in str(ctx.value)
