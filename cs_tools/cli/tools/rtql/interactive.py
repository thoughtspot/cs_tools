from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional
import json
import logging

from rich.console import Console
import httpx
import rich
import typer

from .completer import TQLCompleter
from .const import TQL_HELP

if TYPE_CHECKING:
    from cs_tools.thoughtspot import ThoughtSpot

log = logging.getLogger(__name__)


def _to_table(headers, rows=None):
    header = [column["name"] for column in headers]

    if rows is None:
        rows = [{"v": (" ",) * len(header)}]

    data = [dict(zip(header, row["v"])) for row in rows]
    return data


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

    autocomplete : bool  [default: True]
      whether or not to autocomplete, invoked with TAB

    http_timeout: int [default: 60s]
      number of seconds for http calls to come back

    console : rich.Console  [default: new console]
      rich console to print feedback to

    Attributes
    ----------
    ctx : dict
      local version of the remote TQL context

    completer : TQLCompleter
      used to autocomplete tokens
    """

    def __init__(
        self,
        ts: ThoughtSpot,
        *,
        schema: dict = "falcon_default_schema",
        autocomplete: bool = True,
        http_timeout: int = 60,
        console: Optional[Callable] = None,
    ):
        self.ts = ts
        self.ctx = {"schema": schema, "server_schema_version": -1}
        self.autocomplete = autocomplete
        self.completer = TQLCompleter()
        self._current_prompt = None
        self.console = console if console is not None else Console()
        self.http_timeout = http_timeout

    @property
    def print(self):  # noqa: A003
        return self.console.print

    def _query(self, questions: Optional[list[dict]] = None):
        """
        Send a query to the remote TQL instance.

        If we're in an interactive question, this means we're sending a
        response, which is usually a PARTITION BY statement. These
        commands can take a signficant amount of time to return, so we
        set the timeout to None and block until they do.
        """
        data = {"context": self.ctx, "query": {"statement": self._current_prompt}}

        if questions is not None:
            data["query"]["prompt_responses"] = questions
            timeout = None
        else:
            timeout = max(15.0, self.http_timeout)

        with self.console.status("[bold green]running query[/]"):
            try:
                r = self.ts.api.v1.dataservice_query(data=data, timeout=timeout)
                r.raise_for_status()
            except httpx.HTTPStatusError as e:
                log.error("TQL query request failed.", exc_info=True)
                raise RuntimeError(f"TQL query request failed ({e.response.status_code}) for {e.request.url}") from None
            except Exception:
                log.error("TQL query request failed.", exc_info=True)
                raise ValueError("TQL query request failed.") from None

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
        id_ = q["question_id"]
        question = q["banner"]
        # prompt = q['prompt']  # NOTE: do we actually need this?
        answers = [o.lower() for o in q["options"]]
        answer = ""

        while answer.lower() not in answers:
            if answer != "":
                self.print(f'[red]"{answer} is an unnacceptable answer[/]')

            answer = typer.prompt(
                typer.style(question, fg="yellow"),
                default=" ",
                prompt_suffix=typer.style("\n> ", fg="cyan"),
                show_default=False,
            )

        return {"question_id": id_, "answer": answer}

    def _handle_query(self, lines: list[str]) -> None:
        """ """
        color_map = {"INFO": "[white]", "WARNING": "[yellow]", "ERROR": "[red]"}
        new_ctx = {}

        for line in lines:
            data = json.loads(line)
            new_ctx = data["result"].get("final_context", {})

            # NOTE: do we need/want a progress bar?
            #
            # update progress bar? needed?
            # data['result']['progress']

            if "interactive_question" in data["result"]:
                answers = []

                for q in data["result"]["interactive_question"]:
                    answer = self._handle_question(q)
                    answers.append(answer)

                self._query(answers)
                continue

            if "message" in data["result"]:
                for message in data["result"]["message"]:
                    c = color_map.get(message["type"], "[yellow]")
                    m = message["value"]

                    if m.strip() == "Statement executed successfully.":
                        c = "[bold green]"
                    if m.strip().endswith(";"):
                        c = "[cyan]"

                    self.print(c + m + "[/]", end="")

            if "table" in data["result"]:
                d = _to_table(**data["result"]["table"])
                t = rich.table.Table(*d[0].keys(), box=rich.box.HORIZONTALS)
                [t.add_row(*_.values()) for _ in d]
                self.print(t)

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

        if token_type == "dynamic":
            call_ = self.ts.api.v1.dataservice_tokens_dynamic
            key = "schema"

        if token_type == "static":
            call_ = self.ts.api.v1.dataservice_tokens_static
            key = "language"

        try:
            r = call_()
            r.raise_for_status()
        except Exception as e:
            log.debug(e, exc_info=True)
            self.print(f"[red]Autocomplete tokens could not be fetched. " f"{r.status_code}: {r.text}[/]")
            raise typer.Exit() from None
        else:
            tokens = sorted(r.json()["tokens"])
            self.completer.update({key: tokens})

    def simulate_tql_prompt(self) -> str:
        """
        Get input from user, mimicing the TQL client.
        """
        database = self.ctx.get("database") or "(none)"

        try:
            query = typer.prompt(
                typer.style(f"TQL [database={database}]>", fg="cyan"),
                default=" ",
                prompt_suffix=" ",
                show_default=False,
            )

            while True:
                if query[-1] == ";" or query.strip() in ["exit", "quit", "h", "help", "clear"]:
                    break

                line = typer.prompt(typer.style(">", fg="cyan"), prompt_suffix=" ")
                query += f" {line.strip()}"

        except EOFError:  # aka CTRL+D aka "quit"
            return

        except typer.Abort:  # aka CTRL+C aka "clear"
            return "clear"

        return query.strip()

    def reset_context(self, new_ctx: Optional[dict] = None) -> None:
        """
        Reset the database context in this session.

        This method is purely functional.

        Parameters
        ----------
        new_ctx : dict
          context (from the remote server) to sync with the local client
        """
        if new_ctx is None:
            new_ctx = {"schema": "falcon_default_schema", "server_schema_version": -1}

        if "database" in new_ctx:
            self.ctx["database"] = new_ctx["database"]

        if "server_schema_version" in new_ctx:
            self.ctx["server_schema_version"] = new_ctx["server_schema_version"]
            self.update_tokens("dynamic")

    def run(self) -> None:
        """
        Start the TQL client.

        This method is purely functional.
        """
        with self.console.status("[bold green]starting remote TQL client..[/]"):
            self.ts.login()
            self.ts.tql._check_privileges()
            self.update_tokens("static")
            self.update_tokens("dynamic")

        self.console.clear()
        self.console.clear()

        self.print(
            "\nWelcome to the ThoughtSpot SQL command line interface, "
            f"{self.ts.me.display_name}!"
            "\n\n[green]Controls:"
            "\n  Press Control-C to clear current command."  # cmd-c ?
            '\n  Press Control-D or type "exit" or "quit" to exit.'  # doesn't work on Windows
            '\n  Type "help" for available commands.[/]'
            "\n\n  [yellow]Remember to add a semicolon after each command![/]"
            "\n\nConnected to remote TQL service."
            f"\nCluster address: {self.ts.platform.url}"
            f"\nCluster version: {self.ts.platform.version}"
        )

        while True:
            prompt = self.simulate_tql_prompt()

            if prompt == "clear":
                self.console.clear()
                continue

            if prompt is None or prompt.startswith(("quit", "exit")):
                break

            if prompt == "h" or prompt.startswith("help"):
                self.print(TQL_HELP)
                continue

            # only set the current prompt for when we need to send it remotely
            self._current_prompt = prompt

            r = self._query()
            ctx = self._handle_query(r)
            self.reset_context(ctx)
