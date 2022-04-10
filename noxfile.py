import platform
import pathlib
import os

import nox


ON_GITHUB = 'GITHUB_ACTIONS' in os.environ
HERE = pathlib.Path(__file__).parent
DIST = HERE.parent / 'dist'


nox.options.reuse_existing_virtualenvs = False


def get_system_name() -> str:
    """
    Translate `this` system into a friendlier name.

    Returns
    -------
    system: str
        one of.. windows, linux, mac
    """
    translate = {'Windows': 'windows', 'Linux': 'linux', 'Darwin': 'mac'}
    return translate[platform.uname().system]


@nox.session()
def ensure_working_local_install(session: nox.Session):
    """
    """
    if ON_GITHUB:
        session.log('on Github: must vendor packages first')
        session.log('..installing cs_tools')
        session.install('install', '-e', '.', silent=True)

        session.log('..vendoring packages')
        session.run('python', f'{HERE.as_posix()}/scripts/_vendor-cs_tools.py', silent=True)

        session.log('..resetting environment')
        p = pathlib.Path('_current_requirements.txt')
        with p.open('w') as in_:
            session.run('pip', 'freeze', stdout=in_)
            session.run('pip', 'uninstall', '-r', p.as_posix(), '-y', silent=True)
        p.unlink()

    session.install(
        '-r',
        f'{DIST.as_posix()}/reqs/offline-install.txt',
        f'--find-links={DIST.as_posix()}/{get_system_name()}/',
        '--no-cache-dir',
        '--no-index'
    )

    session.run('cs_tools', '--version')
