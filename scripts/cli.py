from tempfile import TemporaryDirectory
import subprocess as sp
import zipfile
import logging
import pathlib
import shutil
import os

from typer import Argument as A_, Option as O_  # noqa
import oyaml as yaml
import typer

from cs_tools.cli.ux import console, CSToolsApp, CSToolsGroup, CSToolsCommand
from cs_tools.const import PACKAGE_DIR
from cs_tools import __version__


log = logging.getLogger(__name__)


app = typer.Typer(
    cls=CSToolsGroup,
    name="cs_scripts",
    help="""
    Welcome to CS Scripts!

    [bold yellow]You must have a development install in order to run these commands![/]
    """,
    add_completion=False,
    context_settings={
        # global settings
        'help_option_names': ['--help', '-h', '--helpfull'],

        # allow responsive console design
        'max_content_width':
            console.width if console.width <= 120 else max(120, console.width * .65),

        # allow case-insensitive commands
        'token_normalize_func': lambda x: x.lower()
    },
    options_metavar='[--version, --help]'
)


@app.command(cls=CSToolsCommand)
def dos2unix(fp: pathlib.Path):
    """
    """
    with fp.open('r') as in_:
        data = in_.read()

    with fp.open('w') as out:
        out.write(data.replace('\r\n', '\n'))


@app.command(cls=CSToolsCommand)
def develop_docs():
    """
    """
    sp.check_output(['mkdocs', 'serve'])


@app.command('build-docs', cls=CSToolsCommand)
def _docs_build(
    dir_: pathlib.Path = A_(..., metavar='DIR', help='directory to output the documentation to'),
    zipped: bool = O_(False, '--zipped', help='compress the documentation into a single zipfile')
):
    """
    Build the documentation offline.

    [yellow]You must have a development install in order to run this command![/]
    """
    try:
        import mkdocs  # noqa
    except ModuleNotFoundError:
        log.error(
            'You do not have a development install of cs_tools, please see the project '
            'maintainers for an offline version of the documentation.'
        )
        raise typer.Exit(-1)

    PROJECT_ROOT = PACKAGE_DIR.parent
    TMP_DIR  = TemporaryDirectory()
    TMP_FILE = pathlib.Path(TMP_DIR.name) / 'local.yaml'

    if zipped:
        dir_ = dir_ / 'docs'

    with (PROJECT_ROOT / 'mkdocs.yml').open('r') as remote, TMP_FILE.open('w') as local:
        data = yaml.load(remote.read(), Loader=yaml.Loader)
        # should also remove plugins.search when/if we enable it
        data['docs_dir'] = (PROJECT_ROOT / 'docs').as_posix()
        data['site_url'] = ''
        data['use_directory_urls'] = False
        yaml.dump(data, local)

        # -f, --config-file  Provide a specific MkDocs config
        # -d, --site-dir     The directory to output the result of the documentation build.
        with sp.Popen(f'mkdocs build -f {TMP_FILE} -d {dir_}', stdout=sp.PIPE) as p:
            for line in p.stdout:
                log.info(line)

    if zipped:
        shutil.make_archive(dir_.parent / f'cs_tools-docs-{__version__}', 'zip', dir_)
        shutil.rmtree(dir_)


@app.command(cls=CSToolsCommand)
def run_tests(cfg_name: str = O_(..., help='which configuration file to use')):
    """
    """
    os.environ['WARD_TS_CONFIG_NAME'] = cfg_name
    cmd =  'coverage run -m ward'
    # cmd += ' && coverage report -m'

    with sp.Popen(cmd, stdout=sp.PIPE, cwd=PACKAGE_DIR.parent) as proc:
        for line in proc.stdout:
            console.log(line.decode().strip())


@app.command()
def vendor_pkgs():
    """
    """
    sp.check_output(['nox', '--sessions', 'ensure_working_local_install'])

    dist = PACKAGE_DIR.parent / 'dist'

    for arch in ('windows', 'mac', 'linux'):
        with zipfile.ZipFile(dist / f'{arch}-cs_tools-{__version__}.zip', mode='w') as z:
            for file in (dist / arch).iterdir():
                z.write(file, f'pkgs/{file.name}')
                file.unlink()

            z.write(dist / 'reqs/py36-offline-install.txt', 'reqs/py36-offline-install.txt')
            z.write(dist / 'reqs/py36-requirements.txt', 'reqs/py36-requirements.txt')
            z.write(dist / 'reqs/offline-install.txt', 'reqs/offline-install.txt')
            z.write(dist / 'reqs/requirements.txt', 'reqs/requirements.txt')

            if arch == 'windows':
                z.write(dist / 'windows_install.ps1', 'windows_install.ps1')
                z.write(dist / 'windows_activate.ps1', 'windows_activate.ps1')
            else:
                z.write(dist / 'unix_install.sh', 'unix_install.sh')
                z.write(dist / 'unix_activate.sh', 'unix_activate.sh')


if __name__ == '__main__':
    app()
