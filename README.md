# 70 China Cities Housing Index Data

Monthly housing price index data for 70 major Chinese cities, published by the National Bureau of Statistics of China. Collected and cleaned by Chang Gao.

**Current coverage: 2011.1 - 2026.2**

## Data Description

The dataset (`merged_housing_data_eng.csv`) contains monthly residential housing (商品住宅) price indices (month-on-month, previous month = 100) for 70 cities across 8 indicators:

| Column | Description |
|---|---|
| `new_house_price_index` | New residential housing price index (overall) |
| `second_hand_price_index` | Used residential housing price index (overall) |
| `new_small_house_index` | New residential, 90m² or smaller |
| `new_medium_house_index` | New residential, 90-144m² |
| `new_large_house_index` | New residential, larger than 144m² |
| `second_small_house_index` | Used residential, 90m² or smaller |
| `second_medium_house_index` | Used residential, 90-144m² |
| `second_large_house_index` | Used residential, larger than 144m² |

## Automated Monthly Updates

A GitHub Actions workflow runs on the 28th of each month to automatically:

1. Fetch new data pages from [stats.gov.cn](https://www.stats.gov.cn/sj/zxfb/)
2. Parse the HTML tables and extract month-on-month indices
3. Append new rows to the CSV and commit

The workflow can also be triggered manually from the Actions tab.

## Manual Update

To update manually:

```bash
# Fetch new HTML from stats.gov.cn
python3 add_data/fetch_new_data.py

# Parse and append to CSV
python3 add_data/update_data.py
```

Or place HTML files manually as `add_data/YYYYMM.html` and run `update_data.py`. Duplicate months are automatically skipped.
