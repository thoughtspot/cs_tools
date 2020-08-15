"""
Contains utilities to help interfacing directly with the folks running a
script.
"""
import argparse
import sys


def eprint(*args, **kwargs):
    """
    Prints to standard error similar to regular print.
    :param args:  Positional arguments.
    :param kwargs:  Keyword arguments.
    """
    print(*args, file=sys.stderr, **kwargs)


def printif(condition, text):
    """
    Prints out the text if the condition is met.  Simplify tracing.
    :param condition: The condition to check.
    :param condition: bool
    :param text: The text to print.
    :param test: str
    :return: Nothing.
    """
    if condition:
        print(text)


class DefaultArgumentParser(argparse.ArgumentParser):
    """
    """
    def __init__(self, *argparser_a, **argparser_kw):
        super().__init__(*argparser_a, **argparser_kw)
        self.add_argument('--toml', help='location of the tsconfig.toml configuration file')
        self.add_argument('--ts_url', help='the url to thoughtspot, https://my.thoughtspot.com')
        self.add_argument('--log_level', default='INFO', metavar='INFO', help='verbosity of the logger (used for debugging)')
        self.add_argument('--version', action='store_true', help='display the current version of this tool')

    def errored(self, errors: list):
        """
        Prints all accumulated errors during parsing.
        """
        messages = '\n'.join([f'[ERROR] {e}' for e in errors])
        eprint(f'\n{messages}\n')
        self.print_help()
        raise SystemExit('\n[ERROR] parsing arguments has failed, see the logs for details!')

    def print_version(self, vers):
        """
        Prints the version number.
        """
        eprint(f'{self.prog} {vers}')
        raise SystemExit(0)


class FrontendArgumentParser(DefaultArgumentParser):
    """
    """
    def __init__(self, *argparser_a, **argparser_kw):
        super().__init__(*argparser_a, **argparser_kw)
        self.add_argument('--username', help='frontend user to authenticate to ThoughtSpot with')
        self.add_argument('--password', help='frontend password to authenticate to ThoughtSpot with')
        self.add_argument('--disable_ssl', action='store_true', help='whether or not to ignore SSL errors')
        self.add_argument('--disable_sso', action='store_true', help='whether or not to disable SAML login redirect')
