from __future__ import annotations

from typing import (
    Any as Any_,
    Union,
)

from prompt_toolkit.keys import Keys as _PromptToolkitKeys
import pydantic

# Cache keys so we can allow module-level access.
_known_keys_cache: dict[str, Key] = {}


def __getattr__(key_name: str) -> Key:
    # Allow module-level access to individual keys.
    # eg. from promptique.keys import Any, Paste, Enter
    # eg. from promptique import keys    # keys.Enter
    #
    try:
        return _known_keys_cache[key_name]
    except KeyError:
        raise AttributeError(f"AttributeError: module 'promptique.keys' has no attribute '{key_name}'") from None


class Key(pydantic.BaseModel, arbitrary_types_allowed=True, frozen=True):
    """
    Represent known keys.

    Q. Why not use PromptToolkit keys.Keys?
    A. Users of our API don't necessary need to know we're using PTK under the hood.
       Additionally, PTK defines their key object as a StrEnum, which cannot be extended
       easily. We'd like to offer the same interface while defining keys against
       individual letters and numbers, or keys which have no printable representation.
       Finally, creating our own interface allows us to define aliases in our own way.
    """

    name: str
    data: str
    is_printable: bool = False

    @pydantic.model_validator(mode="before")
    @classmethod
    def _fetch_singleton_representation(cls, value: Any_) -> Any_:
        # Otherwise, aliases would override each other.
        try:
            return _known_keys_cache[value["name"]].dict()
        except KeyError:
            return value

    @pydantic.model_validator(mode="after")
    def _cache_singleton_representation(self) -> Key:
        # Cache everything except paste key events, because the data will always be different.
        if self._is_pasted_characters:
            return self

        _known_keys_cache.setdefault(self.name, self)
        return self

    @classmethod
    def letter(cls, value: str) -> Key:
        """Convert a single character into a Key."""
        if len(value) > 1:
            raise ValueError(f"You must provide only single characters, got '{value}'")

        return cls(name=value, data=value, is_printable=True)

    @classmethod
    def number(cls, value: Union[str, int]) -> Key:
        """Convert a single number into a Key."""
        value = str(value)

        if not value.isdigit() or len(value) > 1:
            raise ValueError(f"You must provide only single numbers, got '{value}'")

        return cls(name=value, data=value, is_printable=True)

    # TODO: ..maybe
    # def phrase(cls, value: str) -> Key:
    #     """Keys.phrase("match this", is_key_run=True)"""
    #

    # DEV NOTE: @boonhapus 2024/01/20
    # In order for bracketed paste to compare to itself, we special handle both __hash__
    # and __eq__ , even though in reality the two keys are not identical.
    #
    @property
    def _is_pasted_characters(self) -> bool:
        return self.name == "BracketedPaste" or self.name == "Paste"

    def __hash__(self) -> int:
        return hash("<bracketed-paste>") if self._is_pasted_characters else hash(self.data)

    def __eq__(self, other: Any_) -> bool:
        if not isinstance(other, Key):
            return False

        if self._is_pasted_characters:
            return other._is_pasted_characters

        return hash(self.data) == hash(other.data)


if not _known_keys_cache:
    # See: https://github.com/prompt-toolkit/python-prompt-toolkit/blob/master/src/prompt_toolkit/keys.py
    for key in _PromptToolkitKeys:
        _known_keys_cache[key.name] = Key(name=key.name, data=key.value)

    # DEV NOTE: @boonhapus, 2024/01/20
    # Define some semantic aliases, Key.model_validators will typically take care of the caching machinery.
    #
    _known_keys_cache[" "] = Key(name="Space", data=" ", is_printable=True)
    _known_keys_cache["Paste"] = Key(name="Paste", data=_PromptToolkitKeys.BracketedPaste.value, is_printable=True)
    _known_keys_cache["ControlH"] = Key(name="Backspace", data=_PromptToolkitKeys.Backspace.value)
    _known_keys_cache["ControlI"] = Key(name="Tab", data=_PromptToolkitKeys.Tab.value)
    _known_keys_cache["ControlM"] = Key(name="Enter", data=_PromptToolkitKeys.Enter.value)
