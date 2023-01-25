from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from luma.term import UI
from luma.utils import cp_field


@dataclass
class HookTarget:
    name: str
    pre: list[Callable] = cp_field([])
    core: list[Callable] = cp_field([])
    post: list[Callable] = cp_field([])

    def warn_hooks(self, ui: UI, pre: bool = False, post: bool = False) -> None:
        if pre and self.pre:
            for pre_fn in self.pre:
                ui.echo(f"[warning]pre_{self.name} hook {pre_fn.__module__}:{pre_fn.__qualname__} is not invoked!")
        if post and self.post:
            for post_fn in self.post:
                ui.echo(f"[warning]post{self.name} hook {post_fn.__module__}:{post_fn.__qualname__} is not invoked!")


class HookManager:
    def __init__(self, ui: UI) -> None:
        self.targets: dict[str, HookTarget] = {}
        self.ui: UI = ui
        self.locked: bool = False

    def add_hook(self, target: str, func: Callable, exclusive: bool = False) -> None:
        stage = "core"
        if target.startswith(("pre_", "post_")):
            stage = target[:3]
            target = target[4:]
        hook_target = self.targets.setdefault(target, HookTarget(target))
        target_fns: list[Callable] = getattr(hook_target, stage)
        if func in target_fns and exclusive:
            return
        target_fns.append(func)
        self.ui.echo(
            f"Adding [primary]{func.__module__}:{func.__qualname__}[/primary] "
            f"to [req]{stage}[/req] of [info]{target}[/info]",
            verbosity=2,
        )
