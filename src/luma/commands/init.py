import argparse
from pathlib import Path

from luma.cli.command import Command
from luma.core import Core


def plugin(core: Core):
    core.register_command(InitCommand)


class InitCommand(Command):
    name = "init"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--non-interactive", default=False, help="Run in non-interactive mode.")

    def handle(self, core: Core, options: argparse.Namespace) -> None:
        core.ui.echo("[primary]Initializing [req]luma.toml")
        interactive: bool = not options.non_interactive
        if not interactive:
            core.ui.echo("[warning]Running in non-interactive mode.")
        file = Path.cwd() / "luma.toml"
        if file.exists():
            core.ui.echo("[warning][req]luma.toml[/req] already exists.")
            raise ValueError
