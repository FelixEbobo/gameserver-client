import argparse
import asyncio
import logging
from gameserver.client import Client
from gameserver.misc.models import ErrorResponse, ShopItemList, ShopItem

MENU_STRING = """
Please, choose desired action:
1) View account balance
2) View available items for purchase
3) Buy Item
4) Sell Item
5) Refresh game session
6) Logout
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

async def print_shop_items(client: Client):
    response = await client.send_get_all_items_request()
    if check_if_error_recieved(response):
        return

    logging.debug(response)

    owned_items_dict = client.game_session.owned_items.as_dict()

    def print_item_description(shop_item: ShopItem):
        msg = f"Item name: {shop_item.name}. Price: {shop_item.price}"
        if owned_items_dict.get(str(shop_item.uuid)) is not None: #  Check if item is owned by the account
            msg += ". Owned"
        print(msg)

    for shop_item in response:
        print_item_description(shop_item)

async def process_menu_option(client: Client, menu_option: int):
    if menu_option == 1:
        print(f"Your current balance: {client.game_session.balance} CR")

    if menu_option == 2:
        await print_shop_items(client)

    if menu_option == 6:
        response = await client.send_logout_request()
        check_if_error_recieved(response)

    print_separator()
    return


async def main_menu_loop(client: Client):
    while True:
        print(f"Currently logged in as: {client.game_session.nickname}, session: {str(client.game_session.session_uuid)}")
        print(MENU_STRING)

        menu_option = input("Your choise: ")
        if not menu_option.isdigit() or int(menu_option) < 1 or int(menu_option) > 6:
            input("Your selection should be number within 1-6 range. Press Enter to continue")
            continue

        menu_option_int = int(menu_option)
        await process_menu_option(client, menu_option_int)
        if menu_option_int == 6:
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
    logging.basicConfig(level=logging.INFO)
    args = parse_args()
    asyncio.run(main(args))
