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


RUNNER_PATH = Path(Path(__file__).parent, "luma_runner.py").resolve().absolute()


@contextmanager
def handle_exc(msg: str, ui: UI):
    try:
        yield
    except Exception as e:
        ui.echo(f"[error]{msg}", err=True)
        raise LumaConfigError(e) from e


class RunCommand(Command):
    name = "run"
    description = "Run your bot."

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        pass

    # @require_content
    def handle(self, core: Core, options: argparse.Namespace) -> None:
        ...
