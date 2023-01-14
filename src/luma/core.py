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
import importlib.metadata as pkg_meta
import sys

from rich.traceback import Traceback

from luma import term
from luma.cli.command import Command, verbose_option
from luma.cli.utils import ErrorArgumentParser, LumaFormatter
from luma.exceptions import LumaArgumentError, LumaUsageError


class Core:
    def __init__(self) -> None:
        self.parser: ErrorArgumentParser = ErrorArgumentParser(
            "luma",
            description=term.style(__doc__, style="primary"),
            formatter_class=LumaFormatter,
        )
        self.subparsers = self.parser.add_subparsers(parser_class=argparse.ArgumentParser)
        self.ui: term.UI = term.UI()
        self.version = "0.1.0"
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
        self.parser.add_argument(
            "-c",
            "--config",
            help="Specify another config file path (env var: LUMA_CONFIG_FILE)",
        )
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

    def main(self, args: list[str] | None) -> None:
        args = args or sys.argv[1:]
        try:
            options = self.parser.parse_args(args)
        except LumaArgumentError as e:
            self.parser.error(str(e.__cause__))
        self.ui.set_verbosity(options.verbose)

        try:
            f = options.handler
        except AttributeError:
            self.parser.print_help(sys.stderr)
            sys.exit(1)
        else:
            try:
                f(self, options)
            except Exception as exc:
                should_show_tb = not isinstance(exc, LumaUsageError)
                if self.ui.verbosity > term.Verbosity.NORMAL and should_show_tb:
                    self.ui.echo(Traceback(), err=True)
                    sys.exit(1)
                self.ui.echo(
                    rf"[error]\[{exc.__class__.__name__}][/]: {exc}",
                    err=True,
                )
                if should_show_tb:
                    self.ui.echo(
                        "Add '-v' to see the detailed traceback",
                        style="warning",
                        err=True,
                    )
                sys.exit(1)


def main(args: list[str] | None = None) -> None:
    """The CLI entry function"""
    return Core().main(args)
