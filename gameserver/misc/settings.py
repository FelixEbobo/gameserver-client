from decimal import Decimal
from pydantic import BaseModel, Field
from db.settings import DBSettings

class ServerSettings(BaseModel):
    port: int = Field(gt=0)
    items_path: str
    db_settings: DBSettings
    min_amount_of_money: Decimal = Field(gt=.0, decimal_places=2)
    max_amount_of_money: Decimal = Field(gt=.0, decimal_places=2)


def load_settings() -> ServerSettings:
    with open("settings.json", "r", encoding="utf-8") as f:
        return ServerSettings.model_validate_json(f.read())


def validate_settings() -> ServerSettings:
    settings = load_settings()
    assert settings.max_amount_of_money >= settings.min_amount_of_money
    return settings
