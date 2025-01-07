from __future__ import annotations

import io
from copy import copy
from hashlib import sha1
import logging
from dataclasses import dataclass
from typing import Optional, Dict, AsyncGenerator, Union, Tuple, Sequence

from mysql_mimic.types import read_str_null
from mysql_mimic import utils

logger = logging.getLogger(__name__)


# Many authentication plugins don't need to send any sort of challenge/nonce.
FILLER = b"0" * 20 + b"\x00"


@dataclass
class Forbidden:
    msg: Optional[str] = None


@dataclass
class Success:
    authenticated_as: str


@dataclass
class User:
    name: str
    auth_string: Optional[str] = None
    auth_plugin: Optional[str] = None

    # For plugins that support a primary and secondary password
    # This is helpful for zero-downtime password rotation
    old_auth_string: Optional[str] = None


@dataclass
class AuthInfo:
    username: str
    data: bytes
    user: User
    connect_attrs: Dict[str, str]
    client_plugin_name: Optional[str]
    handshake_auth_data: Optional[bytes]
    handshake_plugin_name: str

    def copy(self, data: bytes) -> AuthInfo:
        new = copy(self)
        new.data = data
        return new


Decision = Union[Success, Forbidden, bytes]
AuthState = AsyncGenerator[Decision, AuthInfo]


class AuthPlugin:
    """
    Abstract base class for authentication plugins.
    """

    name = ""
    client_plugin_name: Optional[str] = None  # None means any

    async def auth(self, auth_info: Optional[AuthInfo] = None) -> AuthState:
        """
        Create an async generator that drives the authentication lifecycle.

        This should either yield `bytes`, in which case an AuthMoreData packet is sent to the client,
        or a `Success` or `Forbidden` instance, in which case authentication is complete.

        Args:
             auth_info: This is None if authentication is starting from the optimistic handshake.
        """
        yield Forbidden()

    async def start(
        self, auth_info: Optional[AuthInfo] = None
    ) -> Tuple[Decision, AuthState]:
        state = self.auth(auth_info)
        data = await state.__anext__()
        return data, state


class AbstractClearPasswordAuthPlugin(AuthPlugin):
    """
    Abstract class for implementing the server-side of the standard client plugin "mysql_clear_password".
    """

    name = "abstract_mysql_clear_password"
    client_plugin_name = "mysql_clear_password"

    async def auth(self, auth_info: Optional[AuthInfo] = None) -> AuthState:
        if not auth_info:
            auth_info = yield FILLER

        r = io.BytesIO(auth_info.data)
        password = read_str_null(r).decode()
        authenticated_as = await self.check(auth_info.username, password)
        if authenticated_as is not None:
            yield Success(authenticated_as)
        else:
            yield Forbidden()

    async def check(self, username: str, password: str) -> Optional[str]:
        return username


