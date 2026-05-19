# twse-institutional-analysis

下載並分析台灣證交所三大法人（外資及陸資、投信、自營商）買賣超日報表，產生累積走勢圖、轉折點標記與投資分析報告。

---

## 功能概覽

| 功能 | 說明 |
|---|---|
| 智慧下載 | 自動補齊缺漏交易日資料，跳過假日 |
| 累積走勢圖 | 三大法人累積買賣超折線圖，標記轉折點 |
| 每日淨部位圖 | 單日合計長條圖（紅＝買超、綠＝賣超） |
| 綜合分析圖 | 多面板分析 + 月度熱力圖 |
| 文字統計報告 | 各法人買賣金額、買超天數、月度明細 |

---

## 觸發情境

當使用者提到以下任何情境時，Skill 會自動啟動：

- 三大法人、外資買賣、法人買超賣超、外資動向、投信動向、自營商
- TWSE 分析、台股法人、bfi82u、日報表下載
- 「外資買了多少」「法人累積走勢」「畫累積圖」「轉折點分析」
- institutional investors Taiwan、foreign investors TWSE
- 任何想了解台股法人籌碼面的問題

---

## 資料來源

**TWSE BFI82U 端點**：`https://www.twse.com.tw/rwd/zh/fund/BFI82U`

機構名稱（TWSE 原始欄位）：

| 欄位名稱 | 說明 |
|---|---|
| `外資及陸資(不含外資自營商)` | 外資（不含自營商） |
| `外資自營商` | 外資自營商 |
| `投信` | 國內投信 |
| `自營商(自行買賣)` | 自營商自行買賣 |
| `自營商(避險)` | 自營商避險 |
| `合計` | 三大法人合計 |

金額單位：新台幣元（腳本內部換算為億元）

---

## 目錄結構

```
.claude/skills/twse-institutional-analysis/
├── SKILL.md               # Skill 定義與觸發描述
├── README.md              # 本文件
├── scripts/
│   ├── check_and_download.py   # 智慧補齊下載（推薦首選）
│   ├── download_bfi82u.py      # 直接下載工具
│   ├── plot_cumulative.py      # 累積走勢圖 + 轉折點
│   ├── analyze_all.py          # 綜合多面板分析
│   └── stats_summary.py        # 文字統計報告
└── evals/
    └── evals.json         # 評測案例
```

資料存放位置：`bfi82u_data/`（每個交易日一個 CSV，格式：`YYYYMMDD.csv`）

---

## 腳本說明

### `check_and_download.py` ★ 推薦優先使用

智慧型補齊下載，自動比對已存在的日期，只下載缺漏的交易日，不會重複抓取。

```bash
python scripts/check_and_download.py --start 2025-01-01 --outdir bfi82u_data
python scripts/check_and_download.py --start 2025-01-01 --end 2025-05-31 --outdir bfi82u_data
```

| 參數 | 必填 | 說明 |
|---|---|---|
| `--start` | ✓ | 起始日期（YYYY-MM-DD） |
| `--end` | | 結束日期，預設為今日 |
| `--outdir` | | 輸出目錄，預設 `bfi82u_data` |

---

### `download_bfi82u.py`

直接下載工具，支援單日、日期區間或最近 N 日，可選擇輸出為合併 CSV 或每日一檔。

```bash
# 單日
python scripts/download_bfi82u.py --date 2025-05-12

# 日期區間，每日一檔
python scripts/download_bfi82u.py --start 2025-01-01 --end 2025-05-31 --per-day --outdir bfi82u_data

# 最近 30 日合併輸出
python scripts/download_bfi82u.py --days 30 --output bfi82u.csv
```

| 參數 | 說明 |
|---|---|
| `--date` | 單一日期（YYYY-MM-DD） |
| `--start` / `--end` | 日期區間 |
| `--days` | 往前 N 日（含週末，自動跳過非交易日） |
| `--output` | 合併輸出檔名（預設 `bfi82u.csv`） |
| `--per-day` | 每日一檔（格式：`YYYYMMDD.csv`） |
| `--outdir` | 每日檔案輸出目錄 |

---

### `plot_cumulative.py`

產生雙面板累積走勢圖：
- **上方**：三大法人各自累積買賣超折線（含轉折點日期標記）
- **下方**：每日合計淨部位長條圖

輸出：`bfi82u_cumulative_full.png`

```bash
python scripts/plot_cumulative.py --start 2025-01-01 --outdir bfi82u_data
python scripts/plot_cumulative.py --start 2025-01-01 --output my_chart.png --order 15
python scripts/plot_cumulative.py --start 2025-01-01 --no-pivots
```

| 參數 | 說明 |
|---|---|
| `--outdir` | CSV 資料目錄（預設 `bfi82u_data`） |
| `--start` | 起始日期篩選 |
| `--output` | 輸出圖檔名（預設 `bfi82u_cumulative_full.png`） |
| `--order` | 轉折點靈敏度，數字越大偵測越少（預設 `10`） |
| `--no-pivots` | 不標記轉折點 |

**色彩對應**：紅線＝外資、綠線＝投信、藍線＝自營商

---

### `analyze_all.py`

產生綜合多面板分析圖（`all_institutions.png`）：
- 四機構累積走勢總覽
- 各機構獨立面板（含填色區域）
- 月度熱力圖（機構 × 月份，單位億元）

同時在 console 輸出月度與年度統計表。

```bash
python scripts/analyze_all.py --start 2025-01-01 --outdir bfi82u_data
```

---

### `stats_summary.py`

純文字統計報告，不產生圖表。輸出各法人：
- 總買進／賣出金額（億元）
- 買超天數 vs. 賣超天數
- 最長連續賣超天數
- 單日最大買超 / 賣超（含日期）
- 每月明細
- 外資轉折點清單（峰值與谷值）

```bash
# 所有機構
python scripts/stats_summary.py --start 2025-01-01 --outdir bfi82u_data

# 單一機構
python scripts/stats_summary.py --start 2025-01-01 --inst 外資及陸資
```

---

## 使用情境對照

| 使用者需求 | 建議腳本 |
|---|---|
| 下載今年所有資料 | `check_and_download.py` |
| 補齊缺漏日期 | `check_and_download.py` |
| 畫累積走勢 + 轉折點 | `plot_cumulative.py` |
| 完整圖表分析 + 月度熱力圖 | `analyze_all.py` |
| 只要文字統計數字 | `stats_summary.py` |
| 外資今年買了多少 | `stats_summary.py --inst 外資及陸資` |
| 重新下載特定日期 | `download_bfi82u.py --date --per-day` |

---

## 執行流程

```
1. check_and_download.py   ← 確保資料完整
        ↓
2. plot_cumulative.py      ← 產生趨勢圖
   analyze_all.py          ← 產生綜合分析圖
   stats_summary.py        ← 輸出文字統計
```

---

## 環境需求

**Python 套件**：

```
requests
pandas
matplotlib
scipy
```

**系統需求**：
- Python 3.7+
- 微軟正黑體字型（Windows 預設已安裝，用於圖表中文顯示）
- 可連線至 `www.twse.com.tw`

---

## 注意事項

- 下載間隔為 0.5 秒（內建限速，避免對 TWSE 伺服器造成負擔）
- 假日與非交易日自動略過，不會產生空白檔案
- 金額單位在 CSV 中為新台幣元，腳本輸出換算為億元（÷ 1e8）
- `analyze_all.py` 目前讀取路徑與日期篩選為固定值，建議搭配 `--outdir` 參數使用其他腳本
- 分析結果僅供參考，不構成投資建議
