"""
三大法人買賣統計摘要（文字輸出）
用法：
  python stats_summary.py --start 2025-01-01 --outdir bfi82u_data
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path

try:
    from scipy.signal import argrelextrema
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


CATS = {
    "外資及陸資": "外資及陸資(不含外資自營商)",
    "投信":        "投信",
    "自營商(自行)": "自營商(自行買賣)",
    "自營商(避險)": "自營商(避險)",
}


def load(outdir, start=None):
    files = sorted(Path(outdir).glob("*.csv"))
    df = pd.concat([pd.read_csv(f, thousands=",") for f in files], ignore_index=True)
    df["日期"] = pd.to_datetime(df["日期"], format="%Y/%m/%d")
    for col in ["買進金額", "賣出金額", "買賣差額"]:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")
    if start:
        df = df[df["日期"] >= start]
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir",  default="bfi82u_data")
    parser.add_argument("--start",   default=None)
    parser.add_argument("--inst",    default=None, help="指定單一法人（中文名）")
    args = parser.parse_args()

    df = load(args.outdir, args.start)
    start_d = df["日期"].min().date()
    end_d   = df["日期"].max().date()

    cats = {args.inst: CATS[args.inst]} if args.inst and args.inst in CATS else CATS

    print("=" * 68)
    print(f"  三大法人統計報告  {start_d} ～ {end_d}")
    print("=" * 68)

    for label, name in cats.items():
        sub = df[df["單位名稱"] == name].sort_values("日期").copy()
        sub["差額億"] = sub["買賣差額"] / 1e8
        sub["年月"] = sub["日期"].dt.to_period("M")
        sub["年"]   = sub["日期"].dt.year

        net     = sub["買賣差額"].sum() / 1e8
        buy_amt = sub["買進金額"].sum() / 1e8
        sel_amt = sub["賣出金額"].sum() / 1e8
        buy_d   = (sub["買賣差額"] > 0).sum()
        sel_d   = (sub["買賣差額"] < 0).sum()
        mx      = sub.loc[sub["差額億"].idxmax()]
        mn      = sub.loc[sub["差額億"].idxmin()]

        # 最長連續賣超
        sign = (sub["差額億"] < 0).astype(int)
        grp  = (sign != sign.shift()).cumsum()
        streak = sign.groupby(grp).sum().max()

        print(f"\n【{label}】")
        print(f"  買進：{buy_amt:>12,.0f} 億　賣出：{sel_amt:>12,.0f} 億　差額：{net:>+12,.0f} 億")
        print(f"  買超 {buy_d} 天 / 賣超 {sel_d} 天　最長連續賣超：{streak} 天")
        print(f"  最大買超：{mx['差額億']:>+,.2f} 億（{mx['日期'].date()}）")
        print(f"  最大賣超：{mn['差額億']:>+,.2f} 億（{mn['日期'].date()}）")

        # 月統計
        monthly = sub.groupby("年月").agg(
            買進=("買進金額", lambda x: x.sum() / 1e8),
            賣出=("賣出金額", lambda x: x.sum() / 1e8),
            差額=("買賣差額", lambda x: x.sum() / 1e8),
            交易日=("差額億", "count"),
            買超日=("差額億", lambda x: (x > 0).sum()),
            賣超日=("差額億", lambda x: (x < 0).sum()),
        )
        print(f"\n  月份統計（億元）：")
        print(f"  {'月份':<10}{'差額':>10}{'買超日':>7}{'賣超日':>7}")
        print("  " + "-" * 36)
        cur_yr = None
        for ym, row in monthly.iterrows():
            yr = str(ym)[:4]
            if yr != cur_yr:
                if cur_yr:
                    print()
                cur_yr = yr
            print(f"  {str(ym):<10}{row['差額']:>+10,.0f}{int(row['買超日']):>7}{int(row['賣超日']):>7}")

    # 轉折點（外資）
    foreign = df[df["單位名稱"] == "外資及陸資(不含外資自營商)"].sort_values("日期").copy()
    foreign["差額億"] = foreign["買賣差額"] / 1e8
    cum_arr = foreign["差額億"].cumsum().values
    dates   = foreign["日期"].values

    if HAS_SCIPY and len(cum_arr) > 20:
        from scipy.signal import argrelextrema
        peaks   = argrelextrema(cum_arr, np.greater, order=10)[0]
        troughs = argrelextrema(cum_arr, np.less,    order=10)[0]
        pivots  = sorted([(i, "高點", cum_arr[i]) for i in peaks] +
                         [(i, "低點", cum_arr[i]) for i in troughs])
        if pivots:
            print("\n\n【外資累積重要轉折點】")
            print(f"{'類型':<4}  {'日期':<12}  {'累積差額（億）':>14}")
            print("-" * 36)
            for i, kind, val in pivots:
                print(f"{kind:<4}  {pd.Timestamp(dates[i]).date()}  {val:>+14,.0f}")


if __name__ == "__main__":
    main()
