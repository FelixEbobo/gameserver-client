import asyncio
import logging
from gameserver.server import Server

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
