import base64
from typing import Optional, Union, Dict, Any
import json

from pydantic import BaseModel, UUID4

from gameserver.misc.models import ActionType, ItemRequest, AccountLoginRequest, GameSessionData, ShopItemList, ErrorResponse, BasicResponse

class ProtocolRequest(BaseModel):
    action_type: ActionType
    session_uuid: Optional[UUID4]
    data: Union[ItemRequest, AccountLoginRequest, None]

class ProtocolResponse(BaseModel):
    data: Union[GameSessionData, BasicResponse, ShopItemList, ErrorResponse]

class Protocol:
    HEADER_SIZE = 10
    HEADER_TOTAL_SIZE = 16 # number with padding + "header" itself
    CHUNK_SIZE = 64

    @staticmethod
    def parse(data: bytes) -> Dict[str, Any]:
        return json.loads(base64.b64decode(data))

    @staticmethod
    def construct(data: Dict[str, Any]) -> bytes:
        msg = base64.b64encode(json.dumps(data).encode("utf-8"))
        return f"{len(msg):<{Protocol.HEADER_SIZE}}HEADER".encode("utf-8") + msg