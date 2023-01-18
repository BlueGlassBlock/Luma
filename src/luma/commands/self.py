import argparse

from luma.cli.command import Command
from luma.core import Core


def plugin(core: Core):
    core.register_command(SelfCommand)


class SelfCommand(Command):
    name = "self"
    description = "Act with luma itself."

    def handle(self, core: Core, options: argparse.Namespace) -> None:
        ...
