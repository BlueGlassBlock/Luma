from asyncio import AbstractEventLoop
from typing import TYPE_CHECKING, Any, Dict

from luma.core import Core
from luma.exceptions import LumaConfigError
from luma.utils import load_from_string

if TYPE_CHECKING:
    from launart import Launchable


def initialize(core: Core):
    core.component_handlers["launart"] = handler


pending_components: "list[Launchable]" = []


def handler(core: Core, kwargs: Dict[str, Any]):
    from launart import Launchable

    if kwargs["__sub__"] is None:
        raise LumaConfigError("Sub component is required to add!")
    core.hooks.add_hook("pre_run", add_launart_component, exclusive=True)
    core.hooks.add_hook("run_config", inject_launart, exclusive=True)
    core.hooks.add_hook("run", run, exclusive=True)
    component_cls = load_from_string(kwargs.pop("__sub__"))
    component = component_cls(**kwargs)  # TODO: Parse kwargs for accurate init
    if not isinstance(component, Launchable):
        msg = f"{component!r} is not launchable!"
        raise LumaConfigError(msg)
    pending_components.append(component)


def inject_launart(_, ctx):
    from launart import Launart

    ctx["launart"] = Launart()


def add_launart_component(core: Core, ctx):
    from launart import Launart

    launart: Launart = ctx["launart"]
    for component in pending_components:
        launart.add_launchable(component)
        core.ui.echo(f"[info]Adding launart component: [req]{component.id}[/req]")


def run(_, ctx):
    import creart
    from launart import Launart

    launart: Launart = ctx["launart"]
    launart.launch_blocking(loop=creart.it(AbstractEventLoop))  # TODO: signal
