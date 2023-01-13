import json
from importlib.resources import read_text

from jsonschema import Draft4Validator

validator = Draft4Validator(json.loads(read_text(__name__, "schema.json", encoding="utf-8")))
