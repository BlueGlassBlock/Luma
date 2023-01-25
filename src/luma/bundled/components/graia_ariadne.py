from dataclasses import dataclass
from typing import Any, Dict, List, Union, cast

from luma.core import Core
from luma.exceptions import LumaConfigError
from luma.utils import cp_field


def initialize(core: Core):
    core.component_handlers["graia-ariadne"] = handler


called: bool = False


def handler(core: Core, kwargs: Dict[str, Any]):
    global called
    if called:
        raise LumaConfigError("Ariadne is specified multiple times.")
    called = True
    if kwargs["__sub__"]:
        raise LumaConfigError("Ariadne don't have sub-component!")
    core.component_handlers["launart"](core, {"__sub__": "graia.ariadne.service:ElizabethService"})
    core.hooks.add_hook("pre_run", conf_ariadne, exclusive=True)


@dataclass
class WebsocketClientConfig:
    """Websocket 客户端配置"""

    host: str = "http://localhost:8080"
    """mirai-api-http 的 Endpoint"""


@dataclass
class WebsocketServerConfig:
    """Websocket 服务器配置"""

    path: str = "/"
    """服务的 Endpoint"""
    params: Dict[str, str] = cp_field({})
    """用于验证的参数"""
    headers: Dict[str, str] = cp_field({})
    """用于验证的请求头"""


@dataclass
class HttpClientConfig:
    """HTTP 客户端配置"""

    host: str = "http://localhost:8080"
    """mirai-api-http 的 Endpoint"""


@dataclass
class HttpServerConfig:
    """HTTP 服务器配置"""

    path: str = "/"
    """服务的 Endpoint """

    headers: Dict[str, str] = cp_field({})
    """用于验证的请求头"""


@dataclass
class AccountCredential:
    account: int
    verify_key: str
    http_client: Union[HttpClientConfig, None] = None
    websocket_client: Union[WebsocketClientConfig, None] = None
    http_server: Union[HttpServerConfig, None] = None
    websocket_server: Union[WebsocketServerConfig, None] = None


class AriadneCredential:
    accounts: List[AccountCredential]


def inject_launart(_, ctx):
    from launart import Launart

    ctx["launart"] = Launart()


def conf_ariadne(core: Core, runtime_ctx):
    from dataclasses import asdict

    from graia.ariadne.app import Ariadne
    from graia.ariadne.connection.config import from_obj
    from kayaku import config, create

    global AriadneCredential

    AriadneCredential = config("graia.ariadne.credential")(AriadneCredential)

    Ariadne.launch_manager = runtime_ctx["launart"]
    for account in create(AriadneCredential).accounts:
        from_obj(cast(Any, asdict(account, dict_factory=lambda t: {k: v for k, v in dict(t).items() if v is not None})))
        core.ui.echo(f"[info]Added account: [req]{account.account}[/req]")
    Ariadne._patch_launch_manager()
