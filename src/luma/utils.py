from __future__ import annotations

import copy
import importlib
import subprocess
import sys
from contextlib import suppress
from dataclasses import field
from pathlib import Path
from typing import Any, Literal

import tomlkit


def is_pipx_env() -> bool:
    return ("pipx", "venvs") in Path(sys.prefix).parts


def test_executable(executable: str) -> bool:
    return (
        subprocess.run(
            [executable, "-V"],
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).returncode
        == 0
    )


def load_from_string(import_str: str) -> Any:
    module_str, _, attrs_str = import_str.partition(":")
    if not module_str or not attrs_str:
        message = f"Import string {import_str!r} must be in format <module>:<attribute>."
        raise ImportError(message)

    module = importlib.import_module(module_str)

    instance = module
    try:
        for attr_str in attrs_str.split("."):
            instance = getattr(instance, attr_str)
    except AttributeError as exc:
        message = f"Attribute {attrs_str!r} not found in module {module_str!r}."
        raise ImportError(message) from exc

    return instance


def cp_field(value) -> Any:
    return field(default_factory=lambda: copy.deepcopy(value))
