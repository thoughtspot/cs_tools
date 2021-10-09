from ward import test, using

from tests.fixtures import app_runner, app


PARAMETERS = {
    '--help': 'Welcome to CS Tools!',
    'logs': 'Export and view log files.',
    'config': 'Work with dedicated config files.',
    'tools': 'Run an installed tool.',
    'tools --private': 'Run an installed tool.'
}


# for command, partial_output in PARAMETERS.items():

#     @test('command: cs_tools {command}', tags=['unit'])
#     @using(runner=app_runner, cli=app)
#     def _(runner, cli, command=command, partial_output=partial_output):
#         r = runner.invoke(cli, command.split())
#         print(r.stdout)
#         assert r.exit_code == 0
#         assert partial_output in r.stdout
