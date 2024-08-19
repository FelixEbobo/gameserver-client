import asyncio
import logging
from typing import List
import uuid

from gameserver.db.manager import DBManager
from gameserver.misc.settings import validate_settings
from gameserver.misc.models import (
    ErrorResponse,
    ShopItemList,
    AccountLoginRequest,
    GameSessionData,
    ActionType,
    BasicResponse,
    ItemRequest,
)
from gameserver.misc import errors
from gameserver.misc.protocol import Protocol, ProtocolRequest, ProtocolResponse
from gameserver.misc.connection import Connection


class Server:
    def __init__(self, settings_path = "settings.json") -> None:
        self._settings = validate_settings(settings_path)
        self._sessions: List[Connection] = []
        self._socket = None

        self.db = DBManager(self._settings.db_settings)

    def __get_items_data(self) -> ShopItemList:
        with open(self._settings.items_path, encoding="utf-8") as f:
            return ShopItemList.model_validate_json(f.read())

    async def add_new_data_to_items(self, shop_items: ShopItemList) -> None:
        async with self.db.sessionmaker.begin() as session:
            for shop_item in shop_items:
                await self.db.add_shop_item(session, shop_item)

        async with self.db.sessionmaker.begin() as session:
            result = await self.db.get_shop_items_list(session)
            for item in result:
                print(item.uuid, item.name, item.price, sep=" | ")

    async def __aenter__(self):
        # Open DB connection
        await self.db.init_db_engine()
        # Parse Items Data
        shop_items = self.__get_items_data()
        await self.add_new_data_to_items(shop_items)

        # Open Socket to serve connections
        self._socket = await asyncio.start_server(self.handle_client, self._settings.host, self._settings.port)
        await self._socket.start_serving()

        return self

    async def __aexit__(self, exc_type, exc_value, exc_tb):
        # Send all clients a close request
        for conn in self._sessions:
            await conn.close()

        # Close Socket
        self._socket.close()
        await self._socket.wait_closed()

        # Close DB connection
        await self.db.shutdown()

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        logging.info("Got a new connection")
        conn = Connection(reader, writer)
        self._sessions.append(conn)

        async for message in conn.listen():
            logging.debug("Got a new message")
            logging.debug(message)
            request = ProtocolRequest.model_validate_json(message)
            try:
                response = await self.action_dispatcher(request)
            except errors.BaseGameServerException as e:
                response = ProtocolResponse(data=ErrorResponse.from_base_gameserver_exception(e))

            await conn.send(Protocol.construct(response.model_dump()))

        logging.info("Connection closed, removing it from sessions")
        await conn.close()
        self._sessions.remove(conn)

    # It would be better if Dispatcher was a class, where you can register handler using decorator
    async def action_dispatcher(self, request: ProtocolRequest) -> ProtocolResponse:
        logging.info("Dispatching action %s", request.action_type.value)
        if request.action_type == ActionType.LOGIN:
            result = await self.login_into_account(request.data)
        elif request.action_type == ActionType.LOGOUT:
            result = await self.logout_from_account(request.session_uuid)
        elif request.action_type == ActionType.BUY_ITEM:
            result = await self.buy_shop_item(request.session_uuid, request.data)
        elif request.action_type == ActionType.SELL_ITEM:
            result = await self.sell_shop_item(request.session_uuid, request.data)
        elif request.action_type == ActionType.GET_ALL_ITEM_LIST:
            result = await self.get_all_shop_items()
        elif request.action_type == ActionType.GET_GAME_DATA_SESSION:
            result = await self.get_game_session_data(request.session_uuid)
        else:
            result = ProtocolResponse(data=ErrorResponse.from_base_gameserver_exception(errors.UnknownActionType()))

        return ProtocolResponse(data=result)

    async def get_all_shop_items(self) -> ShopItemList:
        logging.info("Begin retrieving all shop items")
        async with self.db.sessionmaker() as session:
            shop_item_list = await self.db.get_shop_items_list(session)
        result = ShopItemList([])
        for shop_item in shop_item_list:
            result.append(shop_item.to_shop_item_model())

        return result

    async def get_owned_shop_items(self, sessio_uuid: uuid.UUID) -> ShopItemList:
        async with self.db.sessionmaker() as session:
            account = await self.db.find_account_by_session(session, sessio_uuid)
            shop_item_list = await self.db.get_user_owned_items_list(session, account)
        result = ShopItemList([])
        for shop_item in shop_item_list:
            result.append(shop_item.to_shop_item_model())

        return result

    #  Creates account and its dependencies. Then returns account session

    async def login_into_account(self, params: AccountLoginRequest) -> GameSessionData:
        async with self.db.sessionmaker.begin() as session:
            account = await self.db.find_or_create_account(
                session,
                params.nickname,
                float(self._settings.min_amount_of_money),
                float(self._settings.max_amount_of_money),
            )
            account_session = await self.db.create_account_session(session, account)

        return await self.get_game_session_data(account_session.uuid)

    async def get_game_session_data(self, session_uuild: uuid.UUID) -> GameSessionData:
        async with self.db.sessionmaker() as session:
            account = await self.db.find_account_by_session(session, session_uuild)
            balance = await self.db.get_account_balance(session, account)
            owned_shop_items = await self.db.get_user_owned_items_list(session, account)

        result = ShopItemList([])
        for shop_item in owned_shop_items:
            result.append(shop_item.to_shop_item_model())

        return GameSessionData(
            account_uuid=account.uuid,
            nickname=account.nickname,
            balance=balance.balance,
            session_uuid=session_uuild,
            owned_items=result,
        )

    async def logout_from_account(self, session_uuid: uuid.UUID) -> BasicResponse:
        async with self.db.sessionmaker.begin() as session:
            await self.db.delete_account_session(session, session_uuid)
        return BasicResponse(status="ok")

    async def buy_shop_item(self, session_uuid: uuid.UUID, params: ItemRequest) -> BasicResponse:
        async with self.db.sessionmaker.begin() as session:
            account = await self.db.find_account_by_session(session, session_uuid)
            shop_item = await self.db.find_item_by_uuid(session, params.item_uuid)
            balance = await self.db.get_account_balance(session, account)
            if balance.balance < shop_item.price:
                raise errors.NotEnoughFundsInAccountBalance(balance.balance)

            await self.db.add_item_ownership_to_account(session, account, shop_item)
            await self.db.substitute_balance_from_account(session, account, shop_item.price)

        return BasicResponse(status="ok")

    async def sell_shop_item(self, session_uuid: uuid.UUID, params: ItemRequest) -> BasicResponse:
        async with self.db.sessionmaker.begin() as session:
            account = await self.db.find_account_by_session(session, session_uuid)
            shop_item = await self.db.find_item_by_uuid(session, params.item_uuid)

            await self.db.remove_item_ownership_of_account(session, account, shop_item)
            await self.db.add_balance_to_account(session, account, shop_item.price)

        return BasicResponse(status="ok")

    async def change_account_balace(self, session_uuid: uuid.UUID, new_balance: float) -> BasicResponse:
        async with self.db.sessionmaker.begin() as session:
            account = await self.db.find_account_by_session(session, session_uuid)
            await self.db.set_balance_for_account(session, account, new_balance)

        return BasicResponse(status="ok")
