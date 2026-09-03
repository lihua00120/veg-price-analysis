# -*- coding: utf-8 -*-
"""明日菜價預測

讀取歷史蔬菜價格，依產品名稱分組後，用 PACF 挑出每個產品自己最顯著的
落後期（lag）當特徵，訓練「屬於該產品自己」的線性迴歸模型，預測明日的
加權平均價，輸出成 veg_pred.csv。
"""

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import pacf
from sklearn.linear_model import LinearRegression

MAX_TOP_LAGS = 3  # 每個產品最多選出幾個最顯著的 lag 當特徵
MIN_SAMPLES = MAX_TOP_LAGS + 2  # 資料筆數低於此門檻就跳過該產品

df = pd.read_csv('veg_prices_history.csv')
df['交易日期'] = pd.to_datetime(df['交易日期'], format='%Y/%m/%d', errors='coerce')

# 產品名稱可能帶有品種/等級（例如「冬瓜 白皮」「包心白菜 包 白」），
# 先正規化成基礎菜名，避免同一種菜被拆成多個資料稀疏的小分類，
# 也讓輸出的品名跟 chat-_bot 那邊比對用的簡化菜名保持一致。
df['產品名稱'] = df['產品名稱'].str.strip().str.split().str[0]

# 正規化後，同一天、同一種菜可能有多筆資料（來自不同品種/等級），
# 依交易量重新加權平均，合併回一筆。
df['加權合計'] = df['加權平均價(元/公斤)'] * df['總交易量(公斤)']
df = (
    df.groupby(['交易日期', '產品名稱'], as_index=False)
    .agg(加權合計=('加權合計', 'sum'), 總交易量公斤=('總交易量(公斤)', 'sum'))
)
df['加權平均價(元/公斤)'] = df['加權合計'] / df['總交易量公斤']
df = df[['交易日期', '產品名稱', '加權平均價(元/公斤)']]

df.set_index('交易日期', inplace=True)
df.index.name = '交易時間'
df.sort_index(inplace=True)

grouped_by_product = df.groupby('產品名稱')
print(f"共 {len(grouped_by_product)} 種蔬菜")

predictions = []

for name, group in grouped_by_product:
    ts = pd.to_numeric(group['加權平均價(元/公斤)'], errors='coerce').dropna()

    if len(ts) < MIN_SAMPLES:
        print(f"{name}: 資料太少（{len(ts)} 筆），跳過")
        continue

    # 用 PACF 選出對「這個產品自己」最顯著的 lag
    nlags = min(20, len(ts) // 2 - 1)
    nlags = max(nlags, 1)
    pacf_vals = pacf(ts, nlags=nlags)
    top_lags = np.argsort(np.abs(pacf_vals[1:]))[::-1][:MAX_TOP_LAGS] + 1
    top_lags = sorted(top_lags)

    if len(ts) < max(top_lags) + 1:
        print(f"{name}: 資料不足以涵蓋所選 lag {top_lags}，跳過")
        continue

    # 建立 lag 特徵，訓練這個產品自己的線性迴歸模型
    X = pd.DataFrame({f'lag_{k}': ts.shift(k) for k in top_lags})
    valid = X.notna().all(axis=1)
    X_valid, y_valid = X[valid], ts[valid]

    lin_reg = LinearRegression()
    lin_reg.fit(X_valid, y_valid)
    print(f"{name}: 選用 lag {top_lags}，R² = {lin_reg.score(X_valid, y_valid):.2f}")

    # 用這個產品自己的模型，以最後一筆樣本的 lag 特徵預測明日價格
    last_lags = pd.DataFrame([ts.iloc[-np.array(top_lags)].values], columns=X.columns)
    y_pred = lin_reg.predict(last_lags)[0]

    predictions.append({
        "產品名稱": name,
        "預測明日菜價(元/公斤)": round(y_pred, 2)
    })

result_df = pd.DataFrame(predictions)
result_df.to_csv("veg_pred.csv", index=False, encoding="utf-8-sig")

print(f"✅ 已完成，輸出 veg_pred.csv（共 {len(result_df)} 項產品）")
