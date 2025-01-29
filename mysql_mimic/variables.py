from __future__ import annotations

import abc
import re
from datetime import timezone, timedelta
from functools import lru_cache
from typing import Any, Callable, Tuple, Iterator, MutableMapping

from mysql_mimic.charset import CharacterSet, Collation
from mysql_mimic.errors import MysqlError, ErrorCode


class Default: ...


VariableType = Callable[[Any], Any]
VariableSchema = Tuple[VariableType, Any, bool]


DEFAULT = Default()

SYSTEM_VARIABLES: dict[str, VariableSchema] = {
    # name: (type, default, dynamic)
    "auto_increment_increment": (int, 1, True),
    "autocommit": (bool, True, True),
    "character_set_client": (str, CharacterSet.utf8mb4.name, True),
    "character_set_connection": (str, CharacterSet.utf8mb4.name, True),
    "character_set_database": (str, CharacterSet.utf8mb4.name, True),
    "character_set_results": (str, CharacterSet.utf8mb4.name, True),
    "character_set_server": (str, CharacterSet.utf8mb4.name, True),
    "collation_connection": (str, Collation.utf8mb4_general_ci.name, True),
    "collation_database": (str, Collation.utf8mb4_general_ci.name, True),
    "collation_server": (str, Collation.utf8mb4_general_ci.name, True),
    "external_user": (str, "", False),
    "init_connect": (str, "", True),
    "interactive_timeout": (int, 28800, True),
    "license": (str, "MIT", False),
    "lower_case_table_names": (int, 0, True),
    "max_allowed_packet": (int, 67108864, True),
    "max_execution_time": (int, 0, True),
    "net_buffer_length": (int, 16384, True),
    "net_write_timeout": (int, 28800, True),
    "performance_schema": (bool, False, False),
    "sql_auto_is_null": (bool, False, True),
    "sql_mode": (str, "ANSI", True),
    "sql_select_limit": (int, None, True),
    "system_time_zone": (str, "UTC", False),
    "time_zone": (str, "UTC", True),
    "transaction_read_only": (bool, False, True),
    "transaction_isolation": (str, "READ-COMMITTED", True),
    "version": (str, "8.0.29", False),
    "version_comment": (str, "mysql-mimic", False),
    "wait_timeout": (int, 28800, True),
    "event_scheduler": (str, "OFF", True),
    "default_storage_engine": (str, "mysql-mimic", True),
    "default_tmp_storage_engine": (str, "mysql-mimic", True),
}


class Variables(abc.ABC, MutableMapping[str, Any]):
    """
    Abstract class for MySQL system variables.
    """

    def __init__(self) -> None:
        # Current variable values
        self._values: dict[str, Any] = {}

    def __getitem__(self, key: str) -> Any | None:
        try:
            return self.get_variable(key)
        except MysqlError as e:
            raise KeyError from e

    def __setitem__(self, key: str, value: Any) -> None:
        return self.set(key, value)

    def __delitem__(self, key: str) -> None:
        raise MysqlError(f"Cannot delete session variable {key}.")

    def __iter__(self) -> Iterator[str]:
        return self.schema.__iter__()

    def __len__(self) -> int:
        return len(self.schema)

    def get_schema(self, name: str) -> VariableSchema:
        schema = self.schema.get(name)
        if not schema:
            raise MysqlError(
                f"Unknown variable: {name}", code=ErrorCode.UNKNOWN_SYSTEM_VARIABLE
            )
        return schema

    def set(self, name: str, value: Any, force: bool = False) -> None:
        name = name.lower()
        type_, default, dynamic = self.get_schema(name)

        if not dynamic and not force:
            raise MysqlError(
                f"Variable is not dynamic: {name}", code=ErrorCode.PARSE_ERROR
            )

        if value is DEFAULT or value is None:
            self._values[name] = default
        else:
            self._values[name] = type_(value)

    def get_variable(self, name: str) -> Any | None:
        name = name.lower()
        if name in self._values:
            return self._values[name]
        _, default, _ = self.get_schema(name)

        return default

    def list(self) -> list[tuple[str, Any]]:
        return [(name, self.get(name)) for name in sorted(self.schema)]

    @property
    @abc.abstractmethod
    def schema(self) -> dict[str, VariableSchema]: ...


class GlobalVariables(Variables):
    def __init__(self, schema: dict[str, VariableSchema] | None = None):
        self._schema = schema or SYSTEM_VARIABLES
        super().__init__()

    @property
    def schema(self) -> dict[str, VariableSchema]:
        return self._schema


class SessionVariables(Variables):
    def __init__(self, global_variables: Variables):
        self.global_variables = global_variables
        super().__init__()

    @property
    def schema(self) -> dict[str, VariableSchema]:
        return self.global_variables.schema


RE_TIMEZONE = re.compile(r"^(?P<sign>[+-])(?P<hours>\d\d):(?P<minutes>\d\d)")


@lru_cache(maxsize=48)
def parse_timezone(tz: str) -> timezone:
    if tz.lower() == "utc":
        return timezone.utc
    match = RE_TIMEZONE.match(tz)
    if not match:
        raise MysqlError(msg=f"Invalid timezone: {tz}")
    offset = timedelta(
        hours=int(match.group("hours")), minutes=int(match.group("minutes"))
    )
    if match.group("sign") == "-":
        offset = offset * -1
    return timezone(offset)
