import copy
import importlib.resources
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Union

from jsonschema import Draft202012Validator


def cp_field(value) -> Any:
    return field(default_factory=lambda: copy.deepcopy(value))


@dataclass
class Config:
    endpoints: Dict[str, str] = cp_field({})
    format: Dict[str, Any] = cp_field({})


@dataclass
class SingleModule:
    endpoint: str
    type: Literal["single"] = "single"


@dataclass
class MultiModule:
    endpoint: str
    type: Literal["multi"]
    exclude: List[str] = cp_field([])


@dataclass
class Component:
    endpoint: str
    args: Dict[str, Any] = cp_field({})


@dataclass
class Hook:
    endpoint: str
    target: str


@dataclass
class Metadata:
    version: str = "0.1"


@dataclass
class LumaConfig:
    metadata: Metadata
    config: Config = cp_field(Config())
    modules: List[Union[SingleModule, MultiModule]] = cp_field([])
    storage: Dict[str, str] = cp_field({})
    components: List[Component] = cp_field([])
    hooks: List[Hook] = cp_field([])


content_validator = Draft202012Validator(json.loads(importlib.resources.read_text(__name__, "schema.json", "utf-8")))


def load_content(config_file: Path) -> LumaConfig:
    import tomlkit
    from dacite.config import Config
    from dacite.core import from_dict

    with open(config_file, "r", encoding="utf-8") as fp:
        doc = tomlkit.load(fp)
        doc.pop("$schema", None)
    data = doc.unwrap()
    errs = list(content_validator.iter_errors(data))
    if errs:
        raise ValueError("Invalid `luma.toml`", errs)
    return from_dict(LumaConfig, data, Config(strict=True))
