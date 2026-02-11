"""
Compatibility layer: load shared-lib (hyphen) as shared_lib (underscore).
Python does not allow hyphens in module names.
"""

import sys
import importlib.util
from pathlib import Path

_here = Path(__file__).parent
_shared_lib_path = _here.parent / "shared-lib"

if not _shared_lib_path.is_dir():
    raise ImportError(f"shared-lib directory not found: {_shared_lib_path}")

# Load each module from shared-lib into shared_lib.*
for _name in ("config", "models", "utils"):
    _file = _shared_lib_path / f"{_name}.py"
    if not _file.exists():
        continue
    _spec = importlib.util.spec_from_file_location(f"shared_lib.{_name}", _file)
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules[f"shared_lib.{_name}"] = _mod
    _spec.loader.exec_module(_mod)
    setattr(sys.modules[__name__], _name, _mod)

__all__ = ["models", "config", "utils"]