class NativePasswordAuthPlugin(AuthPlugin):
    """
    Standard plugin that uses a password hashing method.

    The client hashed the password using a nonce provided by the server, so the
    password can't be snooped on the network.

    Furthermore, thanks to some clever hashing techniques, knowing the hash stored in the
    user database isn't enough to authenticate as that user.
    """

    name = "mysql_native_password"
    client_plugin_name = "mysql_native_password"

    async def auth(self, auth_info: Optional[AuthInfo] = None) -> AuthState:
        if (
            auth_info
            and auth_info.handshake_plugin_name == self.name
            and auth_info.handshake_auth_data
        ):
            # mysql_native_password can reuse the nonce from the initial handshake
            nonce = auth_info.handshake_auth_data.rstrip(b"\x00")
        else:
            nonce = utils.nonce(20)
            # Some clients expect a null terminating byte
            auth_info = yield nonce + b"\x00"

        user = auth_info.user
        if self.password_matches(user=user, scramble=auth_info.data, nonce=nonce):
            yield Success(user.name)
        else:
            yield Forbidden()

    def empty_password_quickpath(self, user: User, scramble: bytes) -> bool:
        return not scramble and not user.auth_string

    def password_matches(self, user: User, scramble: bytes, nonce: bytes) -> bool:
        return (
            self.empty_password_quickpath(user, scramble)
            or self.verify_scramble(user.auth_string, scramble, nonce)
            or self.verify_scramble(user.old_auth_string, scramble, nonce)
        )

    def verify_scramble(
        self, auth_string: Optional[str], scramble: bytes, nonce: bytes
    ) -> bool:
        # From docs,
        # response.data should be:
        #   SHA1(password) XOR SHA1("20-bytes random data from server" <concat> SHA1(SHA1(password)))
        # auth_string should be:
        #   SHA1(SHA1(password))
        try:
            sha1_sha1_password = bytes.fromhex(auth_string or "")
            sha1_sha1_with_nonce = sha1(nonce + sha1_sha1_password).digest()
            rcvd_sha1_password = utils.xor(scramble, sha1_sha1_with_nonce)
            return sha1(rcvd_sha1_password).digest() == sha1_sha1_password
        except Exception:  # pylint: disable=broad-except
            logger.info("Invalid scramble")
            return False

    @classmethod
    def create_auth_string(cls, password: str) -> str:
        return sha1(sha1(password.encode("utf-8")).digest()).hexdigest()


class KerberosAuthPlugin(AuthPlugin):
    """
    This plugin implements the Generic Security Service Application Program Interface (GSS-API) by way of the Kerberos
    mechanism as described in RFC1964(https://www.rfc-editor.org/rfc/rfc1964.html).
    """

    name = "authentication_kerberos"
    client_plugin_name = "authentication_kerberos_client"

    def __init__(self, service: str, realm: str) -> None:
        self.service = service
        self.realm = realm

    async def auth(self, auth_info: Optional[AuthInfo] = None) -> AuthState:
        import gssapi
        from gssapi.exceptions import GSSError

        # Fast authentication not supported
        if not auth_info:
            yield b""

        auth_info = (
            yield len(self.service).to_bytes(2, "little")
            + self.service.encode("utf-8")
            + len(self.realm).to_bytes(2, "little")
            + self.realm.encode("utf-8")
        )

        server_creds = gssapi.Credentials(
            usage="accept", name=gssapi.Name(f"{self.service}@{self.realm}")
        )
        server_ctx = gssapi.SecurityContext(usage="accept", creds=server_creds)

        try:
            server_ctx.step(auth_info.data)
        except GSSError as e:
            yield Forbidden(str(e))

        username = str(server_ctx.initiator_name).split("@", 1)[0]
        if auth_info.username and auth_info.username != username:
            yield Forbidden("Given username different than kerberos client")
        yield Success(username)


class NoLoginAuthPlugin(AuthPlugin):
    """
    Standard plugin that prevents all clients from direct login.

    This is useful for user accounts that can only be accessed by proxy authentication.
    """

    name = "mysql_no_login"
    client_plugin_name = None

    async def auth(self, auth_info: Optional[AuthInfo] = None) -> AuthState:
        if not auth_info:
            _ = yield FILLER
        yield Forbidden()


class IdentityProvider:
    """
    Abstract base class for an identity provider.

    An identity provider tells the server which authentication plugins to make
    available to clients and how to retrieve users.
    """

    def get_plugins(self) -> Sequence[AuthPlugin]:
        return [NativePasswordAuthPlugin(), NoLoginAuthPlugin()]

    async def get_user(self, username: str) -> Optional[User]:
        return None

    def get_default_plugin(self) -> AuthPlugin:
        return self.get_plugins()[0]

    def get_plugin(self, name: str) -> Optional[AuthPlugin]:
        try:
            return next(p for p in self.get_plugins() if p.name == name)
        except StopIteration:
            return None


class SimpleIdentityProvider(IdentityProvider):
    """
    Simple identity provider implementation that naively accepts whatever username a client provides.
    """

    async def get_user(self, username: str) -> Optional[User]:
        return User(name=username, auth_plugin=NativePasswordAuthPlugin.name)
