import asyncio
import logging
from typing import Union
import uuid

from gameserver.misc.connection import Connection
from gameserver.misc.protocol import Protocol, ProtocolRequest, ProtocolResponse, BasicResponse, ErrorResponse
from gameserver.misc.models import ActionType, AccountLoginRequest, GameSessionData, ItemRequest, ShopItemList


class Client:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.game_session: GameSessionData = None
        self.connection: Connection = None

    async def __aenter__(self):
        # Open Socket to serve connections
        reader, writer = await asyncio.open_connection(self.host, self.port)
        self.connection = Connection(reader, writer)

        return self

    async def __aexit__(self, exc_type, exc_value, exc_tb):
        await self.connection.close()

    async def send_request(self, request: ProtocolRequest):
        bytes_message = Protocol.construct(request.model_dump(mode="json"))
        await self.connection.send(bytes_message)

    async def get_response(self) -> ProtocolResponse:
        async for message in self.connection.listen():
            logging.debug("Got a response from server")
            logging.debug(message)
            response = ProtocolResponse.model_validate_json(message, strict=True)
            break
        return response

    async def send_login_request(self, nickname: str) -> Union[GameSessionData, ErrorResponse]:
        request = ProtocolRequest(
            action_type=ActionType.LOGIN, session_uuid=None, data=AccountLoginRequest(nickname=nickname)
        )
        await self.send_request(request)

        response = await self.get_response()
        logging.debug(response)
        assert not isinstance(response.data, BasicResponse)
        if isinstance(response.data, GameSessionData):
            self.game_session = response.data

    async def send_logout_request(self) -> Union[BasicResponse, ErrorResponse]:
        assert self.game_session
        request = ProtocolRequest(action_type=ActionType.LOGOUT, session_uuid=self.game_session.session_uuid, data=None)
        await self.send_request(request)

        response = await self.get_response()
        self.game_session = None
        return response.data

    async def send_buy_request(self, item_uuid: uuid.UUID) -> Union[BasicResponse, ErrorResponse]:
        assert self.game_session
        request = ProtocolRequest(
            action_type=ActionType.BUY_ITEM,
            session_uuid=self.game_session.session_uuid,
            data=ItemRequest(item_uuid=item_uuid),
        )
        await self.send_request(request)

        response = await self.get_response()
        return response.data

    async def send_sell_request(self, item_uuid: uuid.UUID) -> Union[BasicResponse, ErrorResponse]:
        assert self.game_session
        request = ProtocolRequest(
            action_type=ActionType.SELL_ITEM,
            session_uuid=self.game_session.session_uuid,
            data=ItemRequest(item_uuid=item_uuid),
        )
        await self.send_request(request)

        response = await self.get_response()
        return response.data

    async def send_get_all_items_request(self) -> Union[ShopItemList, ErrorResponse]:
        logging.debug("Sending get items info request")
        assert self.game_session
        request = ProtocolRequest(
            action_type=ActionType.GET_ALL_ITEM_LIST, session_uuid=self.game_session.session_uuid, data=None
        )
        logging.debug(request)
        await self.send_request(request)

        response = await self.get_response()
        return response.data

    async def refresh_game_session(self) -> Union[GameSessionData, ErrorResponse]:
        assert self.game_session
        request = ProtocolRequest(
            action_type=ActionType.GET_GAME_DATA_SESSION, session_uuid=self.game_session.session_uuid, data=None
        )
        await self.send_request(request)

        response = await self.get_response()
        if isinstance(response.data, GameSessionData):
            self.game_session = response.data
