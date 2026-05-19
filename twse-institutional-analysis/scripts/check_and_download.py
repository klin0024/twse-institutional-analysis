"""
智慧型資料檢查與補下載工具
- 計算指定區間內哪些日期缺少 CSV
- 只下載缺少的日期，跳過已有的

用法：
  python check_and_download.py --start 2025-01-01 --outdir bfi82u_data
  python check_and_download.py --start 2025-01-01 --end 2025-12-31 --outdir bfi82u_data
"""

import argparse
import json
import sys
import time
import requests
from datetime import date, datetime, timedelta
from pathlib import Path

API_URL = "https://www.twse.com.tw/rwd/zh/fund/BFI82U"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.twse.com.tw/zh/trading/foreign/bfi82u.html",
}


def date_range(start: date, end: date):
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def check_missing(outdir: Path, start: date, end: date) -> list[date]:
    """找出 start～end 之間缺少的日期（不含週末，因為週末幾乎不可能有資料）。"""
    existing = {f.stem for f in outdir.glob("*.csv")}  # e.g. "20250102"
    missing = []
    for d in date_range(start, end):
        key = d.strftime("%Y%m%d")
        if key not in existing:
            missing.append(d)
    return missing


def fetch_day(day: date) -> dict | None:
    params = {"type": "day", "dayDate": day.strftime("%Y%m%d"), "response": "json"}
    try:
        resp = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
    except requests.RequestException as exc:
        print(f"  [ERROR] {day} 下載失敗：{exc}", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print(f"  [ERROR] {day} 回應非 JSON", file=sys.stderr)
        return None
    if payload.get("stat") != "OK":
        return None   # 假日/休市，靜默跳過
    return payload


def payload_to_csv(payload: dict, path: Path):
    from datetime import datetime as dt
    import csv
    fields   = payload["fields"]
    date_str = payload["date"]
    date_fmt = dt.strptime(date_str, "%Y%m%d").strftime("%Y/%m/%d")
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["日期"] + fields)
        writer.writeheader()
        for record in payload["data"]:
            row = {"日期": date_fmt}
            row.update(zip(fields, record))
            writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description="檢查並補下載缺少的日期")
    parser.add_argument("--start",  required=True, help="起始日期 YYYY-MM-DD")
    parser.add_argument("--end",    default=None,  help="結束日期 YYYY-MM-DD（預設今日）")
    parser.add_argument("--outdir", default="bfi82u_data", help="CSV 目錄")
    args = parser.parse_args()

    start  = datetime.strptime(args.start, "%Y-%m-%d").date()
    end    = datetime.strptime(args.end, "%Y-%m-%d").date() if args.end else date.today()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # ── 第一步：掃描缺少的日期 ───────────────────────────────
    missing = check_missing(outdir, start, end)
    total_days = (end - start).days + 1
    existing   = total_days - len(missing)

    print(f"[CHECK] {start} ～ {end}（共 {total_days} 天）")
    print(f"  已有：{existing} 個檔案")
    print(f"  缺少：{len(missing)} 個日期待確認")

    if not missing:
        print("[OK] 資料完整，無需下載。")
        return

    # ── 第二步：嘗試下載缺少的日期 ──────────────────────────
    downloaded = 0
    skipped    = 0   # 假日/休市
    errors     = 0

    print(f"\n[DOWNLOAD] 開始下載 {len(missing)} 個缺少日期...")
    for i, d in enumerate(missing):
        print(f"  [{i+1}/{len(missing)}] {d} ...", end=" ", flush=True)
        payload = fetch_day(d)
        if payload:
            path = outdir / f"{d.strftime('%Y%m%d')}.csv"
            payload_to_csv(payload, path)
            print("OK")
            downloaded += 1
        else:
            print("SKIP（假日/休市）")
            skipped += 1
        if len(missing) > 1:
            time.sleep(0.5)

    print(f"\n[DONE] 下載 {downloaded} 筆，跳過 {skipped} 筆（假日），失敗 {errors} 筆")
    print(f"[DONE] 資料目錄：{outdir.resolve()}")


if __name__ == "__main__":
    main()
