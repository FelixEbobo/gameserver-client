from decimal import Decimal
import enum
from typing import List, Optional, Generator, Union, Literal, Dict

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

class ShopItemType(str, enum.Enum):
    SHIP = "ship"
    EQUIPMENT = "equipment"

class ShopItem(BaseModel):
    uuid: Optional[UUID4] = Field(default=None)
    name: str
    price: int
    type: ShopItemType

class ShopItemList(RootModel):
    root: List[ShopItem]

    def append(self, el: ShopItem) -> None:
        self.root.append(el)

    def as_dict(self) -> Dict[str, ShopItem]:
        result = {}
        for shop_item in self.root:
            result[str(shop_item.uuid)] = shop_item
        return result

    # Probably should've used mixins
    def at(self, index: int) -> ShopItem:
        return self.root[index]

    def remove(self, value: ShopItem) -> None:
        self.root.remove(value)

    def __iter__(self) -> Generator[ShopItem, None, None]:
        yield from self.root

    def __len__(self) -> int:
        return len(self.root)

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
    value: Union[str, int, float, None]

    @staticmethod
    def from_base_gameserver_exception(exception: BaseGameServerException):
        return ErrorResponse(
            error_code=exception.code,
            message=exception.message,
            value=exception.value
        )

    def __str__(self) -> str:
        value = " " + str(self.value) if self.value else ""
        return f"Error code: {self.error_code}. Message: {self.message}{value}"
