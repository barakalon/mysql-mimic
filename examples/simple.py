import logging
import asyncio
from sqlglot.executor import execute

from mysql_mimic import MysqlServer, Session

SCHEMA = {
    "test": {
        "x": {
            "a": "INT",
        }
    }
}

TABLES = {
    "test": {
        "x": [
            {"a": 1},
            {"a": 2},
            {"a": 3},
        ]
    }
}


class MySession(Session):
    async def query(self, expression, sql, attrs):
        result = execute(expression, schema=SCHEMA, tables=TABLES)
        return result.rows, result.columns

    async def schema(self):
        return SCHEMA


async def main():
    logging.basicConfig(level=logging.DEBUG)
    server = MysqlServer(session_factory=MySession)
    await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
