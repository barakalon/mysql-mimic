"""Verify that mysql-mimic was installed with mypyc-compiled extensions."""

import importlib.util
import sys

# Find the installed package location via importlib (works across all platforms)
spec = importlib.util.find_spec("mysql_mimic")
if spec is None or spec.submodule_search_locations is None:
    print("ERROR: mysql_mimic package not found", file=sys.stderr)
    sys.exit(1)

pkgdir = spec.submodule_search_locations[0]
print(f"Package directory: {pkgdir}")

# Check for compiled extensions — mypyc produces .so (Unix) or .pyd (Windows)
import pathlib

exts = list(pathlib.Path(pkgdir).glob("*.so")) + list(
    pathlib.Path(pkgdir).glob("*.pyd")
)
print(f"Compiled extensions: {[e.name for e in exts]}")

if not exts:
    print("FAIL: no compiled extensions found — wheel is pure Python", file=sys.stderr)
    sys.exit(1)

print(f"PASS: found {len(exts)} mypyc-compiled extension(s)")
