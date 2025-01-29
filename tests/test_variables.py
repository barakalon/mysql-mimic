from datetime import timezone, timedelta
from typing import Dict

import pytest

from mysql_mimic.errors import MysqlError
from mysql_mimic.variables import (
    parse_timezone,
    Variables,
    VariableSchema,
)


class TestVars(Variables):

    @property
    def schema(self) -> Dict[str, VariableSchema]:
        return {"foo": (str, "bar", True)}


def test_parse_timezone() -> None:
    assert timezone(timedelta()) == parse_timezone("UTC")
    assert timezone(timedelta()) == parse_timezone("+00:00")
    assert timezone(timedelta(hours=1)) == parse_timezone("+01:00")
    assert timezone(timedelta(hours=-1)) == parse_timezone("-01:00")

    # Implicitly test cache
    assert timezone(timedelta(hours=-1)) == parse_timezone("-01:00")

    with pytest.raises(MysqlError):
        parse_timezone("whoops")


def test_variable_mapping() -> None:
    test_vars = TestVars()
    assert test_vars
    assert len(test_vars) == 1

    assert test_vars.get_variable("foo") == "bar"
    assert test_vars["foo"] == "bar"

    test_vars["foo"] = "hello"
    assert test_vars.get_variable("foo") == "hello"
    assert test_vars["foo"] == "hello"

    with pytest.raises(KeyError):
        assert test_vars["world"]

    with pytest.raises(MysqlError):
        test_vars["world"] = "hello"
