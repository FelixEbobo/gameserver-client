from pydantic import BaseModel, Field
from pydantic.networks import IPvAnyAddress


class DBSettings(BaseModel):
    db_type: str
    host: IPvAnyAddress
    port: int = Field(gt=0)
    user: str
    password: str #  It is better to hide this in .env file for security reasons
    is_test_env: bool
