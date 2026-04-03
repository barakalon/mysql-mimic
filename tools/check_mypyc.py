"""Verify that mysql-mimic was installed with mypyc-compiled extensions."""

import importlib
import importlib.util
import io
import pathlib
import sys

# Find the installed package location via importlib (works across all platforms)
spec = importlib.util.find_spec("mysql_mimic")
if spec is None or spec.submodule_search_locations is None:
    print("ERROR: mysql_mimic package not found", file=sys.stderr)
    sys.exit(1)

# These imports must come after the spec check so the "package not found"
# error path fires before Python tries to import any mysql_mimic submodule.
# _read_params is intentionally imported despite its private name — it is
# the real parsing entry-point for prepared-statement parameters and the
# most direct way to smoke-test NullBitmap byte-boundary behaviour on a
# compiled wheel.
from mysql_mimic.charset import CharacterSet
from mysql_mimic.packets import _read_params, make_binary_resultrow
from mysql_mimic.results import NullBitmap, ResultColumn
from mysql_mimic.types import Capabilities, ColumnType, str_len, uint_1

pkgdir = spec.submodule_search_locations[0]
print(f"Package directory: {pkgdir}")

EXPECTED_COMPILED_MODULES = [
    "mysql_mimic.charset",
    "mysql_mimic.packets",
    "mysql_mimic.results",
    "mysql_mimic.stream",
    "mysql_mimic.types",
]

exts = list(pathlib.Path(pkgdir).glob("*.so")) + list(
    pathlib.Path(pkgdir).glob("*.pyd")
)
print(f"Compiled extensions: {[e.name for e in exts]}")

if not exts:
    print("FAIL: no compiled extensions found — wheel is pure Python", file=sys.stderr)
    sys.exit(1)


def assert_expected_modules_are_compiled() -> None:
    for module_name in EXPECTED_COMPILED_MODULES:
        module = importlib.import_module(module_name)
        module_file = getattr(module, "__file__", None)

        if module_file is None:
            raise AssertionError(f"Module {module_name} has no __file__")

        suffix = pathlib.Path(module_file).suffix.lower()
        if suffix not in {".so", ".pyd"}:
            raise AssertionError(
                f"Module {module_name} was not imported from a compiled extension: {module_file}"
            )


def assert_null_bitmap_boundaries() -> None:
    bitmap = NullBitmap.new(8, offset=2)
    for bit in (0, 5, 6, 7):
        bitmap.flip(bit)

    if bytes(bitmap) != b"\x84\x03":
        raise AssertionError(f"Unexpected boundary bitmap bytes: {bytes(bitmap)!r}")


def assert_binary_resultrow_boundaries() -> None:
    row = (None, "a", "b", "c", "d", None, None)
    columns = [ResultColumn(name=str(i), type=ColumnType.STRING) for i in range(7)]
    encoded = make_binary_resultrow(row, columns)

    if encoded != b"\x00\x84\x01\x01a\x01b\x01c\x01d":
        raise AssertionError(f"Unexpected binary result row bytes: {encoded!r}")


def assert_read_params_boundaries() -> None:
    payload = b"".join(
        [
            b"\x21\x01",
            uint_1(1),
            *([uint_1(ColumnType.STRING), uint_1(0)] * 9),
            str_len(b"hi"),
            str_len(b"there"),
            str_len(b"friend"),
            str_len(b"from"),
            str_len(b"the"),
            str_len(b"bitmap"),
        ]
    )

    params = _read_params(Capabilities(0), CharacterSet.utf8mb4, io.BytesIO(payload), 9)
    expected = [
        ("", None),
        ("", "hi"),
        ("", "there"),
        ("", "friend"),
        ("", "from"),
        ("", None),
        ("", "the"),
        ("", "bitmap"),
        ("", None),
    ]

    if params != expected:
        raise AssertionError(f"Unexpected prepared params: {params!r}")


assert_expected_modules_are_compiled()
assert_null_bitmap_boundaries()
assert_binary_resultrow_boundaries()
assert_read_params_boundaries()
print(f"PASS: found {len(exts)} mypyc-compiled extension(s); smoke tests passed")
