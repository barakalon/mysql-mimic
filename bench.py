"""Benchmark: real client-server round trip with mysql.connector."""

import cProfile
import multiprocessing
import pstats
import signal
import time

import mysql.connector

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


def run_server(port_q, profile_path):
    import asyncio

    profiler = cProfile.Profile()

    def dump_profile(signum, frame):
        profiler.disable()
        profiler.dump_stats(profile_path)
        raise SystemExit(0)

    signal.signal(signal.SIGUSR1, dump_profile)

    async def _serve():
        server = MysqlServer(session_factory=BenchSession)
        await server.start_server(host="127.0.0.1", port=0)
        port = server._server.sockets[0].getsockname()[1]
        port_q.put(port)
        profiler.enable()
        await server._server.serve_forever()

    asyncio.run(_serve())


def main():
    profile_path = "/tmp/server_profile.prof"
    port_q = multiprocessing.Queue()
    proc = multiprocessing.Process(target=run_server, args=(port_q, profile_path), daemon=True)
    proc.start()
    port = port_q.get(timeout=10)

    conn = mysql.connector.connect(host="127.0.0.1", port=port, user="root")
    cursor = conn.cursor()

    # warmup
    cursor.execute("SELECT * FROM bench")
    cursor.fetchall()

    # timed runs
    times = []
    for _ in range(10):
        t0 = time.perf_counter()
        cursor.execute("SELECT * FROM bench")
        rows = cursor.fetchall()
        times.append(time.perf_counter() - t0)

    # profiled client run
    client_profile_path = "/tmp/client_profile.prof"
    profiler = cProfile.Profile()
    profiler.enable()
    cursor.execute("SELECT * FROM bench")
    cursor.fetchall()
    profiler.disable()
    profiler.dump_stats(client_profile_path)

    cursor.close()
    conn.close()

    # signal server to dump profile and exit
    import os
    os.kill(proc.pid, signal.SIGUSR1)
    proc.join(timeout=5)

    best = min(times)
    count = len(rows)
    print(f"{count:,} rows in {best*1000:.1f}ms ({count / best:,.0f} rows/s)\n")

    # print client profile
    stats = pstats.Stats(client_profile_path)
    stats.sort_stats("tottime")
    print("=== Client profile: top 30 by total time ===")
    stats.print_stats(30)


if __name__ == "__main__":
    main()
