"""动态加载 adapter。

查找顺序:
1. ~/.cohub/adapters/<name>.py  (用户自定义优先)
2. 内置 cohub.adapters.<name>
"""
from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

from . import paths


def load_adapter(name: str) -> ModuleType:
    # 1. 用户自定义
    user_path = paths.adapters_dir() / f"{name}.py"
    if user_path.exists():
        spec = importlib.util.spec_from_file_location(f"cohub_user_adapter_{name}", user_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"无法加载 {user_path}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        return mod

    # 2. 内置
    return importlib.import_module(f"cohub.adapters.{name}")
