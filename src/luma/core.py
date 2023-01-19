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
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Literal

import importlib_metadata as pkg_meta
from rich.markup import escape
from rich.traceback import Traceback
from typing_extensions import Self

from luma import term
from luma.cli.command import (
    Command,
    bot_path_option,
    environment_option,
    verbose_option,
)
from luma.cli.utils import ErrorArgumentParser, LumaFormatter
from luma.content import Component, LumaConfig, load_content
from luma.exceptions import LumaArgumentError, LumaConfigError, LumaError
from luma.hook import HookManager
from luma.utils import guess_environment, load_from_string


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
        self.environment_mgr: str = ""
        self.version: str = pkg_meta.version("luma") or "development"
        self.hooks: HookManager = HookManager(self.ui)
        self.component_handlers: dict[str, Callable[[Self, dict[str, Any]], None]] = {}
        self.called_components: set[str] = set()
        self._tweak_parser()
        self._load_plugins()

    def _tweak_parser(self):
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

    def _load_plugins(self):
        for plugin in pkg_meta.entry_points(group="luma.plugin"):
            try:
                plugin.load()(self)
            except Exception as e:
                self.ui.echo(
                    f"Failed to load plugin {plugin.name}={plugin.value}: {e!r}",
                    style="error",
                    err=True,
                )

    def _load_luma_file(self, config_file: Path) -> None:
        from tomlkit.exceptions import ParseError

        if config_file.exists():
            try:
                self.config = load_content(config_file)
                if (metadata_v := self.config.metadata.version) != "0.1":
                    self.ui.echo(f"[error]Incompatible [req]luma.toml[/req] version: {metadata_v}")
                    self.config = None
                    return
            except ParseError as e:
                self.ui.echo(f"[req]luma.toml[/req] is invalid TOML file: {e!r}", err=True)
            except ValueError as e:  # JSON Schema error
                self.ui.echo("[req]luma.toml[/req] is not valid", err=True)
                if self.ui.verbosity and "luma.toml" in str(e):
                    for exc in e.args[1]:
                        self.ui.echo(f"[error]{exc!r}", err=True)
            except Exception as e:
                self.ui.echo(f"[error]Error during loading [req]luma.toml[/req]: {e!r}", err=True)

    def register_command(self, command: type[Command]) -> None:
        self.ui.echo(f"Registering command [info]{command.name}[/info]", verbosity=2)
        command.register_to(self.subparsers)

    @property
    def python_cmd(self) -> list[str]:
        return ["python"] if self.environment_mgr == "local" else [self.environment_mgr, "run", "python"]

    def exec_script(self, script: str) -> str:
        proc = subprocess.run(self.python_cmd + ["-c", script, "-X", "utf8"], stdout=subprocess.PIPE, shell=True)
        proc.check_returncode()
        self.ui.echo(f"Run Python script: [primary]{escape(script)}[/]", verbosity=2)
        return proc.stdout.decode("utf-8")

    def _propagate_interpreter_path(self):
        import site

        self.ui.echo("[info]Propagating [req]sys.path[/req] with target interpreter!", verbosity=1)
        pre_sys_path = set(sys.path)
        site_prefixes = self.exec_script("import site; [print(p) for p in site.PREFIXES]").splitlines()
        post_sys_path = site.addsitepackages(pre_sys_path.copy(), prefixes=site_prefixes)
        if post_sys_path:
            for extra_pth in post_sys_path - pre_sys_path:
                self.ui.echo(f"Added [info]{extra_pth}[/] to [req]sys.path[/].", verbosity=2)

    def _load_components(self) -> None:
        for ep in pkg_meta.entry_points(group="luma.component"):
            # NOTE: Here we assume EVERY component is CORRECTLY implemented.
            ep.load()(self)

    def _call_component(self, component: Component) -> None:
        name, _, sub = component.endpoint.partition(":")
        try:
            handler = self.component_handlers[name]
        except KeyError as exc:
            msg = f"Component {name} does not exist!"
            raise LumaConfigError(msg) from exc
        args = {"__sub__": sub or None, **component.args}
        handler(self, args)
        self.called_components.union((name, component.endpoint))

    def _bootstrap_luma_file(self):
        if not self.config:
            return
        for component in self.config.components:
            self._call_component(component)
        for hook in self.config.hooks:
            hook_fn = load_from_string(hook.endpoint)
            if not callable(hook_fn):
                self.ui.echo(f"[error][info]{hook.endpoint}[/info] is not callable, skipping", err=True)
                continue
            self.hooks.add_hook(hook.target, load_from_string(hook.endpoint))

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

        project_root = Path(options.path or os.getenv("LUMA_PROJECT_ROOT") or os.getenv("PROJECT_ROOT") or os.getcwd())
        self.environment_mgr = options.environment_manager or guess_environment(project_root)
        if not self.environment_mgr:
            self.ui.echo("[error]Unable to determine environment manager!", err=True)
            sys.exit(1)
        self.ui.echo(f"[primary]Luma[/] is running with [req]{self.environment_mgr}", verbosity=1)

        try:
            self._load_luma_file(project_root / "luma.toml")
            self._propagate_interpreter_path()
            self._load_components()
            self._bootstrap_luma_file()
            f(self, options)
        except Exception as exc:
            should_show_tb = not isinstance(exc, LumaError)
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
