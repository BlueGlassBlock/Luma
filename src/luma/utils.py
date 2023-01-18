from __future__ import annotations

import importlib
import subprocess
import sys
from contextlib import suppress
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


def guess_environment(project_root: Path) -> Literal["venv", "pdm", "poetry", None]:
    with suppress(Exception):
        build_backend: str = tomlkit.loads((project_root / "pyproject.toml").read_text(encoding="utf-8"))["build-system"]["build-backend"]  # type: ignore
        if "poetry" in build_backend and test_executable("poetry"):
            return "poetry"
        elif test_executable("pdm"):
            return "pdm"
    proc = subprocess.run(
        ["python", "-c", "import sys; print(sys.prefix); print(sys.base_prefix)"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
    )
    if not proc.returncode:
        output: None | str = None
        with suppress(UnicodeDecodeError):
            output = proc.stdout.decode()
        if not output:
            with suppress(UnicodeDecodeError):
                output = proc.stdout.decode("utf-8")
        if output:
            sys_prefix, sys_base_prefix = output.splitlines()
            return "venv" if sys_prefix != sys_base_prefix else None


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
