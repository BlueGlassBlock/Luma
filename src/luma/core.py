r"""
 _
| |
| |    _   _ _ __ ___   __ _
| |   | | | | '_ ` _ \ / _` |
| |___| |_| | | | | | | (_| |
|______\__,_|_| |_| |_|\__,_|
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import importlib_metadata as pkg_meta
from rich.traceback import Traceback

from luma import term
from luma.cli.command import (
    Command,
    bot_path_option,
    environment_option,
    verbose_option,
)
from luma.cli.utils import ErrorArgumentParser, LumaFormatter
from luma.content import LumaConfig, load_content
from luma.exceptions import LumaArgumentError, LumaUsageError
from luma.utils import guess_environment


class Core:
    def __init__(self) -> None:
        self.parser: ErrorArgumentParser = ErrorArgumentParser(
            "luma",
            description=term.style(__doc__, style="primary"),
            formatter_class=LumaFormatter,
        )
        self.subparsers = self.parser.add_subparsers(parser_class=argparse.ArgumentParser)
        self.ui: term.UI = term.UI()
        self.config: LumaConfig | None = None
        self.environment_mgr: str | None = None
        self.version = pkg_meta.version("luma") or "development"
        self.tweak_parser()
        self.load_plugins()

    def tweak_parser(self):
        self.parser.add_argument(
            "-V",
            "--version",
            action="version",
            version="{}, version {}".format(
                term.style("Luma", style="bold"),
                term.style(self.version, style="success"),
            ),
            help="show the version and exit",
        )
        bot_path_option.add_to_parser(self.parser)
        environment_option.add_to_parser(self.parser)
        verbose_option.add_to_parser(self.parser)
        self.parser._positionals.title = "Commands"

    def register_command(self, command: type[Command]) -> None:
        command.register_to(self.subparsers)

    def load_plugins(self):
        for plugin in pkg_meta.entry_points(group="luma.plugin"):
            try:
                plugin.load()(self)
            except Exception as e:
                self.ui.echo(
                    f"Failed to load plugin {plugin.name}={plugin.value}: {e!r}",
                    style="error",
                    err=True,
                )

    def load_luma_file(self, config_file: Path):
        from tomlkit.exceptions import ParseError

        if config_file.exists():
            try:
                self.config = load_content(config_file)
                if (metadata_v := self.config.metadata.version) != "0.1":
                    self.ui.echo(f"[error]Incompatible [req]luma.toml[/req] version: {metadata_v}")
                    self.config = None
            except ParseError as e:
                self.ui.echo(f"[req]luma.toml[/req] is invalid TOML file: {e!r}", err=True)
            except ValueError as e:  # JSON Schema error
                self.ui.echo("[req]luma.toml[/req] is not valid", err=True)
                if self.ui.verbosity and "luma.toml" in str(e):
                    for exc in e.args[1]:
                        self.ui.echo(f"[error]{exc!r}", err=True)
            except Exception as e:
                self.ui.echo(f"[error]Error during loading [req]luma.toml[/req]: {e!r}", err=True)

    def main(self, args: list[str] | None) -> None:
        args = args or sys.argv[1:]
        try:
            options = self.parser.parse_args(args)
        except LumaArgumentError as e:
            self.parser.error(str(e.__cause__))
        self.ui.set_verbosity(options.verbose)

        project_root = Path(options.path or os.getenv("LUMA_PROJECT_ROOT") or os.getenv("PROJECT_ROOT") or os.getcwd())
        self.environment_mgr = options.environment_manager or guess_environment(project_root)
        if not self.environment_mgr:
            self.ui.echo("[error]Unable to determine environment manager!", err=True)
            sys.exit(1)
        self.ui.echo(f"[primary]Luma[/] is running with [req]{self.environment_mgr}", verbosity=1)
        self.load_luma_file(project_root / "luma.toml")

        try:
            f = options.handler
        except AttributeError:
            self.parser.print_help(sys.stderr)
            sys.exit(1)

        try:
            f(self, options)
        except Exception as exc:
            should_show_tb = not isinstance(exc, LumaUsageError)
            if self.ui.verbosity > term.Verbosity.NORMAL and should_show_tb:
                self.ui.echo(Traceback(), err=True)
                sys.exit(1)
            self.ui.echo(rf"[error]\[{exc.__class__.__name__}][/]: {exc}", err=True)
            if should_show_tb:
                self.ui.echo("Add '-v' to see the detailed traceback", style="warning", err=True)
            sys.exit(1)


def main(args: list[str] | None = None) -> None:
    """The CLI entry function"""
    return Core().main(args)
