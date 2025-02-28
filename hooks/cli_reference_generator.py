from __future__ import annotations  # noqa: I001

from typing import Optional, TypedDict
import datetime as dt
import logging
import textwrap

from mkdocs.config.defaults import MkDocsConfig
from mkdocs.structure.files import File, Files, InclusionLevel
import cs_tools
import typer

import _common_hook_utils

_LOG = logging.getLogger(__name__)

GENERATED_MARKDOWN_TEMPLATE = """
---
title: CLI
hide:
    - navigation
    - title
    - toc
    - footer
---

# Reference

{generated_cli_snippets}

<div style="text-align: right" class="fc-gray">
  <sup>
    This page was automatically generated on {date:%Y-%m-%d} for {__version__}
  </>
</div>
"""


class CommandTree(TypedDict):
    """A solved tree of typer commands in an app."""

    name: str
    commands: dict[str, str | CommandTree]


def build_command_tree(command: typer.main.Typer | typer.main.TyperGroup, skip_hidden: bool = True) -> CommandTree:
    """Walk a Typer app to build a CommandTree."""
    if _IS_ROOT := isinstance(command, typer.main.Typer):
        cli = typer.main.get_command(command)
        assert hasattr(cli, "commands"), "CLI commands could not be solved."

        tree: CommandTree = {"name": "cs_tools", "commands": {"--help": ""}}

        # GENERATE THE FULL COMMAND TREE.
        for name, command in cli.commands.items():
            tree["commands"][name] = build_command_tree(command)

        return tree

    #
    # RECURSIVELY WALK THE APP.
    #
    assert isinstance(command, typer.main.TyperGroup), f"Found an unknown Typer type {type(command)}"

    result: CommandTree = {
        "name": command.name or "<UNKNOWN>",
        "commands": {},
    }

    for name, sub_command in command.commands.items():
        if sub_command.hidden and skip_hidden:
            continue

        result["commands"]["--help"] = ""

        if isinstance(sub_command, typer.main.TyperCommand):
            result["commands"][name] = "--help"
        else:
            assert isinstance(sub_command, typer.main.TyperGroup), f"Found an unknown Typer type {type(sub_command)}"
            result["commands"][name] = build_command_tree(sub_command)

    return result


def generate_tabbed_snippet(tree: CommandTree, *, forest_name: str = "", indent: int = 0) -> str:
    """
    Depth-first search the CLI Command Tree, generating markdown.

    Example output is belo which creates a tabbed experience in the documentation.

    Further reading:
      https://squidfunk.github.io/mkdocs-material/reference/content-tabs/

    ------------------------------------------------------------------------------------
    https://thoughtspot.github.io/cs_tools/generated/cli/reference.md
    ------------------------------------------------------------------------------------

    === "cs_tools"
        === "--help"
            ~cs~tools --help

        === "tools"
            === "--help"
                ~cs~tools tools --help

            === "archiver"
                === "--help"
                    ~cs~tools tools archiver --help

                === "identify"
                    ~cs~tools tools archiver identify --help
                ...

    ------------------------------------------------------------------------------------
    """
    tree_name = tree["name"]

    snippet = f'\n=== "{tree_name}"'

    for name, command in tree["commands"].items():
        if isinstance(command, dict):
            fullpath = " ".join(filter(bool, [forest_name, tree_name]))
            snippet += generate_tabbed_snippet(command, forest_name=fullpath, indent=indent)
        else:
            fullpath = " ".join(filter(bool, [forest_name, tree_name, name, command]))
            snippet += textwrap.indent(
                textwrap.dedent(
                    f"""
                    === "{name}"

                        ??? abstract "Get the Command" 
                        
                            <sub class=fc-blue>Find the copy button :material-content-copy: to the right of the code block.</sub>
                    
                            ```shell
                            {fullpath}
                            ```
                    
                        {fullpath.replace("cs_tools", _common_hook_utils.CS_TOOLS_BLOCK_IDENTITY)}
                    """
                ),
                " " * indent,
            )

    return "\n" + textwrap.indent(snippet, " " * (indent if forest_name else 0))


def on_files(files: Files, config: MkDocsConfig) -> Optional[Files]:
    """
    The files event is called after the files collection is populated from the docs_dir.

    Use this event to add, remove, or alter files in the collection. Note that Page
    objects have not yet been associated with the file objects in the collection. Use
    Page Events to manipulate page specific data.

    Further reading:
      https://www.mkdocs.org/dev-guide/plugins/#on_post_build
    """
    app = _common_hook_utils.setup_cs_tools_cli()

    # GENERATE THE COMMAND TREE FROM THE APP.
    tree = build_command_tree(app)

    # GENERATE THE PAGE INFO.
    md_file = File(
        path="generated/cli/reference.md",
        use_directory_urls=False,
        src_dir=None,
        dest_dir=config["site_dir"],
        inclusion=InclusionLevel.INCLUDED,
    )

    # GENERATE THE PAGE METADATA.
    md_file.generated_by = "hooks.cli_generator"

    # PARSE THE COMMAND TREE INTO MARKDOWN.
    md_file.content_string = GENERATED_MARKDOWN_TEMPLATE.strip().format(
        generated_cli_snippets=generate_tabbed_snippet(tree, indent=4),
        date=dt.datetime.now(tz=dt.timezone.utc),
        __version__=f"v{cs_tools.__project__.__version__}",
    )

    # ADD THE GENERATED FILE TO THE LIST OF FILES.
    files.append(md_file)

    return files
