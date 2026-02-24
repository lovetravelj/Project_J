from __future__ import annotations

import pandas as pd


def to_df(receipts):
    if not receipts:
        return pd.DataFrame(columns=["date", "store", "amount", "category"])
    return pd.DataFrame(receipts)


def calc_total(df):
    return int(df["amount"].sum()) if not df.empty else 0


def calc_monthly(df):
    if df.empty:
        return pd.Series(dtype=int)
    temp = df.copy()
    temp["month"] = pd.to_datetime(temp["date"]).dt.strftime("%Y-%m")
    return temp.groupby("month")["amount"].sum().sort_index()


def calc_daily(df):
    if df.empty:
        return pd.Series(dtype=int)
    return df.groupby("date")["amount"].sum().sort_index()


def calc_category(df):
    if df.empty:
        return pd.Series(dtype=int)
    return df.groupby("category")["amount"].sum().sort_values(ascending=False)


def calc_top_category(df):
    cat = calc_category(df)
    if cat.empty:
        return None, 0
    return cat.idxmax(), int(cat.max())


def summary_stats(df):
    if df.empty:
        return {
            "total_amount": 0,
            "count": 0,
            "avg_amount": 0,
            "max_amount": 0,
        }
    return {
        "total_amount": int(df["amount"].sum()),
        "count": int(len(df)),
        "avg_amount": float(df["amount"].mean()),
        "max_amount": int(df["amount"].max()),
    }
