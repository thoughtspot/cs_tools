# DEV NOTE:
#
# Future enhancements:
#   - ability to manipulate objects, such as renaming references to worksheets and tables, token replacement, etc.
#   - add support for tables and connections
#   - add support for importing .zip files
#
import pathlib
import click
from typer import Argument as A_, Option as O_
from typing import List, Optional
import typer

from cs_tools.cli.tools.common import setup_thoughtspot, teardown_thoughtspot
from cs_tools.cli.dependency import depends
from cs_tools.cli.options import CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT
from cs_tools.data.enums import TMLImportPolicy
from cs_tools.cli.types import CommaSeparatedValuesType
from cs_tools.cli.ux import CSToolsGroup, CSToolsCommand

from ._compare import compare
from ._create_mapping import create_mapping
from ._export import export
from ._import import import_


app = typer.Typer(
    help="""
    Tool for easily migrating TML between instance.

    [b][yellow]USE AT YOUR OWN RISK![/b] This tool uses private API calls which
    could change on any version update and break the tool.[/]

    ThoughtSpot provides the ability to extract object metadata (tables, worksheets, liveboards, etc.) 
    in ThoughtSpot Modeling Language (TML) format, which is a text format based on YAML.  
    These files can then be modified and imported into another (or the same) instance to either create 
    or modify objects.

      cs_tools tools scriptability --help
    
    \f
    """,
    cls=CSToolsGroup,
    options_metavar='[--version, --help]'
)


@app.command(cls=CSToolsCommand, name="export")
@depends(
    'thoughtspot',
    setup_thoughtspot,
    options=[CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT],
    teardown=teardown_thoughtspot,
)
def scriptability_export(
        ctx: click.Context,
        path: pathlib.Path = A_(  # may not want to use
            ...,
            help='full path (directory) to save data set to',
            metavar='DIR',
            dir_okay=True,
            resolve_path=True
        ),
        tags: List[str] = O_([], metavar='TAGS',
                             callback=lambda ctx, to: CommaSeparatedValuesType().convert(to, ctx=ctx),
                             help='comma separated list of tags to export'),
        export_ids: List[str] = O_([], metavar='GUIDS',
                                   callback=lambda ctx, to: CommaSeparatedValuesType().convert(to, ctx=ctx),
                                   help='comma separated list of GUIDs to export'),
        author: str = O_('', metavar='USERNAME',
                         help='username that is the author of the content to download'),
        export_associated: bool = O_(False,
                                     help='if specified, also export related content'),
        set_fqns: bool = O_(False,
                            help='if set, then the content in the TML will have FQNs (GUIDs) added.')
):
    export(ctx=ctx, path=path, tags=tags, export_ids=export_ids, author=author,
           export_associated=export_associated, set_fqns=set_fqns)


@app.command(cls=CSToolsCommand, name="import")
@depends(
    'thoughtspot',
    setup_thoughtspot,
    options=[CONFIG_OPT, VERBOSE_OPT, TEMP_DIR_OPT],
    teardown=teardown_thoughtspot,
)
def scriptability_import(
        ctx: click.Context,
        path: pathlib.Path = A_(
            ...,
            help='full path to the TML file or directory to import.',
            metavar='FILE_OR_DIR',
            dir_okay=True,
            resolve_path=True
        ),
        import_policy: TMLImportPolicy = O_(TMLImportPolicy.validate_only.value,
                                            help="The import policy type"),
        force_create: bool = O_(False,
                                help="If true, will force a new object to be created."),
        guid_file: Optional[pathlib.Path] = O_(
            None,
            help='Existing or new mapping file to map GUIDs from source instance to target instance.',
            metavar='FILE_OR_DIR',
            dir_okay=False,
            resolve_path=True
        ),
        tags: List[str] = O_([], metavar='TAGS',
                             callback=lambda ctx, to: CommaSeparatedValuesType().convert(to, ctx=ctx),
                             help='One or more tags to add to the imported content.'),
        share_with: List[str] = O_([], metavar='GROUPS',
                                   callback=lambda ctx, to: CommaSeparatedValuesType().convert(to, ctx=ctx),
                                   help='One or more groups to share the uploaded content with.'),
        tml_logs: Optional[pathlib.Path] = O_(
            None,
            help='full path to the directory to log sent TML.  TML can change during load.',
            metavar='DIR',
            dir_okay=True,
            resolve_path=True
        ),
):
    import_(ctx=ctx, path=path, import_policy=import_policy, force_create=force_create, guid_file=guid_file, tags=tags,
            share_with=share_with, tml_logs=tml_logs)


@app.command(name='compare', cls=CSToolsCommand)
def scriptability_compare(
        file1: pathlib.Path = A_(
            ...,
            help='full path to the first TML file to compare.',
            metavar='FILE1',
            dir_okay=False,
            resolve_path=True
        ),
        file2: pathlib.Path = A_(
            ...,
            help='full path to the second TML file to compare.',
            metavar='FILE2',
            dir_okay=False,
            resolve_path=True
        ),
):
    compare(file1=file1, file2=file2)


@app.command(name='create-mapping', cls=CSToolsCommand)
def scriptability_create_mapping(
    guid_file: pathlib.Path = A_(
        ...,
        help='Path to the new mapping file to be created.  Existing files will not be overwritten.',
        metavar='FILE',
        dir_okay=False,
        resolve_path=True
    ),
):
    create_mapping(guid_file=guid_file)
