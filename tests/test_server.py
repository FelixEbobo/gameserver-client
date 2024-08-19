import random

import pytest
from hamcrest import assert_that, equal_to, is_not, has_item, has_properties, instance_of

from gameserver.server import Server
from gameserver.misc.models import AccountLoginRequest, ItemRequest, GameSessionData, ShopItemList
from gameserver.misc.errors import (
    AccountSessionNotFound,
    BaseGameServerException,
    NotEnoughFundsInAccountBalance,
    AccountAlreadyOwnsItem,
    AccountDoesntOwnItem,
)
from gameserver.misc.protocol import Protocol, ProtocolResponse

SETTINGS_PATH = "tests/settings.json"


@pytest.mark.asyncio
async def test_getting_login():
    async with Server(SETTINGS_PATH) as server:
        login_request = AccountLoginRequest(nickname="rickastley")

        game_session_data_1 = await server.login_into_account(login_request)

        game_session_data_2 = await server.login_into_account(login_request)

        # Check that it is the same user
        assert_that(game_session_data_1.account_uuid, equal_to(game_session_data_2.account_uuid))

        # Check that they have different sessions (i.e. authentication)
        assert_that(game_session_data_1.session_uuid, is_not(equal_to(game_session_data_2.session_uuid)))

        # Check that balance adding worked only once
        assert_that(game_session_data_1.balance, equal_to(game_session_data_2.balance))


@pytest.mark.asyncio
async def test_logout():
    async with Server(SETTINGS_PATH) as server:
        login_request = AccountLoginRequest(nickname="rickastley")

        game_session_data = await server.login_into_account(login_request)
        await server.logout_from_account(game_session_data.session_uuid)
        try:
            await server.get_game_session_data(game_session_data.session_uuid)
        except BaseGameServerException as e:
            assert_that(isinstance(e, AccountSessionNotFound))


@pytest.mark.asyncio
async def test_get_all_item_list():
    async with Server(SETTINGS_PATH) as server:
        shop_item_list = await server.get_all_shop_items()
        Protocol.construct(ProtocolResponse(data=shop_item_list).model_dump())


@pytest.mark.asyncio
async def test_buy_item():
    async with Server(SETTINGS_PATH) as server:
        login_request = AccountLoginRequest(nickname="rickastley")

        game_session_data = await server.login_into_account(login_request)
        shop_item_list = await server.get_all_shop_items()

        shop_item = random.choice(shop_item_list.root)

        # Remove account balance add credits random
        await server.change_account_balace(game_session_data.session_uuid, float(shop_item.price))

        game_session_data = await server.get_game_session_data(game_session_data.session_uuid)

        await server.buy_shop_item(game_session_data.session_uuid, ItemRequest(item_uuid=shop_item.uuid))
        await server.get_game_session_data(game_session_data.session_uuid)

        owned_item_list = await server.get_owned_shop_items(game_session_data.session_uuid)
        assert_that(owned_item_list, has_item(has_properties(uuid=shop_item.uuid, price=shop_item.price)))

        try:
            await server.buy_shop_item(game_session_data.session_uuid, ItemRequest(item_uuid=shop_item.uuid))
        except BaseGameServerException as e:
            assert_that(isinstance(e, NotEnoughFundsInAccountBalance))

        await server.change_account_balace(game_session_data.session_uuid, float(shop_item.price))

        try:
            await server.buy_shop_item(game_session_data.session_uuid, ItemRequest(item_uuid=shop_item.uuid))
        except BaseGameServerException as e:
            assert_that(isinstance(e, AccountAlreadyOwnsItem))


@pytest.mark.asyncio
async def test_sell_item():
    async with Server(SETTINGS_PATH) as server:
        login_request = AccountLoginRequest(nickname="rickastley")

        game_session_data = await server.login_into_account(login_request)
        shop_item_list = await server.get_all_shop_items()

        shop_item = random.choice(shop_item_list.root)

        # Remove account balance add credits random
        await server.change_account_balace(game_session_data.session_uuid, float(shop_item.price))

        await server.buy_shop_item(game_session_data.session_uuid, ItemRequest(item_uuid=shop_item.uuid))

        owned_item_list = await server.get_owned_shop_items(game_session_data.session_uuid)
        assert_that(owned_item_list, has_item(has_properties(uuid=shop_item.uuid, price=shop_item.price)))

        await server.sell_shop_item(game_session_data.session_uuid, ItemRequest(item_uuid=shop_item.uuid))

        owned_item_list = await server.get_owned_shop_items(game_session_data.session_uuid)
        assert_that(owned_item_list, is_not(has_item(has_properties(uuid=shop_item.uuid, price=shop_item.price))))

        try:
            await server.sell_shop_item(game_session_data.session_uuid, ItemRequest(item_uuid=shop_item.uuid))
        except BaseGameServerException as e:
            assert_that(isinstance(e, AccountDoesntOwnItem))


def test_validate():
    # pylint: disable=line-too-long
    game_session_data_json = '{"data": {"account_uuid": "099e9d9c79c54a2397c8904ad903e833", "nickname": "nick", "balance": 13.52, "session_uuid": "5572db08071748bca85924bbf2cbc3fe", "owned_items": [{"uuid": "1f1ecd78d8ef4067979b38b9a4be33ee", "name": "Sampson", "price": 24, "type": "ship"}]}}'
    game_session_data = ProtocolResponse.model_validate_json(game_session_data_json, strict=True)
    assert_that(game_session_data.data, instance_of(GameSessionData))

    shop_item_list_json = (
        '[{"uuid": "1f1ecd78d8ef4067979b38b9a4be33ee", "name": "Sampson", "price": 24, "type": "ship"}]'
    )
    shop_item_list = ShopItemList.model_validate_json(shop_item_list_json)
    assert_that(shop_item_list, instance_of(ShopItemList))

    # pylint: disable=protected-access
    shop_item_list_json = '[{"uuid": "1f1ecd78d8ef4067979b38b9a4be33ee", "name": "Sampson", "price": 24, "type": "ship"}, {"uuid": "1cd5dc973a2f48b19c170558d7c4550e", "name": "garbage can", "price": 43, "type": "equipment"}]'
    shop_item_list = ShopItemList.model_validate_json(shop_item_list_json)
    assert_that(shop_item_list, instance_of(ShopItemList))
