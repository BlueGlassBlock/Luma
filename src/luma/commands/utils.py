import functools
from typing import Any, Callable, TypeVar

from luma.content import LumaConfig
from luma.core import Core
from luma.exceptions import LumaConfigError

_T = TypeVar("_T")


def require_content(meth: Callable[[_T, Core, LumaConfig, Any], Any]) -> Callable[[_T, Core, Any], Any]:
    @functools.wraps(meth)
    def wrapper(self: _T, core: Core, namespace: Any) -> Any:
        if core.config is None:
            raise LumaConfigError("This command requires valid `luma.toml`")
        return meth(self, core, core.config, namespace)

    return wrapper
