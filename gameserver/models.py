from decimal import Decimal
import enum
from typing import List, Optional, Generator, Union, Literal

from gameserver.misc.errors import BaseGameServerException
from pydantic import BaseModel, RootModel, Field, UUID4

# Requests

class ActionType(str, enum.Enum):
    GET_ALL_ITEM_LIST = "get_all_item_list"
    GET_GAME_DATA_SESSION = "get_game_data_session"
    LOGIN = "login"
    LOGOUT = "logout"
    BUY_ITEM = "buy_item"
    SELL_ITEM = "sell_item"

class ItemRequest(BaseModel):
    item_uuid: UUID4

class AccountLoginRequest(BaseModel):
    nickname: str = Field(max_length=12)

# Responses

class ShopItemType(enum.Enum):
    SHIP = "ship"
    EQUIPMENT = "equipment"

class ShopItem(BaseModel):
    uuid: Optional[UUID4]
    name: str
    price: int
    type: ShopItemType

class ShopItemList(RootModel):
    root: List[ShopItem]

    def append(self, el: ShopItem) -> None:
        self.root.append(el)

    def __iter__(self) -> Generator[ShopItem, None, None]:
        yield from self.root

class BasicResponse(BaseModel):
    status: Literal["ok"]

class GameSessionData(BaseModel):
    account_uuid: UUID4
    nickname: str = Field(max_length=12)
    balance: Decimal = Field(decimal_places=2)
    session_uuid: UUID4
    owned_items: ShopItemList

class ErrorResponse(BaseModel):
    error_code: int
    message: str
    value: Union[str, int, None]

    @staticmethod
    def from_base_gameserver_exception(exception: BaseGameServerException):
        return ErrorResponse(
            error_code=exception.code,
            message=exception.message,
            value=exception.value
        )
