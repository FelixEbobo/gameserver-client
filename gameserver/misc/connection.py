import logging
import asyncio
from typing import AsyncGenerator, Dict, Any
from io import BytesIO
from pydantic import ValidationError

from gameserver.misc.models import ErrorResponse
from gameserver.misc.protocol import Protocol, ProtocolResponse
from gameserver.misc import errors

class Connection:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.reader = reader
        self.writer = writer
        self.is_closed = False

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
                message.truncate(0)
                continue
            if not msg[:Protocol.HEADER_SIZE].rstrip().isdigit():
                await self.send_bad_request()
                message.truncate(0)
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
                parsed_bytes = Protocol.parse(message.read())
                yield parsed_bytes
            except ValidationError:
                await self.send_bad_request()
            finally:
                message.truncate(0)

    async def close(self) -> None:
        if self.is_closed:
            return

        try:
            self.reader.feed_eof()
            self.writer.write_eof()
            await self.writer.drain()
        except ConnectionResetError:
            pass
        self.writer.close()
        await self.writer.wait_closed()
        self.is_closed = True

    async def send_bad_request(self) -> None:
        error = ProtocolResponse(data=ErrorResponse.from_base_gameserver_exception(errors.BadRequest()))
        self.writer.write(Protocol.construct(error.model_dump()))
        await self.writer.drain()

    async def send(self, response: bytes) -> None:
        self.writer.write(response)
        await self.writer.drain()