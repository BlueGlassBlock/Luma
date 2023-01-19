from __future__ import annotations

from contextlib import contextmanager
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

    @contextmanager
    def activate_hook(self, pre: bool = True, post: bool = True, *args):
        if pre:
            for fn in self.pre:
                fn(*args)
        yield
        if post:
            for fn in self.post:
                fn(*args)


class HookManager:
    def __init__(self, ui: UI) -> None:
        self.targets: dict[str, HookTarget] = {}
        self.ui: UI = ui
        self.locked: bool = False

    def add_hook(self, target: str, func: Callable) -> None:
        stage = "core"
        if target.startswith(("pre_", "post_")):
            stage = target[:3]
            target = target[4:]
        hook_target = self.targets.setdefault(target, HookTarget(target))
        self.ui.echo(
            f"Adding [primary]{func.__module__}:{func.__qualname__}[/primary] "
            f"to [req]{stage}[/req] of [info]{target}[/info]",
            verbosity=2,
        )
        getattr(hook_target, stage).append(func)
