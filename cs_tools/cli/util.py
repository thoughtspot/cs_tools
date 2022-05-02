import logging
import pathlib
import base64


log = logging.getLogger(__name__)


def base64_to_file(string: str, *, filepath: pathlib.Path) -> None:
    """
    Write a base64-encoded string to file.

    Parameters
    ----------
    string : str
      base64-encoded data

    filepath : pathlib.Path
      where to write the data encoded in string
    """
    # DEV NOTE:
    #
    #   This is a utility which takes data from an internal API and
    #   converts it to a base64 string, sometimes that data isn't
    #   well-formatted since we often ask the API to do something it
    #   isn't strictly designed to do.
    #
    #   The missing_padding check might not be necessary once the TML
    #   apis are public.
    #
    #   further reading: https://stackoverflow.com/a/9807138
    #
    add_padding = len(string) % 4

    if add_padding:
        log.warning(
            f'adding {add_padding} padding characters to meet the required octect '
            f'length for {filepath}'
        )
        string += '=' * add_padding

    with pathlib.Path(filepath).open(mode='wb') as file:
        file.write(base64.b64decode(string))
