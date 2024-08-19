import logging
import pytest
import pytest_asyncio
from hamcrest import assert_that, not_none, none

from gameserver.server import Server
from gameserver.client import Client

settings_path = "tests/settings.json"

@pytest.mark.asyncio
async def test_getting_login():
    async with Server(settings_path) as server:
        async with Client(server._settings.host, server._settings.port) as client:
            nickname = "rickastley"

            await client.send_login_request(nickname)


@pytest.mark.asyncio
async def test_logout():
    async with Server(settings_path) as server:
        async with Client(server._settings.host, server._settings.port) as client:
            nickname = "rickastley"

            await client.send_login_request(nickname)

            assert_that(client.game_session, not_none())

            await client.send_logout_request()

            assert_that(client.game_session, none())


@pytest.mark.asyncio
async def test_get_all_items(caplog):
    caplog.set_level(logging.WARNING) #  Change if you need more detailed logging

    async with Server(settings_path) as server:
        async with Client(server._settings.host, server._settings.port) as client:
            nickname = "rickastley"

            await client.send_login_request(nickname)

            assert_that(client.game_session, not_none())

            await client.send_get_all_items_request()
