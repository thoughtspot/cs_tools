from typing import Dict

try:
    import readline
except ModuleNotFoundError:  # womp, we're on Windows!
    from pyreadline import Readline
    readline = Readline()


# OS X uses libedit
# force emacs bindings and add auto complete on tab
try:
    if 'libedit' in readline.__doc__:
        readline.parse_and_bind('bind -e')
        readline.parse_and_bind('bind "\t" rl_complete')
except TypeError:
    readline.parse_and_bind('tab: complete')


class TQLCompleter:
    """
    Enables autocomplete in TQL.

    Available keys in the .tokens attribute will be:
      language:
      schema:

    Attributes
    ----------
    tokens
      candidates for autocompletion
    """
    def __init__(self, tokens: Dict[str, list]=None, max_to_display: int=30):
        self.tokens = tokens if tokens is not None else {}
        self.max_to_display = max_to_display
        readline.set_completer(self.complete)
        # TODO ... implement prettier return values
        # not available on Windows / pyreadline
        # readline.set_completion_display_matches_hook(self.display)

    @property
    def autocomplete(self) -> bool:
        """
        Show whether or not autocomplete is ON.
        """
        return self.tokens != {}

    def complete(self, text: str, state: int) -> str:
        """
        Function for completion logic.

        Per readline's docs: this function is called until it returns a non-string
        value. <state> is 0, 1, 2, ... which is the number of times the user has asked
        for completion (usually via pressing TAB). .complete will return the next
        possible completion starting with <text>.

        Matches:
            - 30 maximum tokens returned, language tokens prioritized
            - case-insensitive match for all language tokens [must match input casing]
            - case-sensitive for all schema

        Parameters
        ----------
        text : str
          input typed by the user

        state : int
          amount of times user has asked for completion
        """
        results = []

        # case INSENSITIVE matching for language tokens
        if 'language' in self.tokens:
            matched = []

            for token in self.tokens['language']:
                if token.casefold().startswith(text.casefold()):
                    tok = token.lower() if text[-1].islower() else token.upper()
                    matched.append(f'{tok} ')

            matched.sort()
            results.extend(matched[:self.max_to_display])

        # case SENSITIVE matching for language tokens
        if 'schema' in self.tokens:
            matched = []

            for token in self.tokens['schema']:
                if token.startswith(text):
                    matched.append(f'{token} ')

            matched.sort()
            results.extend(matched[:self.max_to_display])

        results.append(None)
        return results[state]

    # def display(self, typed: str, matches: List[str], max_length: int) -> None:
    #     """
    #     Function to display matches.

    #     Displays the contents of all the matches, re-prints the prompt,
    #     and the contents of the line buffer, then call
    #     readline.redisplay.

    #     Parameters
    #     ----------
    #     typed : str
    #       TODO ...

    #     matches : List[str]
    #       TODO ...

    #     max_length : int
    #       TODO ...
    #     """
    #     # display the contents of all matches
    #     print('.display() called!')
    #     [print(match) for match in matches][:self.max_to_display]

    #     # re-print the prompt & typed characters
    #     # txt = readline.get_line_buffer()
    #     # readline.insert_text(txt)
    #     #
    #     # readline.redisplay()

    def update(self, new_tokens: Dict[str, list]) -> None:
        """
        Updates candidate tokens for autocompletion.

        Operates like dict.update():
        - if key exists, overwrite the value
        - if key DNE, add to the available tokens
        """
        self.tokens.update(new_tokens)
