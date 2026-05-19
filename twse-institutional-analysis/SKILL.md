---
name: twse-institutional-analysis
description: |
  下載並分析台灣證交所三大法人（外資及陸資、投信、自營商）買賣超日報表，產生累積走勢圖、轉折點標記與投資分析報告。
  當使用者提到以下任何情境時，主動使用此 skill：
  - 三大法人、外資買賣、法人買超賣超、外資動向、投信動向、自營商
  - TWSE 分析、台股法人、bfi82u、日報表下載
  - 「外資買了多少」「法人累積走勢」「畫累積圖」「轉折點分析」
  - institutional investors Taiwan、foreign investors TWSE
  - 任何想了解台股法人籌碼面的問題
---

# TWSE 三大法人分析 Skill

## 概覽

此 skill 涵蓋三個階段：**下載資料 → 統計分析 → 圖表輸出**。
所有腳本已放在 `scripts/` 目錄，可直接呼叫，不需重新撰寫。

---

## 第一步：檢查並補下載資料（必做）

**永遠先執行 `check_and_download.py`**，它會自動：
1. 掃描 `bfi82u_data/` 中已有哪些日期的 CSV
2. 計算指定區間內哪些日期缺少
3. **只下載缺少的日期**，已有的完全跳過

```bash
# 標準用法：指定起始日，自動補到今天
python .claude/skills/twse-institutional-analysis/scripts/check_and_download.py \
    --start 2025-01-01 --outdir bfi82u_data

# 指定區間
python .claude/skills/twse-institutional-analysis/scripts/check_and_download.py \
    --start 2025-01-01 --end 2025-12-31 --outdir bfi82u_data
```

執行後會顯示：
```
[CHECK] 2025-01-01 ～ 2026-05-16（共 501 天）
  已有：320 個檔案
  缺少：5 個日期待確認
[DOWNLOAD] 開始下載 5 個缺少日期...
  [1/5] 2025-08-05 ... OK
  ...
[DONE] 下載 3 筆，跳過 2 筆（假日）
```

**注意事項：**
- 假日/休市靜默跳過，不會建立空檔
- 批次下載每筆間隔 0.5 秒，避免觸發伺服器限制
- 若出現 timeout，重新執行即可（已下載的不會重複）
- 若需強制重新下載單日：`python .claude/skills/twse-institutional-analysis/scripts/download_bfi82u.py --date 2025-05-12 --per-day --outdir bfi82u_data`

---

## 第三步：分析與圖表

根據使用者需求選擇對應腳本：

### 3a. 三大法人累積走勢圖（最常用）

產生與 `bfi82u_cumulative.png` 相同樣式的圖表：
- **上圖**：外資、投信、自營商合計的累積買賣差額折線，附重要轉折點日期標記
- **下圖**：每日三大法人合計買賣差額柱狀圖（紅=買超、綠=賣超）

```bash
python scripts/plot_cumulative.py --start 2025-01-01 --outdir bfi82u_data --output chart.png
```

### 3b. 全機構分析（含熱力圖）

```bash
python scripts/analyze_all.py --start 2025-01-01 --outdir bfi82u_data
```
輸出：`all_institutions.png`

### 3c. 純文字統計摘要

```bash
python scripts/stats_summary.py --start 2025-01-01 --outdir bfi82u_data
```

---

## 第四步：分析報告撰寫

統計完成後，結合以下框架撰寫敘述分析：

### 統計面
- 全期累積差額（買超/賣超幾億）
- 買超天數 vs 賣超天數
- 最長連續賣超天數與期間
- 各月份統計（哪個月最嚴重/最好）

### 轉折點解讀
對照各高點/低點日期，對應已知市場事件：

| 時間 | 常見觸發事件 |
|---|---|
| 2025-01 | DeepSeek AI 衝擊、川普就職 |
| 2025-03~04 | 美中關稅戰（Liberation Day 4/2） |
| 2025-05~07 | 關稅暫緩、AI 需求復甦 |
| 2025-11 | 年底基金調倉 |
| 2026-03 | 重大賣壓（地緣/貿易事件） |
| 2026-04 | 單日最大買超（政策轉向） |

**注意**：2025 年 8 月以後事件超出知識截止日，應標注「推測」並說明依據。

### 投資建議框架
- 短線（5日均線方向）
- 中線（月度累積方向是否連續翻正）
- 長線（累積差額是否轉正）
- 風險提示：以下為資料面觀察，非正式投資建議

---

## 常見使用者問題對應

| 使用者說 | 動作 |
|---|---|
| 「分析 2025 年至今」 | 先執行 `check_and_download.py --start 2025-01-01`，再執行分析腳本 |
| 「下載最新資料」 | `check_and_download.py --start <上次起始日>` 自動補缺 |
| 「畫累積圖」 | 確認資料後執行 `plot_cumulative.py`，顯示圖片 |
| 「外資買了多少」| 確認資料後執行 `stats_summary.py`，取「買進合計」 |
| 「什麼時候開始賣」 | 找累積高點日期（通常是 2025/01/07 附近） |
| 「分析原因」 | 對照轉折點日期與已知市場事件 |
| 「某月合計」 | 從月份統計表取出對應月份數字 |

---

## 相依套件

```bash
pip install requests pandas matplotlib scipy
```

---

## 輸出格式

- **CSV**：UTF-8 with BOM，欄位：`日期, 單位名稱, 買進金額, 賣出金額, 買賣差額`
- **圖表**：PNG，dpi=150，中文字型使用 Microsoft JhengHei
- **金額單位**：元（原始）/ 億元（分析用，除以 1e8）
