"""Benchmark: real client-server round trip with mysql.connector."""

import multiprocessing
import signal
import time

import mysql.connector
from mysql.connector.cursor import MySQLCursorPrepared

from mysql_mimic import MysqlServer, Session

NUM_ROWS = 10_000

ROWS = [
    (i, f"user_{i}", f"user_{i}@example.com", i * 1.5, i % 2 == 0)
    for i in range(NUM_ROWS)
]
COLUMNS = ["id", "name", "email", "score", "active"]


class BenchSession(Session):
    async def query(self, expression, sql, attrs):
        return ROWS, COLUMNS


def run_server(port_q):
    import asyncio

    async def _serve():
        server = MysqlServer(session_factory=BenchSession)
        await server.start_server(host="127.0.0.1", port=0)
        port = server._server.sockets[0].getsockname()[1]
        port_q.put(port)
        await server._server.serve_forever()

    asyncio.run(_serve())


def bench_text(port):
    conn = mysql.connector.connect(host="127.0.0.1", port=port, user="root")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bench")
    cursor.fetchall()
    times = []
    for _ in range(10):
        t0 = time.perf_counter()
        cursor.execute("SELECT * FROM bench")
        rows = cursor.fetchall()
        times.append(time.perf_counter() - t0)
    cursor.close()
    conn.close()
    return min(times), len(rows)


def bench_binary(port):
    conn = mysql.connector.connect(host="127.0.0.1", port=port, user="root")
    cursor = conn.cursor(cursor_class=MySQLCursorPrepared)
    cursor.execute("SELECT * FROM bench")
    cursor.fetchall()
    times = []
    for _ in range(10):
        t0 = time.perf_counter()
        cursor.execute("SELECT * FROM bench")
        rows = cursor.fetchall()
        times.append(time.perf_counter() - t0)
    cursor.close()
    conn.close()
    return min(times), len(rows)


def main():
    port_q = multiprocessing.Queue()
    proc = multiprocessing.Process(target=run_server, args=(port_q,), daemon=True)
    proc.start()
    port = port_q.get(timeout=10)

    for name, fn in [("text", bench_text), ("binary", bench_binary)]:
        best, count = fn(port)
        print(
            f"{name:>8}: {count:,} rows in {best*1000:.1f}ms ({count / best:,.0f} rows/s)"
        )

    proc.kill()


if __name__ == "__main__":
    main()
