import sys
from collections.abc import Iterator
from typing import List, Any, Dict

from sqlglot import expressions as exp
from sqlglot.optimizer.scope import traverse_scope


class seq(Iterator):
    """Auto-incrementing sequence with an optional maximum size"""

    def __init__(self, size: int = None):
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


def find_tables(expression: exp.Expression) -> List[exp.Table]:
    return [
        source
        for scope in traverse_scope(expression)
        for source in scope.sources.values()
        if isinstance(source, exp.Table)
    ]


def find_dbs(expression: exp.Expression) -> List[str]:
    return [table.text("db") for table in find_tables(expression)]


def lower_case_identifiers(expression: exp.Expression) -> None:
    """Ensure all identifiers in `expression` are lower case, in-place"""
    expression.transform(_lower_case_identifiers, copy=False)


def _lower_case_identifiers(node: exp.Expression, *_: Any) -> exp.Expression:
    if isinstance(node, exp.Identifier):
        node.set("this", node.text("this").lower())
    return node


def dict_depth(d: Dict) -> int:
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
