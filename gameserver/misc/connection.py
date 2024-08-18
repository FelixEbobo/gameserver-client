import logging
import asyncio
from typing import AsyncGenerator
from io import BytesIO
from pydantic import ValidationError

from gameserver.misc.models import ErrorResponse
from gameserver.misc.protocol import Protocol, ProtocolRequest, ProtocolResponse
from gameserver.misc import errors

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