from __future__ import annotations

from datetime import datetime, date
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

Category = Literal[
    "식비",
    "교통비",
    "쇼핑",
    "엔터테인먼트",
    "의료",
    "교육",
    "기타",
]


class ReceiptItem(BaseModel):
    name: str = Field(..., description="Item name")
    qty: int = Field(1, ge=1, description="Quantity")
    price: int = Field(..., ge=0, description="Item price")


class ReceiptBase(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    store: str = Field(..., description="Store name")
    amount: int = Field(..., ge=0, description="Total amount")
    category: Category
    items: Optional[List[ReceiptItem]] = None
    raw_text: Optional[str] = None
    source: Optional[Literal["manual", "ocr", "api"]] = "manual"


class ReceiptCreate(ReceiptBase):
    pass


class Receipt(ReceiptBase):
    id: str = Field(..., description="UUID")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ReceiptStats(BaseModel):
    total_amount: int
    count: int
    top_category: Optional[str] = None
    daily_series: List[dict]
    category_series: List[dict]
