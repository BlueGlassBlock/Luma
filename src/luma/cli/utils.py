"""CLI utils"""

from __future__ import annotations

import argparse
from argparse import Action, _ArgumentGroup
from typing import Any, Callable, Iterable, overload

from luma import term
from luma.exceptions import LumaArgumentError


class ErrorArgumentParser(argparse.ArgumentParser):
    """A subclass of argparse.ArgumentParser that raises
    parsing error rather than exiting.

    This does the same as passing exit_on_error=False on Python 3.9+
    """

    def _parse_known_args(
        self, arg_strings: list[str], namespace: argparse.Namespace
    ) -> tuple[argparse.Namespace, list[str]]:
        try:
            return super()._parse_known_args(arg_strings, namespace)
        except argparse.ArgumentError as e:
            # We raise a dedicated error to avoid being caught by the caller
            raise LumaArgumentError(e) from e


class LumaFormatter(argparse.RawDescriptionHelpFormatter):
    def start_section(self, heading: str | None) -> None:
        return super().start_section(term.style(heading.title() if heading else "", style="warning"))

    def _format_usage(
        self,
        usage: str | None,
        actions: Iterable[Action],
        groups: Iterable[_ArgumentGroup],
        prefix: str | None,
    ) -> str:
        if prefix is None:
            prefix = "Usage: "
        result = super()._format_usage(usage, actions, groups, prefix)
        if prefix:
            return result.replace(prefix, term.style(prefix, style="warning"))
        return result

    def _format_action(self, action: Action) -> str:
        # determine the required width and the entry label
        help_position = min(self._action_max_length + 2, self._max_help_position)
        help_width = max(self._width - help_position, 11)
        action_width = help_position - self._current_indent - 2
        action_header = self._format_action_invocation(action)

        # no help; start on same line and add a final newline
        if not action.help:
            action_header = f"{' ':{self._current_indent}}{action_header}\n"
            parts = [term.style(action_header, style="primary")]
        else:

            # short action name; start on the same line and pad two spaces
            if len(action_header) <= action_width:
                action_header = f"{' ':{self._current_indent}}{action_header:<{action_width}}  "
                indent_first = 0

            # long action name; start on the next line
            else:
                action_header = f"{' ':{self._current_indent}}{action_header}\n"
                indent_first = help_position

            # add lines of help text
            help_text = self._expand_help(action)
            help_lines = self._split_lines(help_text, help_width)

            parts = [
                term.style(action_header, style="primary"),
                f"{' ':{indent_first}}{help_lines[0]}\n",
                *(f"{' ':{help_position}}{line}\n" for line in help_lines[1:]),
            ]

        # if there are any sub-actions, add their help as well
        parts.extend(self._format_action(subaction) for subaction in self._iter_indented_subactions(action))
        # return a single string
        return self._join_parts(parts)


class Option:
    """A reusable option object which delegates all arguments
    to parser.add_argument().
    """

    @overload
    def __init__(
        self,
        *name_or_flags: str,
        action: argparse._ActionStr | type[Action] = ...,
        nargs: int | argparse._NArgsStr | Any = ...,
        const: Any = ...,
        default: Any = ...,
        type: Callable[[str], Any] | argparse.FileType = ...,
        choices: Iterable[Any] | None = ...,
        required: bool = ...,
        help: str | None = ...,
        metavar: str | tuple[str, ...] | None = ...,
        dest: str | None = ...,
        version: str = ...,
        **kwargs: Any,
    ) -> None:
        ...

    @overload
    def __init__(self, *args, **kwargs) -> None:
        ...

    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs

    def add_to_parser(self, parser: argparse._ActionsContainer) -> None:
        parser.add_argument(*self.args, **self.kwargs)

    def add_to_group(self, group: argparse._ArgumentGroup) -> None:
        group.add_argument(*self.args, **self.kwargs)
