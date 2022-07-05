from ward import test
from cs_tools import __version__

from tests.fixtures import runner, entrypoint
from tests.util import clean_args, escape_ansi
from tests.tags import CLI


# PARAMETERIZE
for info in [
    {'cmd': 'cstools', 'in_out': 'Usage: cs_tools <command> [--version, --help]'},
    {'cmd': 'cs_tools', 'in_out': 'Usage: cs_tools <command> [--version, --help]'},
    {'cmd': 'cs_tools --help', 'in_out': 'Usage: cs_tools <command> [--version, --help]'},
    {'cmd': 'cs_tools --helpfull', 'in_out': 'Usage: cs_tools <command> [--version, --help]'},
    {'cmd': 'cs_tools --version', 'in_out': f'cs_tools ({__version__})'},
]:
    command = info['cmd']
    partial = info['in_out']
    test_name = command + ' ' + info.get('test_name', '')

    @test(test_name, tags=[CLI])
    def _(cli=runner, app=entrypoint, command=command, out=partial):
        args = clean_args(command)
        result = cli.invoke(app, args=args)
        assert result.exit_code == 0
        assert out in escape_ansi(result.stdout)
