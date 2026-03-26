# MySQL-Mimic

[![Tests](https://github.com/kelsin/mysql-mimic/actions/workflows/tests.yml/badge.svg)](https://github.com/kelsin/mysql-mimic/actions/workflows/tests.yml)

Pure-python implementation of the MySQL server [wire protocol](https://dev.mysql.com/doc/internals/en/client-server-protocol.html).

This can be used to create applications that act as a MySQL server.

## Installation

```shell
pip install mysql-mimic
```

## Usage

A minimal use case might look like this:

```python
import asyncio

from mysql_mimic import MysqlServer, Session


class MySession(Session):
    async def query(self, expression, sql, attrs):
        print(f"Parsed abstract syntax tree: {expression}")
        print(f"Original SQL string: {sql}")
        print(f"Query attributes: {sql}")
        print(f"Currently authenticated user: {self.username}")
        print(f"Currently selected database: {self.database}")
        return [("a", 1), ("b", 2)], ["col1", "col2"]

    async def schema(self):
        # Optionally provide the database schema.
        # This is used to serve INFORMATION_SCHEMA and SHOW queries.
        return {
            "table": {
                "col1": "TEXT",
                "col2": "INT",
            }
        }

if __name__ == "__main__":
    server = MysqlServer(session_factory=MySession)
    asyncio.run(server.serve_forever())
```

Using [sqlglot](https://github.com/tobymao/sqlglot), the abstract `Session` class handles queries to metadata, variables, etc. that many MySQL clients expect.

To bypass this default behavior, you can implement the [`mysql_mimic.session.BaseSession`](mysql_mimic/session.py) interface.

See [examples](./examples) for more examples.

## Authentication

MySQL-mimic has built in support for several standard MySQL authentication plugins:
- [mysql_native_password](https://dev.mysql.com/doc/refman/8.0/en/native-pluggable-authentication.html)
  - The client sends hashed passwords to the server, and the server stores hashed passwords. See the documentation for more details on how this works.
  - [example](examples/auth_native_password.py)
- [mysql_clear_password](https://dev.mysql.com/doc/refman/8.0/en/cleartext-pluggable-authentication.html)
  - The client sends passwords to the server as clear text, without hashing or encryption.
  - This is typically used as the client plugin for a custom server plugin. As such, MySQL-mimic provides an abstract class, [`mysql_mimic.auth.AbstractClearPasswordAuthPlugin`](mysql_mimic/auth.py), which can be extended.
  - [example](examples/auth_clear_password.py)
- [mysql_no_login](https://dev.mysql.com/doc/refman/8.0/en/no-login-pluggable-authentication.html)
  - The server prevents clients from directly authenticating as an account. See the documentation for relevant use cases.
- [authentication_kerberos](https://dev.mysql.com/doc/mysql-security-excerpt/8.0/en/kerberos-pluggable-authentication.html)
  - Kerberos uses tickets together with symmetric-key cryptography, enabling authentication without sending passwords over the network. Kerberos authentication supports userless and passwordless scenarios.


By default, a session naively accepts whatever username the client provides.

Plugins are provided to the server by implementing [`mysql_mimic.IdentityProvider`](mysql_mimic/auth.py), which configures all available plugins and a callback for fetching users.

Custom plugins can be created by extending [`mysql_mimic.auth.AuthPlugin`](mysql_mimic/auth.py).

## Performance

MySQL-Mimic uses [mypyc](https://mypyc.readthedocs.io/) to compile performance-critical modules to C extensions. When installed from a wheel (the default via `pip install`), the compiled extensions are included automatically.

| | rows/s | time | vs baseline |
|---|---|---|---|
| Pure Python | 122,000 | 82ms | 1.0x |
| mypyc compiled | 380,000 | 26ms | **3.1x** |

*Benchmark: 10,000 rows x 5 columns, real client-server over loopback. See `bench.py`.*

### Options

- `NO_MYPYC=1 pip install .` - Install without compiling C extensions (pure Python fallback)
- `MYPYC_OPT_LEVEL=2 pip install .` - Set mypyc optimization level (default: 3)

If installing from source without a C compiler, the package falls back to pure Python automatically.

## Development

You can install dependencies with `make deps`.

You can format your code with `make format`.

You can lint with `make lint`.

You can check type annotations with `make types`.

You can run tests with `make test`. This will build a coverage report in `./htmlcov/index.html`.

You can run all the checks with `make check`.

You can build a pip package with `make build`.
