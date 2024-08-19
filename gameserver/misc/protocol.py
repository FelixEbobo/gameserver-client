import base64
from typing import Optional, Union, Dict, Any
import json
import uuid
from decimal import Decimal

from pydantic import BaseModel, UUID4

from gameserver.misc.models import (
    ActionType,
    ItemRequest,
    AccountLoginRequest,
    GameSessionData,
    ShopItemList,
    ErrorResponse,
    BasicResponse,
)


class ProtocolRequest(BaseModel):
    action_type: ActionType
    session_uuid: Optional[UUID4]
    data: Union[ItemRequest, AccountLoginRequest, None]


class ProtocolResponse(BaseModel):
    data: Union[GameSessionData, BasicResponse, ShopItemList, ErrorResponse]


class Protocol:
    HEADER_SIZE = 10
    HEADER_TOTAL_SIZE = 16  # number with padding + "header" itself
    CHUNK_SIZE = 64

    @staticmethod
    def parse(data: bytes) -> bytes:
        return base64.b64decode(data)

    @staticmethod
    def construct(data: Dict[str, Any]) -> bytes:
        class JSONEnconderMonkeyPatch(json.JSONEncoder):
            def default(self, o):
                if isinstance(o, uuid.UUID):
                    # if the obj is uuid, we simply return the value of uuid
                    return o.hex
                if isinstance(o, Decimal):
                    # if the obj is uuid, we simply return the value of uuid
                    o: Decimal
                    return float(o)
                return json.JSONEncoder.default(self, o)

        msg = base64.b64encode(json.dumps(data, cls=JSONEnconderMonkeyPatch).encode("utf-8"))
        return f"{len(msg):<{Protocol.HEADER_SIZE}}HEADER".encode("utf-8") + msg
