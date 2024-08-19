import argparse
import asyncio
import logging
import signal
from gameserver.server import Server


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--settings-path",
        dest="settings_path",
        type=str,
        default="settings.json",
        help="Path to the server settings",
    )

    return parser.parse_args()


async def main():
    args = parse_args()
    async with Server(args.settings_path):
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
