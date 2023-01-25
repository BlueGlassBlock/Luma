from __future__ import annotations

import argparse
import importlib
import importlib.util
import pkgutil
from contextlib import contextmanager, suppress
from typing import Any

from luma.cli.command import Command
from luma.commands.utils import require_content
from luma.content import LumaConfig, SingleModule
from luma.core import Core
from luma.exceptions import LumaConfigError
from luma.term import UI


def plugin(core: Core):
    core.register_command(RunCommand)


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

    @require_content
    def handle(self, core: Core, config: LumaConfig, options: argparse.Namespace) -> None:
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
                    require_modules.append(candidate_name)
                    core.ui.echo(f"Adding module [info]{candidate_name}[/info]")

        runtime_ctx: dict[str, Any] = {}

        # Set up runner core
        run_hook_target = core.hooks.targets.get("run")
        if not run_hook_target:
            msg = "Running target not configured!"
            raise LumaConfigError(msg)
        if len(run_hook_target.core) != 1:
            msg = f"Found {len(run_hook_target.core)} running target(s) instead of 1!"
            raise LumaConfigError(msg)

        # Run configuration hooks
        if config_target := core.hooks.targets.get("run_config"):
            config_target.warn_hooks(core.ui, pre=True, post=True)
            for hook_fn in config_target.core:
                hook_fn(core, runtime_ctx)

        # Kayaku startup
        import kayaku
        import kayaku.pretty

        kayaku.initialize(config.config.endpoints, kayaku.pretty.Prettifier(**config.config.format))

        # Import Saya modules
        import creart
        from graia.saya import Saya

        saya: Saya = runtime_ctx.get("saya") or creart.it(Saya)
        runtime_ctx["saya"] = saya
        with saya.module_context():
            for mod in require_modules:
                saya.require(mod)

        # Invoke run hook
        run_hook_target.warn_hooks(core.ui, post=True)
        for pre_fn in run_hook_target.pre:
            pre_fn(core, runtime_ctx)

        # Kayaku bootstrap
        kayaku.bootstrap()

        run_hook_target.core[0](core, runtime_ctx)
