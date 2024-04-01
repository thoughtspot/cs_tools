from __future__ import annotations


def __monkeypatch_for_sqlalchemy_20() -> None:
    """
    https://github.com/snowflakedb/snowflake-sqlalchemy/issues/380#issuecomment-1470762025
    """
    import sqlalchemy.util.compat

    # make strings always return unicode strings
    sqlalchemy.util.compat.string_types = (str,)
    sqlalchemy.types.String.RETURNS_UNICODE = True

    import snowflake.sqlalchemy.snowdialect  # type: ignore[import-untyped]

    snowflake.sqlalchemy.snowdialect.SnowflakeDialect.returns_unicode_strings = True

    # make has_table() support the `info_cache` kwarg
    import snowflake.sqlalchemy.snowdialect

    def has_table(self, connection, table_name, schema=None, info_cache=None):  # noqa: ARG001
        """
        Checks if the table exists
        """
        return self._has_object(connection, "TABLE", table_name, schema)

    snowflake.sqlalchemy.snowdialect.SnowflakeDialect.has_table = has_table


__monkeypatch_for_sqlalchemy_20()
