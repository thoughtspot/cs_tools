from setuptools import setup, find_packages
import re


def read_version() -> str:
    """
    Don't import from the package we're trying to install.
    """
    # excludes inline comments as well
    RE_VERSION = re.compile(r'__version__\s*=\s*[\'"]([^\'"]*)[\'"]')

    with open('cs_tools/_version.py') as py:
        __version__ = RE_VERSION.search(py.read()).group(1)

    return __version__


with open('./requirements.txt') as f:
    REQUIRED = [f'{req.strip()}' for req in f.readlines()]


with open('./README.md') as f:
    README = '\n'.join(f.readlines())


setup(
    name='cs_tools',
    version=read_version(),
    description='Python programming interface to the ThoughtSpot API and platform',
    long_description=README,
    author='Customer Success @ ThoughtSpot',
    author_email='ps-na@thoughtspot.com',
    url='https://github.com/thoughtspot/cs_tools',
    license='Proprietary',
    packages=find_packages(),
    include_package_data=True,
    install_requires=REQUIRED,
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'cs_tools = cs_tools.cli:run',
            'cstools = cs_tools.cli:run',
        ]
    }
)
