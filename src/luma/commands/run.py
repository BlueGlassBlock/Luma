from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import pkgutil
import signal
import subprocess
import sys
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Any, Callable, TypedDict

from luma.cli.command import Command
from luma.commands.utils import require_content
from luma.content import LumaConfig, SingleModule
from luma.core import Core
from luma.exceptions import LumaConfigError
from luma.term import UI
from luma.utils import load_from_string


def plugin(core: Core):
    core.register_command(RunCommand)


RUNNER_PATH = Path(Path(__file__).parent.parent, "runner.py").resolve().absolute()


@contextmanager
def handle_exc(msg: str, ui: UI):
    try:
        yield
    except Exception as e:
        ui.echo(f"[error]{msg}", err=True)
        raise LumaConfigError(e) from e


class LumaRuntimeContext(TypedDict):
    config_endpoints: dict[str, str]
    config_format: dict[str, Any]
    saya_modules: list[str]
    pre_run_hooks: list[str]
    core_hook: str


def get_import(func: Callable) -> str:
    return f"{func.__module__}:{func.__qualname__}"


class RunCommand(Command):
    name = "run"
    description = "Run your bot."

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--", dest="runtime_args", nargs="*", default=[])

    @require_content
    def handle(self, core: Core, config: LumaConfig, options: argparse.Namespace) -> None:
        runtime_args: list[str] = options.runtime_args
        require_modules = []
        for mod in config.modules:
            if isinstance(mod, SingleModule):
                require_modules.append(mod.endpoint)
                core.ui.echo(f"Adding module [info]{mod.endpoint}[/info]", verbosity=2)
            else:
                iter_pth = [mod.endpoint]
                with suppress(ImportError):
                    iter_pth = list(importlib.import_module(mod.endpoint).__path__)
                for mod_info in pkgutil.iter_modules(iter_pth):
                    if mod_info.name in mod.exclude:
                        continue
                    candidate_name = f"{mod.endpoint}.{mod_info.name}"
                    if importlib.util.find_spec(candidate_name) is None:
                        core.ui.echo(f"[warning]{candidate_name} is invalid module, skipping")
                        continue
                    require_modules.append(mod_info)
                    core.ui.echo(f"Adding module [info]{mod_info}[/info]")

        runtime_ctx: dict[str, Any] = {}

        # Set up runner core
        run_hook_target = core.hooks.targets.get("run")
        if not run_hook_target:
            msg = "Running target not configured!"
            raise LumaConfigError(msg)
        if len(run_hook_target.core) != 1:
            msg = f"Found {len(run_hook_target.core)} running target(s) instead of 1!"
            raise LumaConfigError(msg)
        core_hook: str = get_import(run_hook_target.core[0])

        # Set up pre-run hook
        pre_run_hooks: list[str] = []
        run_hook_target.warn_hooks(core.ui, post=True)
        for pre_fn in run_hook_target.pre:
            pre_fn_importer = get_import(pre_fn)
            try:
                load_from_string(pre_fn_importer)
            except Exception as exc:
                msg = f"Unable to import pre_run hook {pre_fn_importer}"
                raise LumaConfigError(msg) from exc

        runtime_ctx["luma"] = LumaRuntimeContext(
            config_endpoints=config.config.endpoints,
            config_format=config.config.format,
            saya_modules=require_modules,
            pre_run_hooks=pre_run_hooks,
            core_hook=core_hook,
        )

        # Run configuration hooks
        if config_target := core.hooks.targets.get("run_config"):
            for hook_fn in config_target.core:
                hook_fn(core, runtime_ctx, runtime_args)
            config_target.warn_hooks(core.ui, pre=True, post=True)

        # Invoke subprocess

        def forward_signal(sig, _) -> None:
            if sys.platform == "win32" and sig == signal.SIGINT:
                sig = signal.CTRL_C_EVENT
            process.send_signal(sig)

        handle_term = signal.signal(signal.SIGTERM, forward_signal)
        handle_int = signal.signal(signal.SIGINT, forward_signal)
        process = subprocess.Popen(
            core.python_cmd + [RUNNER_PATH, json.dumps(runtime_ctx, indent=None, ensure_ascii=True)] + runtime_args,
            shell=True,
            bufsize=0,
        )
        process.wait()
        signal.signal(signal.SIGTERM, handle_term)
        signal.signal(signal.SIGINT, handle_int)
        sys.exit(process.returncode)
