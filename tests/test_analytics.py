import pandas as pd

from analytics import to_df, calc_total, calc_daily, calc_category, calc_top_category, summary_stats


def test_analytics_basic():
    receipts = [
        {"date": "2026-02-24", "store": "A", "amount": 1000, "category": "식비"},
        {"date": "2026-02-24", "store": "B", "amount": 2000, "category": "식비"},
        {"date": "2026-02-23", "store": "C", "amount": 3000, "category": "쇼핑"},
    ]
    df = to_df(receipts)

    assert len(df) == 3
    assert calc_total(df) == 6000

    daily = calc_daily(df)
    assert daily.loc["2026-02-24"] == 3000
    assert daily.loc["2026-02-23"] == 3000

    category = calc_category(df)
    assert category.loc["식비"] == 3000
    assert category.loc["쇼핑"] == 3000

    top_cat, top_amt = calc_top_category(df)
    assert top_cat in {"식비", "쇼핑"}
    assert top_amt == 3000

    stats = summary_stats(df)
    assert stats["total_amount"] == 6000
    assert stats["count"] == 3


def test_analytics_empty():
    df = to_df([])
    assert df.empty
    assert calc_total(df) == 0
    assert calc_daily(df).empty
    assert calc_category(df).empty
    top_cat, top_amt = calc_top_category(df)
    assert top_cat is None
    assert top_amt == 0
