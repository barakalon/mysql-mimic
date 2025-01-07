from __future__ import annotations

import asyncio
import inspect
import sys
from collections.abc import Iterator  # pylint: disable=import-error
import random
from typing import List, TypeVar, AsyncIterable, Iterable, AsyncIterator, cast
import string

from sqlglot import expressions as exp
from sqlglot.optimizer.scope import traverse_scope


T = TypeVar("T")

# MySQL Connector/J uses ASCII to decode nonce
SAFE_NONCE_CHARS = (string.ascii_letters + string.digits).encode()


class seq(Iterator):
    """Auto-incrementing sequence with an optional maximum size"""

    def __init__(self, size: int | None = None):
        self.size = size
        self.value = 0

    def __next__(self) -> int:
        value = self.value
        self.value = self.value + 1
        if self.size:
            self.value = self.value % self.size
        return value

    def reset(self) -> None:
        self.value = 0


def xor(a: bytes, b: bytes) -> bytes:
    # Fast XOR implementation, according to https://stackoverflow.com/questions/29408173/byte-operations-xor-in-python
    a, b = a[: len(b)], b[: len(a)]
    int_b = int.from_bytes(b, sys.byteorder)
    int_a = int.from_bytes(a, sys.byteorder)
    int_enc = int_b ^ int_a
    return int_enc.to_bytes(len(b), sys.byteorder)


def nonce(nbytes: int) -> bytes:
    return bytes(
        bytearray(
            [random.SystemRandom().choice(SAFE_NONCE_CHARS) for _ in range(nbytes)]
        )
    )


def find_tables(expression: exp.Expression) -> List[exp.Table]:
    """Find all tables in an expression"""
    if isinstance(
        expression, (exp.Select, exp.Subquery, exp.Union, exp.Except, exp.Intersect)
    ):
        return [
            source
            for scope in traverse_scope(expression)
            for source in scope.sources.values()
            if isinstance(source, exp.Table)
        ]
    return []


def find_dbs(expression: exp.Expression) -> List[str]:
    """Find all database names in an expression"""
    return [table.text("db") for table in find_tables(expression)]


def dict_depth(d: dict) -> int:
    """
    Get the nesting depth of a dictionary.
    For example:
        >>> dict_depth(None)
        0
        >>> dict_depth({})
        1
        >>> dict_depth({"a": "b"})
        1
        >>> dict_depth({"a": {}})
        2
        >>> dict_depth({"a": {"b": {}}})
        3
    Args:
        d (dict): dictionary
    Returns:
        int: depth
    """
    try:
        return 1 + dict_depth(next(iter(d.values())))
    except AttributeError:
        # d doesn't have attribute "values"
        return 0
    except StopIteration:
        # d.values() returns an empty sequence
        return 1


async def aiterate(iterable: AsyncIterable[T] | Iterable[T]) -> AsyncIterator[T]:
    """Iterate either an async iterable or a regular iterable"""
    if inspect.isasyncgen(iterable):
        async for item in iterable:
            yield item
    else:
        for item in cast(Iterable, iterable):
            yield item


async def cooperative_iterate(
    iterable: AsyncIterable[T], batch_size: int = 10_000
) -> AsyncIterator[T]:
    """
    Iterate an async iterable in a cooperative manner, yielding control back to the event loop every `batch_size` iterations
    """
    i = 0
    async for item in iterable:
        if i != 0 and i % batch_size == 0:
            await asyncio.sleep(0)
        yield item
        i += 1
