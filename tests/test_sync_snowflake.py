from __future__ import annotations

import pathlib

from cs_tools.sync.base import DatabaseSyncer
from cs_tools.sync.snowflake.syncer import Snowflake
import pytest
import sqlalchemy as sa


@pytest.fixture()
def no_connect(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stop __finalize__ from opening a real connection (create_all / Session.begin)."""
    monkeypatch.setattr(DatabaseSyncer, "__finalize__", lambda *_: None)


@pytest.fixture()
def key_file(tmp_path: pathlib.Path) -> pathlib.Path:
    # pydantic.FilePath only requires the path to exist; engine construction never reads it
    # (the key is loaded lazily by the driver at connect time, which these tests do not reach).
    kf = tmp_path / "rsa_key.p8"
    kf.write_text("-----BEGIN PRIVATE KEY-----\nnot-a-real-key\n-----END PRIVATE KEY-----\n")
    return kf


def _snowflake(**overrides) -> Snowflake:
    kwargs = {
        "account_name": "acct",
        "username": "u",
        "warehouse": "w",
        "role": "r",
        "database": "d",
        "schema": "s",
        "authentication": "basic",
        "secret": "pw",
    }
    kwargs.update(overrides)
    return Snowflake(**kwargs)


@pytest.mark.usefixtures("no_connect")
def test_keypair_credentials_are_not_placed_in_the_url(key_file: pathlib.Path) -> None:
    """
    Regression guard: newer snowflake-sqlalchemy raises ArgumentError when 'private_key_file'
    is passed via the URL query string. Sensitive params must ride in connect_args on
    create_engine() instead. See snowflake.sqlalchemy.util._reject_or_warn.
    """
    syncer = _snowflake(authentication="key-pair", secret="pw", private_key_path=str(key_file))

    url = str(syncer.make_url())
    connect_args = syncer.make_connect_args()

    assert "private_key" not in url
    assert connect_args["private_key_file"] == str(key_file)
    assert connect_args["private_key_file_pwd"] == "pw"


@pytest.mark.usefixtures("no_connect")
def test_keypair_engine_builds_without_argument_error(key_file: pathlib.Path) -> None:
    """The engine must construct; the previous URL-based approach raised ArgumentError here."""
    syncer = _snowflake(authentication="key-pair", secret="pw", private_key_path=str(key_file))
    assert isinstance(syncer._engine, sa.engine.Engine)


@pytest.mark.usefixtures("no_connect")
def test_query_tag_rides_in_connect_args_not_the_url() -> None:
    """session_parameters belong in connect_args, not serialized into the URL query string."""
    syncer = _snowflake(authentication="basic", secret="pw")

    assert "connect_args" not in str(syncer.make_url())
    assert "query_tag" in syncer.make_connect_args()["session_parameters"]


@pytest.mark.usefixtures("no_connect")
@pytest.mark.parametrize("authentication", ["basic", "sso", "oauth"])
def test_non_keypair_auth_still_builds(authentication: str) -> None:
    """basic / sso / oauth are untouched by the key-pair code path and must still build cleanly."""
    secret = None if authentication == "sso" else "pw"
    syncer = _snowflake(authentication=authentication, secret=secret)

    assert isinstance(syncer._engine, sa.engine.Engine)
    assert "private_key" not in str(syncer.make_url())
