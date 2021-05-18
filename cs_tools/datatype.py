from typing import Union, Any

from pydantic import BaseModel


JSONType = dict[str, Any]


class Table(BaseModel):
    """
    Representation of a ThoughtSpot table.
    """
    guid: str
    name: str = None
    author: str = None
    author_display_name: str = None
    database_stripe: str = None
    owner_guid: str = None
    is_deleted: bool = None
    is_external: bool = None
    is_hidden: bool = None
    schema_stripe: str = None
    type: str = None

    @property
    def qualified_name(self):
        """
        TODO:

        <db>.<schema>.<name>
        """
        db = self.database_stripe or ''
        schema = self.schema_stripe or ''
        name = self.name or 'unknown'
        return '.'.join(filter(None, [db, schema, name]))

    @classmethod
    def from_json(cls, json_obj: Union[str, JSONType]):
        """
        Build a Table from json.
        """
        if isinstance(json_obj, str):
            return cls.parse_raw(json_obj)
        return cls.parse_obj(json_obj)

    # TODO:
    #
    # def __repr__(self):
    #     pass
