from __future__ import annotations

import abc
import argparse

import luma.core
from luma.cli.utils import LumaFormatter, Option

verbose_option = Option(
    "-v",
    "--verbose",
    action="count",
    default=0,
    help="-v for detailed output and -vv for more detailed",
)

bot_path_option = Option(
    "-p",
    "--path",
    help="Specify bot directory (env var: LUMA_PROJECT_ROOT / PROJECT_ROOT)",
)

python_option = Option("-py", "--python-path", help="Specify Python path")


class Command(abc.ABC):
    """A CLI subcommand"""

    # The subcommand's name
    name: str | None = None
    # The subcommand's help string, if not given, __doc__ will be used.
    description: str | None = None
    # A list of pre-defined options which will be loaded on initializing
    # Rewrite this if you don't want the default ones
    arguments: list[Option] = [verbose_option]

    def __init__(self, parser: argparse.ArgumentParser) -> None:
        for arg in self.arguments:
            arg.add_to_parser(parser)
        self.add_arguments(parser)

    @classmethod
    def register_to(cls, subparsers: argparse._SubParsersAction, name: str | None = None, **kwargs) -> None:
        """Register a subcommand to the subparsers,
        with an optional name of the subcommand.
        """
        help_text = cls.description or cls.__doc__
        name = name or cls.name or ""
        # Remove the existing subparser as it will raises an error on Python 3.11+
        subparsers._name_parser_map.pop(name, None)
        subactions = subparsers._get_subactions()
        subactions[:] = [action for action in subactions if action.dest != name]
        parser = subparsers.add_parser(
            name,
            description=help_text,
            help=help_text,
            formatter_class=LumaFormatter,
            **kwargs,
        )
        command = cls(parser)

        # Add necessary options
        bot_path_option.add_to_parser(parser)
        python_option.add_to_parser(parser)

        parser.set_defaults(handler=command.handle)

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Manipulate the argument parser to add more arguments"""
        pass

    @abc.abstractmethod
    def handle(self, core: luma.core.Core, options: argparse.Namespace) -> None:
        """The command handler function.
        :param options: the parsed Namespace object
        """
        raise NotImplementedError
