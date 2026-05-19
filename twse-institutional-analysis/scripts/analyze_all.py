"""
三大法人全體分析（2025-01-01 至今）
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import numpy as np
from pathlib import Path

plt.rcParams["font.family"] = ["Microsoft JhengHei", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False

# ── 讀取資料 ─────────────────────────────────────────────────
files = sorted(Path("bfi82u_data").glob("*.csv"))
df = pd.concat([pd.read_csv(f, thousands=",") for f in files], ignore_index=True)
df["日期"] = pd.to_datetime(df["日期"], format="%Y/%m/%d")
for col in ["買進金額", "賣出金額", "買賣差額"]:
    df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")

df = df[df["日期"] >= "2025-01-01"].copy()

# 分析用法人（排除合計與外資自營商）
CATS = {
    "外資及陸資": "外資及陸資(不含外資自營商)",
    "投信":       "投信",
    "自營商(自行)": "自營商(自行買賣)",
    "自營商(避險)": "自營商(避險)",
}
COLORS = {
    "外資及陸資":  "#d62728",
    "投信":        "#2ca02c",
    "自營商(自行)": "#1f77b4",
    "自營商(避險)": "#ff7f0e",
}

# 建立每日各法人 pivot
pivot = {}
for label, name in CATS.items():
    s = (df[df["單位名稱"] == name]
         .sort_values("日期")
         .set_index("日期")["買賣差額"] / 1e8)
    pivot[label] = s

pv = pd.DataFrame(pivot).sort_index()
pv["自營商合計"] = pv["自營商(自行)"] + pv["自營商(避險)"]
pv["三大法人合計"] = pv[list(CATS.keys())].sum(axis=1)

cum = pv.cumsum()

# ── 月統計（各法人） ─────────────────────────────────────────
monthly_all = {}
for label, name in CATS.items():
    sub = df[df["單位名稱"] == name].copy()
    sub["年月"] = sub["日期"].dt.to_period("M")
    m = sub.groupby("年月")["買賣差額"].sum() / 1e8
    monthly_all[label] = m

monthly_df = pd.DataFrame(monthly_all).sort_index()
monthly_df["自營商合計"] = monthly_df["自營商(自行)"] + monthly_df["自營商(避險)"]
monthly_df["三大法人合計"] = monthly_df[list(CATS.keys())].sum(axis=1)

# ── 年統計 ────────────────────────────────────────────────────
yearly_all = {}
for label, name in CATS.items():
    sub = df[df["單位名稱"] == name].copy()
    sub["年"] = sub["日期"].dt.year
    y = sub.groupby("年").agg(
        買進=("買進金額", lambda x: x.sum() / 1e8),
        賣出=("賣出金額", lambda x: x.sum() / 1e8),
        差額=("買賣差額", lambda x: x.sum() / 1e8),
        交易日=("買賣差額", "count"),
        買超日=("買賣差額", lambda x: (x > 0).sum()),
        賣超日=("買賣差額", lambda x: (x < 0).sum()),
    )
    yearly_all[label] = y

# ── 印出統計 ─────────────────────────────────────────────────
start_date = df["日期"].min().date()
end_date   = df["日期"].max().date()
trade_days = pv.shape[0]

print("=" * 72)
print(f"  三大法人完整分析  {start_date} ～ {end_date}  （{trade_days} 個交易日）")
print("=" * 72)

for label, name in CATS.items():
    sub = df[df["單位名稱"] == name]
    net   = sub["買賣差額"].sum() / 1e8
    buy_d = (sub["買賣差額"] > 0).sum()
    sel_d = (sub["買賣差額"] < 0).sum()
    mx    = sub.loc[sub["買賣差額"].idxmax()]
    mn    = sub.loc[sub["買賣差額"].idxmin()]
    print(f"\n【{label}】  累積差額：{net:+,.0f} 億元  買超{buy_d}天／賣超{sel_d}天")
    print(f"  最大買超：{mx['買賣差額']/1e8:+,.2f} 億（{mx['日期'].date()}）")
    print(f"  最大賣超：{mn['買賣差額']/1e8:+,.2f} 億（{mn['日期'].date()}）")

print("\n\n【月份合計統計（各法人差額，億元）】")
print(f"{'月份':<10}", end="")
cols = ["外資及陸資", "投信", "自營商合計", "三大法人合計"]
for c in cols:
    print(f"{c:>12}", end="")
print()
print("-" * 62)
cur_yr = None
for ym, row in monthly_df.iterrows():
    yr = str(ym)[:4]
    if yr != cur_yr:
        if cur_yr:
            print()
        cur_yr = yr
    print(f"{str(ym):<10}", end="")
    for c in cols:
        print(f"{row[c]:>+12,.0f}", end="")
    print()

print("\n\n【年度合計】（億元）")
print(f"{'年份':<6}{'外資及陸資':>12}{'投信':>10}{'自營商合計':>12}{'三大法人合計':>14}")
print("-" * 56)
for yr in [2025, 2026]:
    row_vals = []
    for label in ["外資及陸資", "投信", "自營商(自行)", "自營商(避險)"]:
        if label in yearly_all and yr in yearly_all[label].index:
            row_vals.append(yearly_all[label].loc[yr, "差額"])
        else:
            row_vals.append(0)
    dealer_total = row_vals[2] + row_vals[3]
    total = sum(row_vals)
    print(f"{yr:<6}{row_vals[0]:>+12,.0f}{row_vals[1]:>+10,.0f}{dealer_total:>+12,.0f}{total:>+14,.0f}")

# ── 畫圖 ─────────────────────────────────────────────────────
fig = plt.figure(figsize=(16, 18))
gs  = fig.add_gridspec(4, 2, hspace=0.5, wspace=0.35)

month_starts = pd.date_range("2025-02-01", pv.index.max(), freq="MS")
yr_line = pd.Timestamp("2026-01-01")

def add_year_grid(ax):
    for ms in month_starts:
        ax.axvline(ms, color="lightgray", linewidth=0.4, linestyle=":", alpha=0.6)
    ax.axvline(yr_line, color="gray", linewidth=1.0, linestyle="--", alpha=0.7)
    ax.axhline(0, color="black", linewidth=0.7, linestyle="--")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.grid(axis="y", linestyle=":", alpha=0.3)

# ① 累積走勢（四法人 + 三大合計）
ax1 = fig.add_subplot(gs[0, :])
for label, color in COLORS.items():
    ax1.plot(cum.index, cum[label], color=color, linewidth=1.6, label=label)
ax1.plot(cum.index, cum["三大法人合計"], color="black", linewidth=2.2,
         linestyle="--", label="三大法人合計")
add_year_grid(ax1)
ax1.set_title("三大法人 累積買賣差額走勢（2025/01 ～ 至今）", fontsize=13, pad=10)
ax1.set_ylabel("累積差額（億元）")
ax1.legend(loc="lower left", fontsize=9, ncol=3)

# ② 外資累積（獨立放大）
ax2 = fig.add_subplot(gs[1, 0])
ax2.fill_between(cum.index, cum["外資及陸資"], 0,
                 where=cum["外資及陸資"] < 0, alpha=0.2, color="#d62728")
ax2.plot(cum.index, cum["外資及陸資"], color="#d62728", linewidth=1.8)
add_year_grid(ax2)
ax2.set_title("外資及陸資 累積差額", fontsize=11)
ax2.set_ylabel("億元")

# ③ 投信累積
ax3 = fig.add_subplot(gs[1, 1])
ax3.fill_between(cum.index, cum["投信"], 0,
                 where=cum["投信"] >= 0, alpha=0.2, color="#2ca02c")
ax3.fill_between(cum.index, cum["投信"], 0,
                 where=cum["投信"] < 0, alpha=0.2, color="#d62728")
ax3.plot(cum.index, cum["投信"], color="#2ca02c", linewidth=1.8)
add_year_grid(ax3)
ax3.set_title("投信 累積差額", fontsize=11)
ax3.set_ylabel("億元")

# ④ 自營商(自行)累積
ax4 = fig.add_subplot(gs[2, 0])
ax4.fill_between(cum.index, cum["自營商(自行)"], 0,
                 where=cum["自營商(自行)"] >= 0, alpha=0.2, color="#1f77b4")
ax4.fill_between(cum.index, cum["自營商(自行)"], 0,
                 where=cum["自營商(自行)"] < 0, alpha=0.2, color="#d62728")
ax4.plot(cum.index, cum["自營商(自行)"], color="#1f77b4", linewidth=1.8)
add_year_grid(ax4)
ax4.set_title("自營商(自行買賣) 累積差額", fontsize=11)
ax4.set_ylabel("億元")

# ⑤ 自營商(避險)累積
ax5 = fig.add_subplot(gs[2, 1])
ax5.fill_between(cum.index, cum["自營商(避險)"], 0,
                 where=cum["自營商(避險)"] >= 0, alpha=0.2, color="#ff7f0e")
ax5.fill_between(cum.index, cum["自營商(避險)"], 0,
                 where=cum["自營商(避險)"] < 0, alpha=0.2, color="#d62728")
ax5.plot(cum.index, cum["自營商(避險)"], color="#ff7f0e", linewidth=1.8)
add_year_grid(ax5)
ax5.set_title("自營商(避險) 累積差額", fontsize=11)
ax5.set_ylabel("億元")

# ⑥ 月份各法人差額熱圖
ax6 = fig.add_subplot(gs[3, :])
heat_cols = ["外資及陸資", "投信", "自營商(自行)", "自營商(避險)", "三大法人合計"]
heat_data = monthly_df[heat_cols].T
vmax = heat_data.abs().max().max()
im = ax6.imshow(heat_data.values, aspect="auto", cmap="RdYlGn",
                vmin=-vmax, vmax=vmax)
ax6.set_xticks(range(len(heat_data.columns)))
ax6.set_xticklabels([str(c) for c in heat_data.columns], rotation=60, ha="right", fontsize=8)
ax6.set_yticks(range(len(heat_cols)))
ax6.set_yticklabels(heat_cols, fontsize=9)
for i in range(len(heat_cols)):
    for j in range(len(heat_data.columns)):
        val = heat_data.values[i, j]
        ax6.text(j, i, f"{val:+,.0f}", ha="center", va="center",
                 fontsize=6.5, color="black" if abs(val) < vmax * 0.6 else "white")
plt.colorbar(im, ax=ax6, label="億元", shrink=0.6)
ax6.set_title("月份各法人買賣差額熱力圖（億元）", fontsize=11, pad=8)

fig.autofmt_xdate(rotation=25)
out = "all_institutions.png"
plt.savefig(out, dpi=150, bbox_inches="tight")
print(f"\n圖表已儲存 → {Path(out).resolve()}")
