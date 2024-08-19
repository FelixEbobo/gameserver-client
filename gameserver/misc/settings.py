from decimal import Decimal
from pydantic import BaseModel, Field
from gameserver.db import DBSettings


class ServerSettings(BaseModel):
    host: str
    port: int = Field(gt=0)
    items_path: str
    db_settings: DBSettings
    min_amount_of_money: Decimal = Field(gt=0.0, decimal_places=2)
    max_amount_of_money: Decimal = Field(gt=0.0, decimal_places=2)


def load_settings(settings_path: str) -> ServerSettings:
    with open(settings_path, "r", encoding="utf-8") as f:
        return ServerSettings.model_validate_json(f.read())


def validate_settings(settings_path: str) -> ServerSettings:
    settings = load_settings(settings_path)
    assert settings.max_amount_of_money >= settings.min_amount_of_money
    return settings
