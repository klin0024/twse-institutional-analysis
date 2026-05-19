"""
三大法人累積買賣差額走勢圖（含重要轉折點標記）
用法：
  python plot_cumulative.py --start 2025-01-01 --outdir bfi82u_data --output chart.png
"""

import argparse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import numpy as np
from pathlib import Path

try:
    from scipy.signal import argrelextrema
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

plt.rcParams["font.family"] = ["Microsoft JhengHei", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False


def load_data(outdir: str, start: str = None) -> tuple[pd.DatetimeIndex, dict]:
    files = sorted(Path(outdir).glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"找不到資料：{outdir}/*.csv")
    df = pd.concat([pd.read_csv(f, thousands=",") for f in files], ignore_index=True)
    df["日期"] = pd.to_datetime(df["日期"], format="%Y/%m/%d")
    df["買賣差額"] = pd.to_numeric(df["買賣差額"].astype(str).str.replace(",", ""), errors="coerce")
    if start:
        df = df[df["日期"] >= start]
    all_dates = df["日期"].drop_duplicates().sort_values().reset_index(drop=True)

    def get_series(name):
        s = (df[df["單位名稱"] == name]
             .sort_values("日期").set_index("日期")["買賣差額"] / 1e8)
        return s.reindex(all_dates, fill_value=0)

    return all_dates, {
        "foreign_d": get_series("外資及陸資(不含外資自營商)"),
        "trust_d":   get_series("投信"),
        "dealer_d":  get_series("自營商(自行買賣)") + get_series("自營商(避險)"),
    }


def find_pivots(arr: np.ndarray, order: int = 10):
    if not HAS_SCIPY:
        return np.array([np.argmax(arr)]), np.array([np.argmin(arr)])
    peaks   = argrelextrema(arr, np.greater, order=order)[0]
    troughs = argrelextrema(arr, np.less,    order=order)[0]
    return peaks, troughs


def annotate_pivots(ax, dates, arr, color, order=10, pk_off=(6, 10), tr_off=(6, -30)):
    peaks, troughs = find_pivots(arr, order=order)
    for i in peaks:
        ax.scatter(dates[i], arr[i], color=color, s=55, zorder=6)
        ax.annotate(
            f'{pd.Timestamp(dates[i]).strftime("%y/%m/%d")}\n{arr[i]:+,.0f}',
            xy=(dates[i], arr[i]), xytext=pk_off, textcoords="offset points",
            fontsize=7, color=color,
            bbox=dict(fc="white", alpha=0.65, pad=1, ec="none"),
            arrowprops=dict(arrowstyle="->", color=color, lw=0.7),
        )
    for i in troughs:
        ax.scatter(dates[i], arr[i], color=color, s=55, zorder=6, marker="v")
        ax.annotate(
            f'{pd.Timestamp(dates[i]).strftime("%y/%m/%d")}\n{arr[i]:+,.0f}',
            xy=(dates[i], arr[i]), xytext=tr_off, textcoords="offset points",
            fontsize=7, color=color,
            bbox=dict(fc="white", alpha=0.65, pad=1, ec="none"),
            arrowprops=dict(arrowstyle="->", color=color, lw=0.7),
        )


def main():
    parser = argparse.ArgumentParser(description="三大法人累積走勢圖")
    parser.add_argument("--outdir",  default="bfi82u_data", help="CSV 資料目錄")
    parser.add_argument("--start",   default=None, help="起始日期 YYYY-MM-DD")
    parser.add_argument("--output",  default="bfi82u_cumulative_full.png", help="輸出圖檔名")
    parser.add_argument("--order",   type=int, default=10, help="轉折點偵測敏感度（越大越少）")
    parser.add_argument("--no-pivots", action="store_true", help="不標記轉折點")
    args = parser.parse_args()

    all_dates, series = load_data(args.outdir, args.start)
    foreign_d = series["foreign_d"]
    trust_d   = series["trust_d"]
    dealer_d  = series["dealer_d"]
    total_d   = foreign_d + trust_d + dealer_d

    foreign_c = foreign_d.cumsum()
    trust_c   = trust_d.cumsum()
    dealer_c  = dealer_d.cumsum()

    dates = all_dates.values
    month_starts = pd.date_range(
        pd.Timestamp(dates[0]).replace(day=1) + pd.DateOffset(months=1),
        pd.Timestamp(dates[-1]), freq="MS"
    )
    yr_boundaries = [pd.Timestamp(f"{y}-01-01")
                     for y in range(pd.Timestamp(dates[0]).year + 1,
                                    pd.Timestamp(dates[-1]).year + 1)]

    fig, axes = plt.subplots(2, 1, figsize=(18, 10), sharex=True,
                              gridspec_kw={"height_ratios": [2, 1]})
    fig.subplots_adjust(hspace=0.12)

    # ── 上圖：累積折線 ───────────────────────────────────────
    ax1 = axes[0]
    ax1.plot(dates, foreign_c.values, color="#d62728", linewidth=1.8, label="外資及陸資")
    ax1.plot(dates, trust_c.values,   color="#2ca02c", linewidth=1.8, label="投信")
    ax1.plot(dates, dealer_c.values,  color="#1f77b4", linewidth=1.8, label="自營商合計")

    if not args.no_pivots:
        annotate_pivots(ax1, dates, foreign_c.values, "#d62728", args.order,
                        pk_off=(6, 10), tr_off=(6, -30))
        annotate_pivots(ax1, dates, trust_c.values,   "#2ca02c", args.order,
                        pk_off=(-68, 8), tr_off=(-68, -28))
        annotate_pivots(ax1, dates, dealer_c.values,  "#1f77b4", args.order,
                        pk_off=(6, 10), tr_off=(6, -30))

    ax1.axhline(0, color="black", linewidth=0.7, linestyle="--")
    for yr in yr_boundaries:
        ax1.axvline(yr, color="gray", linewidth=1, linestyle=":", alpha=0.7)
        ax1.text(yr, ax1.get_ylim()[0] if ax1.get_ylim()[0] < 0 else 0,
                 f' {yr.year}', fontsize=8.5, color="gray")
    for ms in month_starts:
        ax1.axvline(ms, color="lightgray", linewidth=0.4, linestyle=":", alpha=0.5)

    ax1.set_title("三大法人買賣差額累積走勢（含重要轉折點）", fontsize=13, pad=10)
    ax1.set_ylabel("累積買賣差額（億元）")
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax1.legend(loc="lower left", fontsize=10)
    ax1.grid(axis="y", linestyle=":", alpha=0.45)

    # ── 下圖：每日合計柱狀 ──────────────────────────────────
    ax2 = axes[1]
    bar_colors = ["#d62728" if v >= 0 else "#2ca02c" for v in total_d.values]
    ax2.bar(dates, total_d.values, color=bar_colors, width=0.8, alpha=0.85)
    ax2.axhline(0, color="black", linewidth=0.6)
    for yr in yr_boundaries:
        ax2.axvline(yr, color="gray", linewidth=1, linestyle=":", alpha=0.7)
    for ms in month_starts:
        ax2.axvline(ms, color="lightgray", linewidth=0.4, linestyle=":", alpha=0.5)

    # 單日最大/最小
    hi2 = int(np.argmax(total_d.values)); lo2 = int(np.argmin(total_d.values))
    for idx, marker, color, off in [(hi2, "o", "#d62728", (6, 6)), (lo2, "v", "#2ca02c", (6, -30))]:
        ax2.scatter(dates[idx], total_d.values[idx], color=color, s=60, zorder=5, marker=marker)
        ax2.annotate(
            f'{pd.Timestamp(dates[idx]).strftime("%y/%m/%d")}\n{total_d.values[idx]:+,.0f}',
            xy=(dates[idx], total_d.values[idx]), xytext=off, textcoords="offset points",
            fontsize=7.5, color=color,
            bbox=dict(fc="white", alpha=0.7, pad=1, ec="none"),
            arrowprops=dict(arrowstyle="->", color=color, lw=0.8),
        )

    ax2.set_ylabel("日合計差額（億元）")
    ax2.set_xlabel("日期")
    ax2.set_title("三大法人合計每日買賣差額", fontsize=11)
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax2.grid(axis="y", linestyle=":", alpha=0.4)

    fig.autofmt_xdate(rotation=20)
    out = Path(args.output)
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"圖表已儲存 → {out.resolve()}")


if __name__ == "__main__":
    main()
