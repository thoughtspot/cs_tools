from typing import List
import logging
import json

import httpx
import typer

from cs_tools.helpers.cli_ux import console
from cs_tools.schema.user import PrivilegeEnum
from cs_tools.api import ThoughtSpot
from .completer import TQLCompleter
from .const import TQL_HELP


log = logging.getLogger(__name__)


class InteractiveTQL:
    """
    An interactive TQL client.

    iTQL will handle all session details. The API instance passed to iTQL
    should not already be logged in to the platform.

    Parameters
    ----------
    api : ThoughtSpot
      thoughtspot api instance

    schema : dict
      default schema to use

    autocomplete: bool  [default: True]
      whether or not to autocomplete, invoked with TAB

    Attributes
    ----------
    ctx : dict
      local version of the remote TQL context

    completer : TQLCompleter
      used to autocomplete tokens
    """
    def __init__(
        self,
        api: ThoughtSpot,
        *,
        schema: dict='falcon_default_schema',
        autocomplete: bool=True,
    ):
        self.ts_api = api
        self.ctx = {'schema': schema, 'server_schema_version': -1}
        self.autocomplete = autocomplete
        self.completer = TQLCompleter()
        self._current_prompt = None

    def _check_privileges(self):
        required = set([PrivilegeEnum.can_administer_thoughtspot, PrivilegeEnum.can_manage_data])
        privileges = set(self.ts_api.logged_in_user.privileges)

        if not set(privileges).intersection(required):
            console.print(
                '[red]You do not have the correct privileges to access the remote TQL '
                'service!\n\nYou require at least the "Can Manage Data" privilege.'
                '\n\nPlease consult with your ThoughtSpot Administrator.[/]'
            )
            raise typer.Exit()

    def _query(self, questions: List[dict]=None):
        """
        Send a query to the remote TQL instance.

        If we're in an interactive question, this means we're sending a
        response, which is usually a PARTITION BY statement. These
        commands can take a signficant amount of time to return, so we
        set the timeout to None and block until they do.
        """
        data = {
            'context': self.ctx,
            'query': {
                'statement': self._current_prompt
            }
        }

        if questions is not None:
            data['query']['prompt_responses'] = questions
            timeout = None
        else:
            timeout = 5.0

        with console.status('[bold green]running query[/]'):
            try:
                r = self.ts_api.ts_dataservice.query(data, timeout=timeout)
                r.raise_for_status()
            except Exception:
                raise ValueError(f'TQL query request failed. {r.status_code}: {r.text}')

        return r.iter_lines()

    def _handle_question(self, q: dict) -> dict:
        """
        Interactively handle a question present from the API.

        Commands that generate an interactive question...
            ALTER TABLE 'tbl' SET DIMENSION
            ALTER TABLE 'tbl' SET FACT PARTITION BY HASH (##) KEY ('column')

        Question data comes as a dict with keys:
            question_id .. unique id of the question to answer
            banner ....... warning/pip to display prior to asking for input
            prompt ....... text you'd supply to an input() call
            answers ......  list of acceptable content to match against

        Response data should return as a dict with keys:
           question_id .. unique id of the question to answer
           answer ....... one of the unique values from <answers>
        """
        id_ = q['question_id']
        question = q['banner']
        # prompt = q['prompt']  # NOTE: do we actually need this?
        answers = [o.lower() for o in q['options']]
        answer = ''

        while answer.lower() not in answers:
            if answer != '':
                console.print(f'[red]"{answer} is an unnacceptable answer[/]')

            answer = typer.prompt(
                        typer.style(question, fg='yellow'),
                        default=' ',
                        prompt_suffix=typer.style('\n> ', fg='cyan'),
                        show_default=False
                    )

        return {'question_id': id_, 'answer': answer}

    def _handle_query(self, lines: List[str]) -> None:
        """

        """
        new_ctx = {}

        for line in lines:
            data = json.loads(line)
            new_ctx = data['result'].get('final_context', {})

            # NOTE: do we need/want a progress bar?
            #
            # update progress bar? needed?
            # data['result']['progress']

            if 'interactive_question' in data['result']:
                answers = []

                for q in data['result']['interactive_question']:
                    answer = self._handle_question(q)
                    answers.append(answer)

                self._query(answers)
                continue

            if 'message' in data['result']:
                msg = self.ts_api.ts_dataservice._parse_api_messages(data['result']['message'])
                console.print(msg)

            if 'table' in data['result']:
                msg = self.ts_api.ts_dataservice._parse_tql_query(data['result']['table'])
                console.print(msg)

        return new_ctx

    def update_tokens(self, token_type: str) -> None:
        """
        Update tokens for autocomplete.

        This method is purely functional.

        Parameters
        ----------
        token_type : str
          classifier for the type of dataservice call to make
        """
        if not self.autocomplete:
            return

        if token_type == 'dynamic':
            call_ = self.ts_api.ts_dataservice.tokens_dynamic
            key = 'schema'

        if token_type == 'static':
            call_ = self.ts_api.ts_dataservice.tokens_static
            key = 'language'

        try:
            r = call_()
            r.raise_for_status()
        except Exception as e:
            log.debug(e)
            console.print(
                f'[red]Autocomplete tokens could not be fetched. '
                f'{r.status_code}: {r.text}[/]'
            )
            raise typer.Exit() from None
        else:
            tokens = sorted(list(r.json()['tokens']))
            self.completer.update({key: tokens})

    def simulate_tql_prompt(self) -> str:
        """
        Get input from user, mimicing the TQL client.
        """
        database = self.ctx.get('database') or '(none)'

        try:
            query = typer.prompt(
                        typer.style(f'TQL [database={database}]>', fg='cyan'),
                        default=' ',
                        prompt_suffix=' ',
                        show_default=False
                    )

            while True:
                if query[-1] == ';' or query.strip() in ['exit', 'quit', 'h', 'help']:
                    break

                line = typer.prompt(typer.style('>', fg='cyan'), prompt_suffix=' ')
                query += f' {line.strip()}'

        except EOFError:     # aka CTRL+D aka "quit"
            return

        except typer.Abort:  # aka CTRL+C aka "clear"
            return 'clear'

        return query.strip()

    def reset_context(self, new_ctx: dict=None) -> None:
        """
        Reset the database context in this session.

        This method is purely functional.

        Parameters
        ----------
        new_ctx : dict
          context (from the remote server) to sync with the local client
        """
        if new_ctx is None:
            new_ctx = {'schema': 'falcon_default_schema', 'server_schema_version': -1}

        if 'database' in new_ctx:
            self.ctx['database'] = new_ctx['database']

        if 'server_schema_version' in new_ctx:
            self.ctx['server_schema_version'] = new_ctx['server_schema_version']
            self.update_tokens('dynamic')

    def run(self) -> None:
        """
        Start the TQL client.

        This method is purely functional.
        """
        with console.status('[green]starting remote TQL client..[/]'):
            self.ts_api.__enter__()
            self._check_privileges()
            self.update_tokens('static')
            self.update_tokens('dynamic')

        console.clear()

        console.print(
            '\nWelcome to the ThoughtSpot SQL command line interface, '
            f'{self.ts_api.logged_in_user.display_name}!'
            '\n\n[green]Controls:'
            '\n  Press Control-C to clear current command.'          # cmd-c ?
            '\n  Press Control-D or type "exit" or "quit" to exit.'  # doesn't work on Windows
            '\n  Type "help" for available commands.[/]'
            '\n\n  [yellow]Remember to add a semicolon after each command![/]'
            '\n\nConnected to remote TQL service.'
            f'\nCluster address: {self.ts_api.host}'
            f'\nCluster version: {self.ts_api.thoughtspot_version}'
        )

        while True:
            prompt = self.simulate_tql_prompt()

            if prompt == 'clear':
                console.clear()
                continue

            if prompt is None or prompt.startswith(('quit', 'exit')):
                break

            if prompt == 'h' or prompt.startswith('help'):
                console.print(TQL_HELP)
                continue

            # only set the current prompt for when we need to send it remotely
            self._current_prompt = prompt

            r   = self._query()
            ctx = self._handle_query(r)
            self.reset_context(ctx)

        self.ts_api.__exit__(None, None, None)
