from pydantic import BaseModel


class Settings(BaseModel):
    """
    Base class for settings management and validation.
    """


class APIParameters(Settings):
    """
    Base class for API parameter validation.
    """
