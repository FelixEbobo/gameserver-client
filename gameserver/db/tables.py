import datetime
import uuid

from sqlalchemy import String, Enum, Uuid, DateTime, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.sql import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from gameserver.misc.models import ShopItemType, ShopItem


#  Do not put id column definition, as it gets dragged to the end in DBMS. Embrace breaking DRY
class BaseTable(AsyncAttrs, DeclarativeBase):

    __table_args__ = {
        "mysql_engine": 'InnoDB',
        "mysql_charset": 'utf8mb4'
    }


class DBShopItem(BaseTable):
    __tablename__ = "gm_shop_item"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[Uuid] = mapped_column(Uuid, unique=True, nullable=False, default=uuid.uuid4)
    type: Mapped[ShopItemType] = mapped_column(Enum(ShopItemType))
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    price: Mapped[int] = mapped_column(nullable=False)

    UniqueConstraint(type, name, price, name="uix_1")

    def to_shop_item_model(self) -> ShopItem:
        return ShopItem(
            uuid=self.uuid,
            name=self.name,
            type=self.type,
            price=self.price
        )


class DBAccount(BaseTable):
    __tablename__ = "gm_account"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[Uuid] = mapped_column(Uuid, unique=True, nullable=False, default=uuid.uuid4)
    nickname: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)


class DBAccountSession(BaseTable):
    __tablename__ = "gm_account_session"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[Uuid] = mapped_column(Uuid, unique=True, nullable=False, default=uuid.uuid4)
    created: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=False), server_default=func.now())
    account: Mapped[int] = mapped_column(ForeignKey(DBAccount.id))


#  Make balance separate table as in real world you probably take billing data from another service
class DBAccountBalance(BaseTable):
    __tablename__ = "gm_account_balance"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account: Mapped[int] = mapped_column(ForeignKey(DBAccount.id), unique=True)
    balance: Mapped[float] = mapped_column(Numeric(precision=2), default=.0)


class DBShopItem2Account(BaseTable):
    __tablename__ = "gm_shop_item2account"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    account: Mapped[int] = mapped_column(ForeignKey(DBAccount.id))
    shop_item: Mapped[int] = mapped_column(ForeignKey(DBShopItem.id))

    UniqueConstraint(account, shop_item, name="uix_1")
