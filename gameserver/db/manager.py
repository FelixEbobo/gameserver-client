import logging
from typing import List, Optional
import uuid
import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession, AsyncEngine

from gameserver.misc.models import ShopItem
from gameserver.misc import errors

from gameserver.db.settings import DBSettings
from gameserver.db import tables


class DBManager:
    def __init__(self, settings: DBSettings) -> None:
        self.settings = settings
        self._engine: AsyncEngine = None
        self.sessionmaker: async_sessionmaker = None

    async def init_db_engine(self) -> None:
        if self.settings.db_type != "mysql":
            raise NotImplementedError("Unsupported DB type")

        # self._engine = create_async_engine(f"mysql+aiomysql://{self.settings.user}:{self.settings.password}@{self.settings.host}:{self.settings.port}/gmdb?charset=utf8mb4", echo=True)
        self._engine = create_async_engine(f"mysql+aiomysql://{self.settings.user}:{self.settings.password}@{self.settings.host}:{self.settings.port}/gmdb?charset=utf8mb4")
        async with self._engine.begin() as conn:
            await conn.run_sync(tables.BaseTable.metadata.drop_all)
            await conn.run_sync(tables.BaseTable.metadata.create_all)

        self.sessionmaker = async_sessionmaker(self._engine, expire_on_commit=False, class_=AsyncSession)

    async def shutdown(self) -> None:
        logging.info("Shutting down db connection")
        await self._engine.dispose()

    #  Work with shop_items

    async def add_shop_item(self, session: AsyncSession, item: ShopItem) -> None:
        result = await session.execute(select(tables.DBShopItem).where(tables.DBShopItem.name == item.name).where(tables.DBShopItem.price == item.price))
        if result.scalar():
            print(f"Item {item.name} with price {item.price} already exists!")
        else:
            item = tables.DBShopItem(name=item.name, type=item.type, price=item.price)
            session.add(item)
            await session.flush()

    async def get_shop_items_list(self, session: AsyncSession) -> List[tables.DBShopItem]:
        result: List[tables.DBShopItem] = []
        rows = await session.execute(select(tables.DBShopItem))

        for item in rows.scalars():
            result.append(item)

        return result

    async def get_user_owned_items_list(self, session: AsyncSession, account: tables.DBAccount) -> List[tables.DBShopItem]:
        rows = await session.execute(
            select(tables.DBShopItem)
                .join(tables.DBShopItem2Account, tables.DBShopItem2Account.shop_item == tables.DBShopItem.id)
                .where(tables.DBShopItem2Account.account == account.id)
            )

        result: List[tables.DBShopItem] = []
        for item in rows.scalars():
            result.append(item)

        return result

    # Work with Account Session

    async def create_account_session(self, session: AsyncSession, account: tables.DBAccount) -> tables.DBAccountSession:
        account_session = tables.DBAccountSession(account=account.id)
        session.add(account_session)
        await session.flush()
        await session.refresh(account_session)

        return account_session

    async def delete_account_session(self, session: AsyncSession, session_uuid: uuid.UUID) -> None:
        account_session = (await session.execute(select(tables.DBAccountSession).where(tables.DBAccountSession.uuid == session_uuid))).scalar()
        if not account_session:
            raise errors.AccountSessionNotFound(session_uuid)

        await session.delete(account_session)

    # Work with Account

    async def find_or_create_account(self, session: AsyncSession, nickname: str, min_money: float, max_money: float) -> tables.DBAccount:
        account = await self.find_account_by_nickname(session, nickname)
        if account:
            return account

        account = await self.create_account(session, nickname)
        await self.create_balance_record_for_account(session, account)
        random_balance = round(random.uniform(min_money, max_money), 2)
        await self.add_balance_to_account(session, account, random_balance)

        return account

    async def create_account(self, session: AsyncSession, nickname: str) -> tables.DBAccount:
        if (await session.execute(select(tables.DBAccount).where(tables.DBAccount.nickname == nickname))).scalar():
            raise errors.AccountAlreadyExists(nickname)

        new_account = tables.DBAccount(nickname=nickname)
        session.add(new_account)
        await session.flush()
        await session.refresh(new_account)

        return new_account

    async def create_balance_record_for_account(self, session: AsyncSession, account: tables.DBAccount) -> tables.DBAccountBalance:
        balance = tables.DBAccountBalance(account=account.id)
        session.add(balance)
        await session.flush()
        await session.refresh(balance)
        
        return balance

    async def find_account_by_nickname(self, session: AsyncSession, nickname: str) -> Optional[tables.DBAccount]:
        return (await session.execute(select(tables.DBAccount).where(tables.DBAccount.nickname == nickname))).scalar()

    async def find_account_by_session(self, session: AsyncSession, account_session: uuid.UUID) -> tables.DBAccount:
        db_account_session = (await session.execute(select(tables.DBAccountSession).where(tables.DBAccountSession.uuid == account_session))).scalar()
        if not db_account_session:
            raise errors.AccountSessionNotFound()

        account = (await session.execute(select(tables.DBAccount).where(tables.DBAccount.id == db_account_session.account))).scalar()
        if not account:
            raise errors.AccountNotExist()

        return account

    # Work with account balance

    async def get_account_balance(self, session: AsyncSession, account: tables.DBAccount) -> tables.DBAccountBalance:
        account_balance = (await session.execute(select(tables.DBAccountBalance).where(tables.DBAccountBalance.account == account.id))).scalar()
        if not account_balance:
            raise errors.AccountBalanceNotFound(account.id)

        return account_balance

    async def add_balance_to_account(self, session: AsyncSession, account: tables.DBAccount, amount: float) -> None:
        assert amount >= 0
        account_balance = (await session.execute(select(tables.DBAccountBalance).where(tables.DBAccountBalance.account == account.id))).scalar()
        if not account_balance:
            raise errors.AccountBalanceNotFound(account.id)

        account_balance.balance = float(account_balance.balance) + amount
        await session.flush()

    async def substitute_balance_from_account(self, session: AsyncSession, account: tables.DBAccount, amount: float) -> None:
        assert amount >= 0
        account_balance = (await session.execute(select(tables.DBAccountBalance).where(tables.DBAccountBalance.account == account.id))).scalar()
        if not account_balance:
            raise errors.AccountBalanceNotFound(account.id)

        if account_balance.balance < amount:
            raise errors.NotEnoughFundsInAccountBalance(amount)

        account_balance.balance = float(account_balance.balance) - amount
        await session.flush()

    async def set_balance_for_account(self, session: AsyncSession, account: tables.DBAccount, amount: float) -> None:
        assert amount >= 0
        account_balance = (await session.execute(select(tables.DBAccountBalance).where(tables.DBAccountBalance.account == account.id))).scalar()
        if not account_balance:
            raise errors.AccountBalanceNotFound(account.id)

        account_balance.balance = amount
        await session.flush()

    # Work with item ownership

    async def add_item_ownership_to_account(self, session: AsyncSession, account: tables.DBAccount, shop_item: tables.DBShopItem) -> None:
        shop_item2account = (await session.execute(
            select(tables.DBShopItem2Account)
                .where(tables.DBShopItem2Account.account == account.id)
                .where(tables.DBShopItem2Account.shop_item == shop_item.id)
            )).scalar()

        if shop_item2account:
            raise errors.AccountAlreadyOwnsItem(shop_item.name)

        shop_item2account = tables.DBShopItem2Account(account=account.id, shop_item=shop_item.id)
        session.add(shop_item2account)
        await session.flush()

    async def remove_item_ownership_of_account(self, session: AsyncSession, account: tables.DBAccount, shop_item: tables.DBShopItem) -> None:
        shop_item2account = (await session.execute(
            select(tables.DBShopItem2Account)
                .where(tables.DBShopItem2Account.account == account.id)
                .where(tables.DBShopItem2Account.shop_item == shop_item.id)
            )).scalar()

        if not shop_item2account:
            raise errors.AccountDoesntOwnItem(shop_item.name)

        await session.delete(shop_item2account)

    async def find_item_by_uuid(self, session: AsyncSession, item_uuid: uuid.UUID) -> tables.DBShopItem:
        shop_item = (await session.execute(select(tables.DBShopItem).where(tables.DBShopItem.uuid == item_uuid))).scalar()
        if not shop_item:
            raise errors.ShopItemNotFound(item_uuid)

        return shop_item
