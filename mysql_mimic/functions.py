from typing import Any, Mapping, Callable
from datetime import datetime

Functions = Mapping[str, Callable[[], Any]]


def mysql_datetime_function_mapping(timestamp: datetime) -> Functions:
    functions = {
        "NOW": lambda: timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        "CURDATE": lambda: timestamp.strftime("%Y-%m-%d"),
        "CURTIME": lambda: timestamp.strftime("%H:%M:%S"),
    }
    functions.update(
        {
            "CURRENT_TIMESTAMP": functions["NOW"],
            "LOCALTIME": functions["NOW"],
            "LOCALTIMESTAMP": functions["NOW"],
            "CURRENT_DATE": functions["CURDATE"],
            "CURRENT_TIME": functions["CURTIME"],
        }
    )
    return functions
