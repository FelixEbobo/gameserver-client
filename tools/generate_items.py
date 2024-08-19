import argparse
import random

from gameserver.misc.models import ShopItem, ShopItemList, ShopItemType


def generate(count: int, start_price: int, end_price: int) -> ShopItemList:
    result = ShopItemList([])
    ship_names = []
    equipment_names = []
    with open("ship_names.txt", "r", encoding="utf-8")as f:
        for ship_name in f.readlines():
            ship_names.append(ship_name.rstrip())

    with open("equipment_names.txt", "r", encoding="utf-8") as f:
        for equip_name in f.readlines():
            equipment_names.append(equip_name.rstrip())

    for _ in range(count):
        if random.random() <= 0.6:
            item_type = ShopItemType.SHIP
            item_name = random.choice(ship_names)
        else:
            item_type = ShopItemType.EQUIPMENT
            item_name = random.choice(equipment_names)

        result.append(ShopItem(
            name=item_name,
            price=random.randint(start_price, end_price),
            type=item_type
        ))

    return result


def main():
    parser = argparse.ArgumentParser("Item Generator")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--start-price", type=int, default=5, metavar="start_price")
    parser.add_argument("--end-price", type=int, default=100, metavar="end_price")

    args = parser.parse_args()

    item_list = generate(args.count, args.start_price, args.end_price)

    print(item_list.model_dump_json())
    with open("shop_items.json", "w", encoding="utf-8") as f:
        f.write(item_list.model_dump_json(indent=2))

if __name__ == "__main__":
    main()
