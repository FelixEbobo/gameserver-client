import argparse
import asyncio
import logging
from gameserver.client import Client
from gameserver.misc.models import ErrorResponse, ShopItemList, ShopItem

MENU_STRING = """
Please, choose desired action:
1) View account balance
2) View purchased items
3) View available items for purchase
4) Buy Item
5) Sell Item
6) Refresh game session
7) Logout
"""

def check_if_error_recieved(response) -> bool:
    if isinstance(response, ErrorResponse):
        logging.error("Error had occured!")
        logging.error(str(response))
        return True
    return False

def print_separator() -> None:
    print()
    print("----------------------")
    print()


def print_item_description(shop_item: ShopItem, index: int, owned: bool = False):
    msg = f"{index + 1}) Item name: {shop_item.name}. Price: {shop_item.price}"
    if owned: #  Check if item is owned by the account
        msg += ". Owned"
    print(msg)

async def view_shop_items(client: Client) -> ShopItemList:
    response = await client.send_get_all_items_request()
    if check_if_error_recieved(response):
        return

    owned_items_dict = client.game_session.owned_items.as_dict()

    for index, shop_item in enumerate(response):
        is_owned = owned_items_dict.get(str(shop_item.uuid)) is not None
        print_item_description(shop_item, index, is_owned)

    return response

def view_purchased_items(client: Client):
    owned_items = client.game_session.owned_items
    if len(owned_items) == 0:
        print("No purchased items")
        return

    for index, shop_item in enumerate(owned_items):
        print_item_description(shop_item, index)

async def buy_item(client: Client):
    # Refresh to get actual information at the moment
    await client.refresh_game_session()
    shop_item_list = await view_shop_items(client)

    while True:
        buy_option = input("Please, choose item you want to buy (Enter 0 to go back): ")
        if buy_option.isdigit() and int(buy_option) == 0:
            return

        if not buy_option.isdigit() or int(buy_option) < 1 or int(buy_option) > len(shop_item_list):
            logging.error(f"Your selection should be number within 1-{len(shop_item_list)} range.")
            continue

        shop_item_index = int(buy_option) - 1
        owned_items_dict = client.game_session.owned_items.as_dict()
        if (owned_items_dict.get(str(shop_item_list.at(shop_item_index).uuid))):
            logging.error(f"Your selection should be number within 1-{len(shop_item_list)} range.")
            continue
        break

    response = await client.send_buy_request(shop_item_list.at(shop_item_index).uuid)
    if check_if_error_recieved(response):
        return
    client.game_session.owned_items.append(shop_item_list.at(shop_item_index))


async def sell_item(client: Client):
    # Refresh to get actual information at the moment
    await client.refresh_game_session()
    view_purchased_items(client)
    owned_items = client.game_session.owned_items
    if len(owned_items) == 0:
        return

    while True:
        buy_option = input("Please, choose item you want to sell (Enter 0 to go back): ")
        if buy_option.isdigit() and int(buy_option) == 0:
            return

        if not buy_option.isdigit() or int(buy_option) < 1 or int(buy_option) > len(owned_items):
            logging.error(f"Your selection should be number within 1-{len(owned_items)} range.")
            continue

        shop_item_index = int(buy_option) - 1
        break

    response = await client.send_sell_request(owned_items.at(shop_item_index).uuid)
    if check_if_error_recieved(response):
        return
    owned_items.remove(owned_items.at(shop_item_index))


async def process_menu_option(client: Client, menu_option: int):
    if menu_option == 1:
        print(f"Your current balance: {client.game_session.balance} CR")

    if menu_option == 2:
        view_purchased_items(client)

    if menu_option == 3:
        await view_shop_items(client)

    if menu_option == 4:
        await buy_item(client)

    if menu_option == 5:
        await sell_item(client)

    if menu_option == 6:
        response = await client.refresh_game_session()
        if not check_if_error_recieved(response):
            print("Game session data has been refreshed")

    if menu_option == 7:
        response = await client.send_logout_request()
        check_if_error_recieved(response)

    print_separator()
    return


async def main_menu_loop(client: Client):
    while True:
        print(f"Currently logged in as: {client.game_session.nickname}, session: {str(client.game_session.session_uuid)}")
        print(MENU_STRING)

        menu_option = input("Your choise: ")
        if not menu_option.isdigit() or int(menu_option) < 1 or int(menu_option) > 7:
            input("Your selection should be number within 1-6 range. Press Enter to continue")
            continue

        menu_option_int = int(menu_option)
        await process_menu_option(client, menu_option_int)
        if menu_option_int == 7:
            break

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host", dest="host", type=str, default="localhost", required=True, help="IP address of server to connect to"
    )
    parser.add_argument(
        "--port",
        dest="port",
        type=int,
        default=3233,
        required=True,
        help="Port of server to connect to",
    )

    return parser.parse_args()

async def main(args: argparse.Namespace):
    logging.info("Welcome to basic Ship Economy game")
    async with Client(args.host, args.port) as client:
        nickname = input("Please, provide nickname to login into an account: ")

        response = await client.send_login_request(nickname)
        check_if_error_recieved(response)

        await main_menu_loop(client)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    args = parse_args()
    asyncio.run(main(args))
