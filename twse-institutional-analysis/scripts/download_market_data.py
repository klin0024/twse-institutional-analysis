"""
下載大盤指數（TAIEX）、個股（預設台積電 2330）與美元/新台幣匯率，
作為三大法人買賣超分析的佐證資料。

來源：
- TAIEX 加權指數：https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK（逐月）
- 個股日成交資訊：https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY（逐月）
- 美元/新台幣匯率：Yahoo Finance TWD=X 歷史資料（逐日）

用法：
  python download_market_data.py --start 2025-07-01 --end 2026-07-01 --outdir market_data
  python download_market_data.py --start 2025-07-01 --end 2026-07-01 --stock 2330 --outdir market_data
"""

import argparse
import csv
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.twse.com.tw/zh/trading/historical/fmtqik.html",
}

TWSE_FMTQIK = "https://www.twse.com.tw/rwd/zh/afterTrading/FMTQIK"
TWSE_STOCK_DAY = "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY"
YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/TWD=X"


def month_starts(start: date, end: date):
    cur = date(start.year, start.month, 1)
    while cur <= end:
        yield cur
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)


def roc_date_to_iso(roc_str: str) -> str:
    """'115/06/01' -> '2026-06-01'"""
    y, m, d = roc_str.split("/")
    return f"{int(y) + 1911:04d}-{int(m):02d}-{int(d):02d}"


def fetch_taiex_month(month_start: date) -> list[dict]:
    params = {"response": "json", "date": month_start.strftime("%Y%m01")}
    r = requests.get(TWSE_FMTQIK, params=params, headers=HEADERS, timeout=15)
    r.raise_for_status()
    payload = r.json()
    if payload.get("stat") != "OK":
        return []
    rows = []
    for rec in payload["data"]:
        iso_date, vol_shares, vol_amt, tx_count, index_close, change = rec
        rows.append({
            "日期": roc_date_to_iso(iso_date),
            "加權指數": index_close.replace(",", ""),
            "漲跌點數": change.replace(",", ""),
            "成交金額": vol_amt.replace(",", ""),
        })
    return rows


def fetch_stock_month(month_start: date, stock_no: str) -> list[dict]:
    params = {"response": "json", "date": month_start.strftime("%Y%m01"), "stockNo": stock_no}
    r = requests.get(TWSE_STOCK_DAY, params=params, headers=HEADERS, timeout=15)
    r.raise_for_status()
    payload = r.json()
    if payload.get("stat") != "OK":
        return []
    rows = []
    for rec in payload["data"]:
        d, vol_shares, vol_amt, open_, high, low, close, change, tx_count, note = rec
        rows.append({
            "日期": roc_date_to_iso(d),
            "開盤價": open_.replace(",", ""),
            "最高價": high.replace(",", ""),
            "最低價": low.replace(",", ""),
            "收盤價": close.replace(",", ""),
            "漲跌價差": change.replace(",", "").strip(),
        })
    return rows


def fetch_usdtwd(start: date, end: date) -> list[dict]:
    period1 = int(datetime(start.year, start.month, start.day).timestamp())
    period2 = int(datetime(end.year, end.month, end.day, 23, 59, 59).timestamp())
    params = {"period1": period1, "period2": period2, "interval": "1d"}
    r = requests.get(YAHOO_CHART, params=params, headers=HEADERS, timeout=15)
    r.raise_for_status()
    payload = r.json()
    result = payload["chart"]["result"][0]
    timestamps = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]
    rows = []
    for ts, close in zip(timestamps, closes):
        if close is None:
            continue
        d = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
        rows.append({"日期": d, "USDTWD": round(close, 4)})
    return rows


def write_csv(rows: list[dict], path: Path):
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="下載 TAIEX 指數、個股與美元台幣匯率佐證資料")
    parser.add_argument("--start", required=True, help="起始日期 YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="結束日期 YYYY-MM-DD（預設今日）")
    parser.add_argument("--stock", default="2330", help="個股代號（預設 2330 台積電）")
    parser.add_argument("--outdir", default="market_data", help="輸出目錄")
    args = parser.parse_args()

    start = datetime.strptime(args.start, "%Y-%m-%d").date()
    end = datetime.strptime(args.end, "%Y-%m-%d").date() if args.end else date.today()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"[TAIEX] 下載 {start} ~ {end} 加權指數 ...")
    taiex_rows = []
    for m in month_starts(start, end):
        print(f"  {m.strftime('%Y-%m')} ...", end=" ", flush=True)
        rows = fetch_taiex_month(m)
        taiex_rows.extend(rows)
        print(f"{len(rows)} 筆")
        time.sleep(0.5)
    taiex_rows = [r for r in taiex_rows if start.isoformat() <= r["日期"] <= end.isoformat()]
    write_csv(taiex_rows, outdir / "taiex_index.csv")
    print(f"[TAIEX] 共 {len(taiex_rows)} 筆 -> {outdir / 'taiex_index.csv'}")

    print(f"\n[STOCK {args.stock}] 下載 {start} ~ {end} 日成交資訊 ...")
    stock_rows = []
    for m in month_starts(start, end):
        print(f"  {m.strftime('%Y-%m')} ...", end=" ", flush=True)
        rows = fetch_stock_month(m, args.stock)
        stock_rows.extend(rows)
        print(f"{len(rows)} 筆")
        time.sleep(0.5)
    stock_rows = [r for r in stock_rows if start.isoformat() <= r["日期"] <= end.isoformat()]
    write_csv(stock_rows, outdir / f"stock_{args.stock}.csv")
    print(f"[STOCK {args.stock}] 共 {len(stock_rows)} 筆 -> {outdir / f'stock_{args.stock}.csv'}")

    print(f"\n[USDTWD] 下載 {start} ~ {end} 美元/台幣匯率 ...")
    fx_rows = fetch_usdtwd(start, end)
    write_csv(fx_rows, outdir / "usdtwd.csv")
    print(f"[USDTWD] 共 {len(fx_rows)} 筆 -> {outdir / 'usdtwd.csv'}")


if __name__ == "__main__":
    main()
