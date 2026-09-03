# -*- coding: utf-8 -*-
"""高雄果菜市場每日蔬菜行情爬蟲

抓取當日交易行情，依產品名稱計算以交易量加權的平均價，存成
today_veg_prices.csv，並合併進歷史資料 veg_prices_history.csv
（依交易日期＋產品名稱去重，保留最新一筆）。
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd

URL = "https://www.khfv.com.tw/pagepub/AppContent.aspx?GP=GP04.01"
TABLE_ID = "WR1_1_WG1"

response = requests.get(URL, timeout=30)
response.raise_for_status()
soup = BeautifulSoup(response.text, "html.parser")

table = soup.find('table', id=TABLE_ID)
if table is None:
    raise RuntimeError(f"找不到 ID 為 '{TABLE_ID}' 的表格，網站頁面可能已改版。")

all_rows = table.find_all('tr')
table_data = [
    [cell.text.strip() for cell in row.find_all(['td', 'th'])]
    for row in all_rows
]
table_data = [row for row in table_data if row]

if len(table_data) < 2:
    raise RuntimeError("表格內沒有抓到任何資料列。")

column_headers = table_data[0]
data_rows = table_data[1:]
print(f"抓到 {len(data_rows)} 筆交易紀錄，欄位：{column_headers}")

df = pd.DataFrame(data_rows, columns=column_headers)
df_selected = df[['交易日期', '產品名稱', '均價', '交易量(公斤)']].copy()

# 移除千分位逗號再轉成數字
df_selected['交易量(公斤)'] = pd.to_numeric(
    df_selected['交易量(公斤)'].astype(str).str.replace(',', '', regex=False),
    errors='coerce'
)
df_selected['均價'] = pd.to_numeric(df_selected['均價'], errors='coerce')

# 依「交易日期＋產品名稱」計算以交易量加權的平均價
df_weighted = (
    df_selected.groupby(['交易日期', '產品名稱'], as_index=False)
    .agg({
        '均價': lambda x: (x * df_selected.loc[x.index, '交易量(公斤)']).sum()
                          / df_selected.loc[x.index, '交易量(公斤)'].sum(),
        '交易量(公斤)': 'sum'
    })
    .rename(columns={'均價': '加權平均價(元/公斤)', '交易量(公斤)': '總交易量(公斤)'})
)
df_weighted['加權平均價(元/公斤)'] = df_weighted['加權平均價(元/公斤)'].round(6)

df_weighted.to_csv('today_veg_prices.csv', index=False)
print(f"已輸出 today_veg_prices.csv（{len(df_weighted)} 項產品）")

# 合併進歷史資料，依交易日期＋產品名稱去重（保留最新一筆，也就是今天抓到的資料）
df_history = pd.read_csv('veg_prices_history.csv')
df_merged = pd.concat([df_history, df_weighted], ignore_index=True)
df_merged.drop_duplicates(subset=['交易日期', '產品名稱'], keep='last', inplace=True)
df_merged.to_csv('veg_prices_history.csv', float_format="%.6f", index=False)

print(f"合併後的歷史資料已存回 veg_prices_history.csv（共 {len(df_merged)} 筆）")
