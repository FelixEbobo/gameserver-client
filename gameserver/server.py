import asyncio
from typing import List, AsyncGenerator
import logging
import uuid
import random
from io import BytesIO

from pydantic import ValidationError

from db.manager import DBManager
from misc.settings import validate_settings
from gameserver.models import ErrorResponse, ShopItemList, AccountLoginRequest, GameSessionData, ActionType, BasicResponse, ItemRequest
from gameserver.misc import errors
from gameserver.protocol import Protocol, ProtocolRequest, ProtocolResponse

class Connection:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.reader = reader
        self.writer = writer

    async def listen(self) -> AsyncGenerator[bytes, None]:
        msglen = 0
        readlen = 0
        message = BytesIO()
        logging.debug("Begin reading")
        while True:
            msg = await self.reader.read(Protocol.CHUNK_SIZE)
            if self.reader.at_eof():
                break
            logging.debug("Read chunk")

            if len(msg) < Protocol.HEADER_TOTAL_SIZE:
                await self.send_bad_request()
                continue
            if not msg[:Protocol.HEADER_SIZE].rstrip().isdigit():
                await self.send_bad_request()
                continue

            msglen = int(msg[:Protocol.HEADER_SIZE])
            readlen += message.write(msg[Protocol.HEADER_TOTAL_SIZE:])
            while readlen < msglen:
                msg = await self.reader.read(Protocol.CHUNK_SIZE)
                readlen += message.write(msg)

            message.seek(0)
            readlen = 0
            msglen = 0
            try:
                parsed_data = Protocol.parse(message.read())
                yield ProtocolRequest.model_validate(parsed_data)
            except ValidationError:
                await self.send_bad_request()

    async def close(self) -> None:
        self.writer.write_eof()
        await self.writer.drain()
        await self.writer.wait_closed()

    async def send_bad_request(self) -> None:
        error = ErrorResponse.from_base_gameserver_exception(errors.BadRequest())
        self.writer.write(Protocol.construct(error.model_dump()))
        await self.writer.drain()

    async def send(self, response: ProtocolResponse) -> None:
        self.writer.write(Protocol.construct(response.model_dump()))
        await self.writer.drain()

class Server:
    def __init__(self) -> None:
        self._settings = validate_settings()
        self._sessions: List[Connection] = []
        self._socket = None

        self.db = DBManager(self._settings.db_settings)

    def __get_items_data(self) -> ShopItemList:
        with open(self._settings.items_path) as f:
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
        self._socket = await asyncio.start_server(self.handle_client, "localhost", 5555)
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
            logging.debug("Got new message")
            request_json = Protocol.parse(message)
            request = ProtocolRequest.model_validate(request_json)
            try:
                response = await self.action_dispatcher(request)
            except errors.BaseGameServerException as e:
                response = ErrorResponse.from_base_gameserver_exception(e)

            await conn.send(response)

        self._sessions.remove(conn)

    async def action_dispatcher(self, request: ProtocolRequest) -> ProtocolResponse:
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
            result = await self.get_game_session_data()

        return Protocol.construct(ProtocolResponse(data=result))

    async def get_all_shop_items(self) -> ShopItemList:
        async with self.db.sessionmaker() as session:
            shop_item_list = await self.db.get_shop_items_list(session)
        result: ShopItemList = []
        for shop_item in shop_item_list:
            result.append(shop_item.to_shop_item_model())

        return result

    async def login_into_account(self, params: AccountLoginRequest) -> GameSessionData:
        async with self.db.sessionmaker.begin() as session:
            account = await self.db.find_account_by_nickname(session, params.nickname)
            if not account:
                account = await self.db.create_account(session, params.nickname)
                await self.db.create_balance_record_for_account(session, account)
                random_balance = round(random.uniform(self._settings.min_amount_of_money, self._settings.max_amount_of_money), 2)
                await self.db.add_balance_to_account(session, account, random_balance)

                await session.commit()

            balance = await self.db.get_account_balance(session, account)
            account_session = await self.db.create_account_session(session, account)
            owned_shop_items = await self.db.get_user_owned_items_list(session, account)


        return GameSessionData(
            account_uuid=account.uuid,
            nickname=account.nickname,
            balance=balance.balance,
            session_uuid=account_session.uuid,
            owned_items=owned_shop_items
        )

    async def get_game_session_data(self, session_uuild: uuid.UUID) -> GameSessionData:
        async with self.db.sessionmaker() as session:
            account = await self.db.find_account_by_session(session, session_uuild)
            balance = await self.db.get_account_balance(session, account)
            account_session = await self.db.create_account_session(session, account)
            owned_shop_items = await self.db.get_user_owned_items_list(session, account)

        return GameSessionData(
            account_uuid=account.uuid,
            nickname=account.nickname,
            balance=balance.balance,
            session_uuid=account_session.uuid,
            owned_items=owned_shop_items
        )

    async def logout_from_account(self, session_uuid: uuid.UUID) -> BasicResponse:
        async with self.db.sessionmaker() as session:
            await self.db.delete_account_session(session_uuid)
        return BasicResponse()

    async def buy_shop_item(self, session_uuid: uuid.UUID, params: ItemRequest) -> BasicResponse:
        async with self.db.sessionmaker.begin() as session:
            account = await self.db.find_account_by_session(session, session_uuid)
            shop_item = await self.db.find_item_by_uuid(session, params.item_uuid)
            balance = await self.db.get_account_balance(session, account)
            if balance.balance < shop_item.price:
                raise errors.NotEnoughFundsInAccountBalance(balance.balance)

            await self.db.add_item_ownership_to_account(session, account, shop_item)
            await self.db.substitute_balance_from_account(session, account, shop_item.price)

            await session.commit()

        return BasicResponse()

    async def sell_shop_item(self, session_uuid: uuid.UUID, params: ItemRequest) -> BasicResponse:
        async with self.db.sessionmaker.begin() as session:
            account = await self.db.find_account_by_session(session, session_uuid)
            shop_item = await self.db.find_item_by_uuid(session, params.item_uuid)

            await self.db.remove_item_ownership_of_account(session, account, shop_item)
            await self.db.add_balance_to_account(session, account, shop_item.price)

            await session.commit()

        return BasicResponse()


async def main():
    import signal
    async with Server() as server:
        loop = asyncio.get_running_loop()

        # Dirty hack to run forever, as we don't have other work than to wait until server shutdown
        infinite_furute = loop.create_future()
        loop.add_signal_handler(signal.SIGINT, infinite_furute.cancel)
        loop.add_signal_handler(signal.SIGTERM, infinite_furute.cancel)
        try:
            await infinite_furute
        except asyncio.CancelledError:
            infinite_furute = None

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())