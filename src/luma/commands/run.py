from __future__ import annotations

import argparse
import json
import subprocess
from contextlib import contextmanager
from functools import partial
from pathlib import Path

import tomlkit

from luma.cli.command import Command
from luma.commands.utils import require_content
from luma.content import LumaConfig
from luma.core import Core
from luma.exceptions import LumaConfigError
from luma.term import UI


def plugin(core: Core):
    core.register_command(RunCommand)


PATH_RETRIEVE_COMMAND = [
    "python",
    "-c",
    "import sys; import json; print(json.dumps(sys.path, indent=4, ensure_ascii=True))",
]

BASE_RUN_COMMAND = ["python", Path(Path(__file__).parent, "luma_runner.py").resolve().absolute()]


@contextmanager
def handle_exc(msg: str, ui: UI):
    try:
        yield
    except Exception as e:
        ui.echo(f"[error]{msg}", err=True)
        raise LumaConfigError(e) from e


def retrieve_path(package_manager: str, ui: UI) -> list[str]:
    with handle_exc("Unable to retrieve target [req]sys.path[/req]", ui):
        proc = subprocess.run(
            [package_manager, "run"] + PATH_RETRIEVE_COMMAND, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        proc.check_returncode()
        return json.loads(proc.stdout.decode())


class RunCommand(Command):
    name = "run"
    description = "Run your bot."

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        pass

    # @require_content
    def handle(self, core: Core, options: argparse.Namespace) -> None:
        ...
