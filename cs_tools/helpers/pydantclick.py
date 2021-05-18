from typing import Union, Dict, List, Any

from pydantic import BaseModel, ValidationError
import typer


# typer doesn't yet support pydantic types natively, but it's planned. We can
# shim them together with _validate_args()
#
# https://github.com/tiangolo/typer/issues/77
# https://github.com/tiangolo/typer/issues/111
#

JSONMapping = Dict[str, Any]
JSONArray = List[Any]
JSONType = Union[JSONMapping, JSONArray]


def _validate_args(data: JSONType, model: BaseModel) -> None:
    """
    Validates provided arguments against custom types.

    Used as the first line in a CLI command. typer doesn't yet support
    custom types, so we need to back our way into it via this.

    Parameters
    ----------
    data : JSONType
      data to validate against the model

    model : pydantic.BaseModel
      validator to use against the data

    Returns
    -------
    model : pydantic.BaseModel
    """
    try:
        return model(**data)
    except ValidationError as e:
        typer.echo(e)
        raise typer.Exit()
