"""Dynamic adapter loading.

Lookup order:
1. ~/.cohub/adapters/<name>.py  (user overrides first)
2. built-in cohub.adapters.<name>
"""
from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from . import paths


def load_adapter(name: str) -> ModuleType:
    # 1. User-defined adapter.
    user_path = paths.adapters_dir() / f"{name}.py"
    if user_path.exists():
        spec = importlib.util.spec_from_file_location(f"cohub_user_adapter_{name}", user_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load {user_path}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        return mod

    # 2. Built-in adapter.
    return importlib.import_module(f"cohub.adapters.{name}")
