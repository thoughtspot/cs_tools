"""
Prepare a distributable version of CS Tools, complete with dependencies.

Client machines often times do not have outside internet access. Additionally, multiple
versions of python and OS configurations are supported by CS Tools. This can become
difficult to manage by hand across 25+ configurations.

Additionally, when new python versions, dependency requirements, or unix OS versions are
released, we need augment the distribution. This scaffolding helps do just that.
"""
from zipfile import ZipFile, ZIP_DEFLATED
import subprocess as sp
import itertools as it
import logging
import pathlib
import sys


log = logging.getLogger(__name__)
HERE = pathlib.Path(__file__).parent
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

    if not in_virtual_env():
        log.warning('not running in virtual environment.. activate it first!')
        raise SystemExit(-1)

    # it's a hack to get the current version, assuming you won't attempt to run this
    # script unless CS Tools is actually installed :~)
    __version__ = __import__('cs_tools._version').__version__

    # uninstall all dependencies to reset the environment
    log.info('uninstalling all packages')
    now_frozen = pip('freeze').strip().split('\r\n')
    reqs = [_ for _ in now_frozen if 'cs_tools' not in _ if _]
    reqs.append('cs_tools')
    pip('uninstall', '-y', *reqs)

    # install from requirements.txt
    log.info('installing packages from requirements.txt')
    reqs = HERE.parent / 'requirements.txt'
    pip('install', '-r', reqs)

    # download all packages..
    dist = HERE.parent / 'dist'

    for platform, architectures in SUPPORTED_ARCHITECTURES.items():
        log.info(f'downloading packages for {platform}..')
        for py_version in SUPPORTED_PYTHON_VERSIONS:
            log.info(f'\t on  py{py_version: <5}')
            pip(
                'download',
                '-r', reqs,
                '--dest', dist / platform,
                '--implementation', 'cp',
                *it.chain.from_iterable(('--platform', f'{a}') for a in architectures),
                '--python-version', py_version,
                '--only-binary=:all:'
            )

        # vendor cs_tools itself
        log.info(f'\t vendoring cs_tools=={__version__}\n')
        with ZipFile(dist / platform / f'cs_tools-{__version__}.zip', mode='w', compression=ZIP_DEFLATED) as z:
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

    # re-install from dev-requirements.txt
    log.info('installing packages from dev-requirements.txt')
    reqs = HERE.parent / 'dev-requirements.txt'
    pip('install', '-r', reqs)
