import logging
import pytest
import pytest_asyncio
from hamcrest import assert_that, not_none, none, equal_to

from gameserver.server import Server
from gameserver.client import Client

from gameserver.misc.protocol import Protocol, ProtocolRequest
from gameserver.misc.models import ActionType, AccountLoginRequest

@pytest.mark.asyncio
async def test_getting_login():
    async with Server() as server:
        async with Client(server._settings.host, server._settings.port) as client:
            nickname = "rickastley"

            await client.send_login_request(nickname)


@pytest.mark.asyncio
async def test_logout():
    async with Server() as server:
        async with Client(server._settings.host, server._settings.port) as client:
            nickname = "rickastley"

            await client.send_login_request(nickname)

            assert_that(client.game_session, not_none())

            await client.send_logout_request()

            assert_that(client.game_session, none())


@pytest.mark.asyncio
async def test_get_all_items(caplog):
    caplog.set_level(logging.DEBUG)
    async with Server() as server:
        async with Client(server._settings.host, server._settings.port) as client:
            nickname = "rickastley"

            await client.send_login_request(nickname)

            assert_that(client.game_session, not_none())

            await client.send_get_all_items_request()

            await client.connection.close()