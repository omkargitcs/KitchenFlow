from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

OrderStatus = Literal["placed", "preparing", "ready", "completed", "cancelled"]


class MenuItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=50)
    price_cents: int = Field(gt=0)
    stock: int = Field(ge=0, default=0)
    low_stock_threshold: int = Field(ge=0, default=5)


class MenuItemUpdate(BaseModel):
    price_cents: int | None = Field(default=None, gt=0)
    stock: int | None = Field(default=None, ge=0)
    is_available: bool | None = None


class MenuItemOut(MenuItemCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_available: bool


class OrderLineIn(BaseModel):
    menu_item_id: int
    quantity: int = Field(gt=0, le=50)


class OrderCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=100)
    items: list[OrderLineIn] = Field(min_length=1)


class OrderLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    menu_item_id: int
    quantity: int
    unit_price_cents: int


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_name: str
    status: OrderStatus
    total_cents: int
    created_at: datetime
    items: list[OrderLineOut]


class StatusUpdate(BaseModel):
    status: OrderStatus
