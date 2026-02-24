from analytics import to_df, calc_total, calc_daily, calc_category, calc_top_category

sample_receipts = [
    {"date": "2026-02-24", "store": "Starbucks Gangnam", "amount": 9500, "category": "식비"},
    {"date": "2026-02-24", "store": "Metro", "amount": 1400, "category": "교통비"},
    {"date": "2026-02-23", "store": "Market", "amount": 12000, "category": "쇼핑"},
]

df = to_df(sample_receipts)
print("rows:", len(df))
print("total:", calc_total(df))
print("daily:")
print(calc_daily(df))
print("category:")
print(calc_category(df))
print("top category:", calc_top_category(df))
