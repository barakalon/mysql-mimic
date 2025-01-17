from typing import Any, Dict, Mapping, Iterator
from datetime import datetime


class Functions(Mapping):
    def __init__(self, functions: Dict[str, Any]):
        self._function_mapping = functions

    def __getitem__(self, key: str) -> Any:
        return self._function_mapping.get(key)

    def __iter__(self) -> Iterator[str]:
        return iter(self._function_mapping)

    def __len__(self) -> int:
        return len(self._function_mapping)


class MySQLDatetimeFunctions(Functions):
    def __init__(self, timestamp: datetime):
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
        super().__init__(functions)
