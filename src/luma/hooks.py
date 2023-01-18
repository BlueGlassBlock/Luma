from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from luma.term import UI


@dataclass
class HookReceipt:
    target: str
    callable: Callable


class HookManager:
    def __init__(self, ui: UI) -> None:
        self.record: dict[str, Callable] = {}
        self.ui: UI = ui
