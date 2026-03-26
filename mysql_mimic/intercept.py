from __future__ import annotations

from typing import Any

from sqlglot import expressions as exp

from mysql_mimic.errors import MysqlError, ErrorCode
from mysql_mimic.variables import DEFAULT

# Mapping of transaction characteristic from SET TRANSACTION statements to their corresponding system variable
TRANSACTION_CHARACTERISTICS = {
    "ISOLATION LEVEL REPEATABLE READ": ("transaction_isolation", "REPEATABLE-READ"),
    "ISOLATION LEVEL READ COMMITTED": ("transaction_isolation", "READ-COMMITTED"),
    "ISOLATION LEVEL READ UNCOMMITTED": ("transaction_isolation", "READ-UNCOMMITTED"),
    "ISOLATION LEVEL SERIALIZABLE": ("transaction_isolation", "SERIALIZABLE"),
    "READ WRITE": ("transaction_read_only", False),
    "READ ONLY": ("transaction_read_only", True),
}


def setitem_kind(setitem: exp.SetItem) -> str:
    kind = setitem.text("kind")
    if not kind:
        return "VARIABLE"

    if kind in {"GLOBAL", "PERSIST", "PERSIST_ONLY", "SESSION", "LOCAL"}:
        return "VARIABLE"

    return kind


def value_to_expression(value: Any) -> exp.Expression:
    if value is True:
        return exp.true()
    if value is False:
        return exp.false()
    if value is None:
        return exp.null()
    if isinstance(value, (int, float)):
        return exp.Literal.number(value)
    return exp.Literal.string(str(value))


def expression_to_value(expression: exp.Expression) -> Any:
    if expression == exp.true():
        return True
    if expression == exp.false():
        return False
    if expression == exp.null():
        return None
    if isinstance(expression, exp.Literal) and not expression.args.get("is_string"):
        try:
            return int(expression.this)
        except ValueError:
            return float(expression.this)
    if isinstance(expression, exp.Literal):
        return expression.name
    if expression.name == "DEFAULT":
        return DEFAULT
    if expression.name == "ON":
        return True
    if expression.name == "OFF":
        return False
    raise MysqlError(
        "Complex expressions in variables not supported yet",
        code=ErrorCode.NOT_SUPPORTED_YET,
    )
