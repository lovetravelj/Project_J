from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Query

from schemas import Receipt, ReceiptCreate, ReceiptStats
from analytics import to_df, calc_daily, calc_category, calc_top_category, calc_total

app = FastAPI(title="Receipt Analyzer API")

DB: List[Receipt] = []


@app.post("/api/receipts", response_model=Receipt)
def create_receipt(payload: ReceiptCreate):
    receipt = Receipt(
        id=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
        **payload.model_dump()
    )
    DB.append(receipt)
    return receipt


@app.get("/api/receipts", response_model=List[Receipt])
def list_receipts(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
):
    data = DB
    if from_date:
        data = [r for r in data if r.date >= from_date]
    if to_date:
        data = [r for r in data if r.date <= to_date]
    if category:
        data = [r for r in data if r.category == category]
    return data


@app.get("/api/receipts/stats", response_model=ReceiptStats)
def get_stats(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
):
    data = DB
    if from_date:
        data = [r for r in data if r.date >= from_date]
    if to_date:
        data = [r for r in data if r.date <= to_date]

    df = to_df([r.model_dump() for r in data])
    total_amount = calc_total(df)
    top_category, _ = calc_top_category(df)

    daily_series = calc_daily(df).reset_index().rename(columns={"date": "date", "amount": "amount"}).to_dict(orient="records")
    category_series = calc_category(df).reset_index().rename(columns={"category": "category", "amount": "amount"}).to_dict(orient="records")

    return ReceiptStats(
        total_amount=total_amount,
        count=len(df),
        top_category=top_category,
        daily_series=daily_series,
        category_series=category_series,
    )
