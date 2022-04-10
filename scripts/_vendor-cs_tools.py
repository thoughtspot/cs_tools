"""
Prepare a distributable version of CS Tools, complete with dependencies.

Client machines often times do not have outside internet access. Additionally, multiple
versions of python and OS configurations are supported by CS Tools. This can become
difficult to manage by hand across 25+ configurations.

Additionally, when new python versions, dependency requirements, or unix OS versions are
released, we need augment the distribution. This scaffolding helps do just that.

Files will be written under the project root /dist subdirectory.

    cs_tools/
    ├─ ...
    │
    ├─ dist/
    │  ├─ windows/
    │  │  ├─ dependency-1.whl
    │  │  ├─ ...
    │  │  └─ dependency-N.whl
    │  ├─ linux/
    │  │  ├─ ...
    │  │  └─ ...
    │  ├─ mac/
    │  │  ├─ ...
    │  │  └─ ...
    │  │
    │  └─ req/
    │     ├─ offline-install.txt
    │     └─ requirements.txt
    │
    └─ ...

"""
from zipfile import ZipFile, ZIP_DEFLATED
import subprocess as sp
import itertools as it
import platform
import logging
import pathlib
import sys
import os


log = logging.getLogger(__name__)
HERE = pathlib.Path(__file__).parent
DIST = HERE.parent / 'dist'
ON_GITHUB = 'GITHUB_ACTIONS' in os.environ

SUPPORTED_PYTHON_VERSIONS = ('3.6.8', '3.7', '3.8', '3.9', '3.10')
SUPPORTED_ARCHITECTURES = {
    'windows': (
        'win_amd64',  # Who's running on win32 these days? :~)
    ),
    'linux': (
        # more info: https://github.com/pypa/manylinux
        # 'manylinux_x_y',       # Future-proofing
        'manylinux2014_x86_64',  # Centos7 based, aka thoughtspot supported
        'manylinux1_x86_64',     # Centos5 based, common in the wild, manylinux EOL: 2022/01
    ),
    'mac': (
        'macosx_12_x86_64',      # Monterey released 2021/10
        'macosx_11_x86_64',      # Big Sur  released 2020/11
        'macosx_10_15_x86_64',   # Catalina released 2019/10
        'macosx_10_14_x86_64',   # Mojave   released 2018/09
    )
}


def in_virtual_env() -> bool:
    """
    Check if the current script is running inside a virtual environment.
    """
    real_prefix = getattr(sys, 'real_prefix', None)
    base_prefix = getattr(sys, 'base_prefix', sys.prefix)
    return (base_prefix or real_prefix) != sys.prefix


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


def pip(*args) -> str:
    """
    Use pip, programmatically.

    pip is a command line program. This does not mean that the pip developers
    are opposed in principle to the idea that pip could be used as a library
    - it’s just that this isn’t how it was written. What this means in practice
    is that everything inside of pip is considered an implementation detail.

    Having said all of the above, it is worth covering the options available
    if you decide that you do want to run pip from within your program. The
    most reliable approach, and the one that is fully supported, is to run pip
    in a subprocess.

    Full discourse here:
      https://pip.pypa.io/en/stable/user_guide/#using-pip-from-your-program
    """
    r = sp.check_output([sys.executable, '-m', 'pip', *args])
    return r.decode()


if __name__ == '__main__':
    logging.basicConfig(format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S', level='INFO')

    if not ON_GITHUB:
        if not in_virtual_env():
            log.warning('not running in virtual environment.. please activate it first!')
            raise SystemExit(-1)

    try:
        import cs_tools
    except ModuleNotFoundError:
        log.warning(
            f'import of cs_tools failed, you might have a broken local install!\n\n'
            f'try running..\n\n\tpip install -r {HERE.parent}/dev-requirements.txt\n\n'
            f'and then re-run this script\n\n\t{" ".join(sys.argv)}'
        )
        raise SystemExit(-1)

    __version__ = cs_tools._version.__version__

    if not ON_GITHUB:
        # uninstall all dependencies and reset the environment
        log.info('uninstalling all packages and deleting pip\'s cache')
        now_frozen = pip('freeze').strip().split('\r\n')
        reqs = [_ for _ in now_frozen if 'cs_tools' not in _ if _]
        reqs.append('cs_tools')
        pip('uninstall', '-y', *reqs)
        pip('cache', 'purge')

    # install from requirements.txt
    log.info('installing packages from requirements.txt')
    reqs = HERE.parent / 'requirements.txt'
    pip('install', '-r', reqs)

    # download all packages..
    for platform_name, architectures in SUPPORTED_ARCHITECTURES.items():
        if ON_GITHUB and get_system_name() != platform_name:
            continue

        log.info(f'downloading packages for {platform_name}..')
        for py_version in SUPPORTED_PYTHON_VERSIONS:
            log.info(f'\t on  py{py_version: <5}')
            pip(
                'download',
                '-r', reqs.as_posix(),
                '--dest', (DIST / platform_name).as_posix(),
                '--implementation', 'cp',
                *it.chain.from_iterable(('--platform', f'{a}') for a in architectures),
                '--python-version', py_version,
                '--only-binary=:all:'
            )

        # vendor cs_tools itself
        log.info(f'\t vendoring cs_tools=={__version__}\n')
        with ZipFile(DIST / platform_name / f'cs_tools-{__version__}.zip', mode='w', compression=ZIP_DEFLATED) as z:
            dir_ = HERE.parent.expanduser().resolve(strict=True)

            for stem in (
                'setup.py', 'requirements.txt', 'README.md', 'LICENSE', 'MANIFEST.in',
                'ThoughtSpot_Dev_Tools_EULA.pdf'
            ):
                file = dir_ / stem
                z.write(file, file.relative_to(dir_))

            for file in (dir_ / 'cs_tools').rglob('*'):
                if '__pycache__' in file.as_posix():
                    continue

                z.write(file, file.relative_to(dir_))

    # install environment using the local option..
    log.info('installing in virtual environment using offline-install.txt')
    pip(
        'install',
        '-r',
        f'{DIST}/reqs/offline-install.txt',
        f'--find-links={DIST}/{get_system_name()}/',
        '--no-cache-dir',
        '--no-index'
    )

    log.info('checking if cs_tools meets the current version')
    r = sp.check_output(['cs_tools', '--version'])
    a = r.decode().strip()
    t = f'cs_tools ({__version__})'
    
    try:
        assert a == t
    except AssertionError:
        log.info(f'\t failed! ❌\n\t   [found: {a}, expecting: {t}]')
        raise
    else:
        log.info('\tsuccess! ✅')

    if not ON_GITHUB:
        # re-install from dev-requirements.txt
        log.info('resetting environment from dev-requirements.txt')
        reqs = HERE.parent / 'dev-requirements.txt'
        pip('install', '-r', reqs)
