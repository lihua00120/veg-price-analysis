# veg-price-analysis

高雄果菜市場（[khfv.com.tw](https://www.khfv.com.tw)）蔬菜交易行情的自動化爬蟲、資料整合與價格預測專案。每天定時抓取當日交易行情，累積成歷史資料庫，並用時間序列模型預測隔日菜價，供下游的 LINE Bot（[chat-_bot](https://github.com/lihua00120/chat-_bot)）讀取使用，讓使用者能查到「明日哪些蔬菜會比較便宜」。

## 這個專案在做什麼

1. **爬蟲 [for_crawler.py](for_crawler.py)**
   - 從高雄果菜市場網站抓取當日各項蔬菜的交易行情表格（交易日期、產品名稱、均價、交易量）。
   - 依「產品名稱」計算以交易量加權的加權平均價，輸出成 [today_veg_prices.csv](today_veg_prices.csv)。
   - 將當日資料併入既有的歷史資料 [veg_prices_history.csv](veg_prices_history.csv)，並去除重複紀錄，讓歷史資料庫持續累積、越來越完整。

2. **價格預測 [price_prediction.py](price_prediction.py)**
   - 讀取歷史資料，依產品名稱分組成各自的時間序列。
   - 針對每個產品分析 ACF / PACF，自動挑出最能預測未來價格的落後期數（lag）。
   - 用這些特徵訓練線性迴歸模型，預測每項蔬菜「明日」的加權平均價。
   - 將所有產品的預測結果輸出成 [veg_pred.csv](veg_pred.csv)。

### 自動化 workflow

專案透過 GitHub Actions（[.github/workflows/main.yml](.github/workflows/main.yml)）全自動運作，不需要人工介入：

```
每 8 小時觸發一次
      │
      ▼
1. 執行 for_crawler.py
   → 抓取當日菜價、合併進歷史資料
      │
      ▼
2. 執行 price_prediction.py
   → 依歷史資料預測明日菜價
      │
      ▼
3. 自動 commit + push
   → 更新 today_veg_prices.csv / veg_prices_history.csv / veg_pred.csv 回 main 分支
```

也可以在 GitHub 的 Actions 頁面手動觸發，或在有 push / PR 進 `main` 分支時觸發一次。每次跑完，最新的菜價與預測結果都會直接反映在 repo 裡的 CSV 檔案上，[chat-_bot](https://github.com/lihua00120/chat-_bot) 會直接讀取這些檔案的最新版本。

### 資料檔案說明

| 檔案 | 說明 |
|---|---|
| [today_veg_prices.csv](today_veg_prices.csv) | 當日爬取並加權平均後的蔬菜價格 |
| [veg_prices_history.csv](veg_prices_history.csv) | 歷史每日蔬菜加權平均價格與交易量（持續累積） |
| [veg_pred.csv](veg_pred.csv) | 各項蔬菜「明日」預測價格 |

## 注意事項

- 預測模型為線性迴歸，且對交易資料較少的品項，準確度可能有限，僅供參考。
