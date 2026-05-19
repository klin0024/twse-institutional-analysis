"""
三大法人買賣金額統計表下載工具
來源：https://www.twse.com.tw/zh/trading/foreign/bfi82u.html
"""

import argparse
import csv
import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

API_URL = "https://www.twse.com.tw/rwd/zh/fund/BFI82U"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.twse.com.tw/zh/trading/foreign/bfi82u.html",
}


def fetch_day(day: date) -> dict | None:
    """下載單日資料，回傳 dict；若無資料或失敗則回傳 None。"""
    params = {
        "type": "day",
        "dayDate": day.strftime("%Y%m%d"),
        "response": "json",
    }
    try:
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException as exc:
        print(f"[ERROR] {day} 下載失敗：{exc}", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print(f"[ERROR] {day} 回應非 JSON 格式", file=sys.stderr)
        return None

    if payload.get("stat") != "OK":
        print(f"[SKIP]  {day} 無資料（假日或休市）")
        return None

    return payload


def payload_to_rows(payload: dict) -> list[dict]:
    """將 API payload 轉為 list of dict（含日期欄）。"""
    fields = payload["fields"]
    date_str = payload["date"]           # e.g. "20250512"
    date_fmt = datetime.strptime(date_str, "%Y%m%d").strftime("%Y/%m/%d")
    rows = []
    for record in payload["data"]:
        row = {"日期": date_fmt}
        row.update(zip(fields, record))
        rows.append(row)
    return rows


def save_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="下載 TWSE 三大法人買賣金額統計表",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例：
  python download_bfi82u.py                                         # 下載今日（單檔）
  python download_bfi82u.py --date 2025-05-12                       # 下載指定日期（單檔）
  python download_bfi82u.py --start 2025-05-01 --end 2025-05-12    # 下載區間（單檔）
  python download_bfi82u.py --start 2025-05-01 --per-day           # 每日一個 CSV
  python download_bfi82u.py --start 2025-05-01 --per-day --outdir data  # 存到 data/ 目錄
""",
    )
    parser.add_argument("--date", help="指定單一日期 (YYYY-MM-DD)")
    parser.add_argument("--start", help="起始日期 (YYYY-MM-DD)，搭配 --end 使用")
    parser.add_argument("--end", help="結束日期 (YYYY-MM-DD)，預設為今日")
    parser.add_argument("--days", type=int, help="往回幾個自然日（包含假日，會自動跳過）")
    parser.add_argument(
        "--output", default="bfi82u.csv", help="合併輸出檔案路徑 (預設: bfi82u.csv)"
    )
    parser.add_argument(
        "--per-day", action="store_true",
        help="每個交易日儲存為獨立 CSV，檔名格式 YYYYMMDD.csv"
    )
    parser.add_argument(
        "--outdir", default=".", help="--per-day 的輸出目錄 (預設: 當前目錄)"
    )
    return parser.parse_args()


def date_range(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def write_csv(rows: list[dict], path: Path) -> None:
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    today = date.today()
    outdir = Path(args.outdir)

    # 決定日期清單
    if args.date:
        dates = [datetime.strptime(args.date, "%Y-%m-%d").date()]
    elif args.start:
        start = datetime.strptime(args.start, "%Y-%m-%d").date()
        end = datetime.strptime(args.end, "%Y-%m-%d").date() if args.end else today
        dates = list(date_range(start, end))
    elif args.days:
        start = today - timedelta(days=args.days - 1)
        dates = list(date_range(start, today))
    else:
        dates = [today]

    if args.per_day:
        outdir.mkdir(parents=True, exist_ok=True)

    all_rows: list[dict] = []
    saved_files: list[Path] = []

    for d in dates:
        print(f"[FETCH] {d} ...", end=" ", flush=True)
        payload = fetch_day(d)
        if payload:
            rows = payload_to_rows(payload)
            if args.per_day:
                # 每日存為獨立 CSV，檔名 YYYYMMDD.csv
                file_path = outdir / f"{d.strftime('%Y%m%d')}.csv"
                write_csv(rows, file_path)
                saved_files.append(file_path)
                print(f"OK → {file_path}")
            else:
                all_rows.extend(rows)
                print(f"OK（{len(rows)} 筆）")
        if len(dates) > 1:
            time.sleep(0.5)   # 避免過快觸發伺服器限制

    if args.per_day:
        print(f"\n共儲存 {len(saved_files)} 個檔案至 {outdir.resolve()}")
        return

    if not all_rows:
        print("沒有任何資料可儲存。")
        return

    output = Path(args.output)
    write_csv(all_rows, output)
    print(f"\n已儲存 {len(all_rows)} 筆資料 → {output.resolve()}")


if __name__ == "__main__":
    main()
