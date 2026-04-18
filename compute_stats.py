"""
Compute each city's drop from its all-time-peak cumulative price index
(base Dec 2010 = 100), for new-home and existing-home overall indices.

Writes stats.md, stats.json, and refreshes the block between
<!-- STATS_START --> / <!-- STATS_END --> in README.md.
"""

import json
import os
from datetime import datetime, timezone

import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, 'merged_housing_data_eng.csv')
README_PATH = os.path.join(BASE_DIR, 'README.md')
STATS_MD_PATH = os.path.join(BASE_DIR, 'stats.md')
STATS_JSON_PATH = os.path.join(BASE_DIR, 'stats.json')

INDICES = [
    ('new_home_price_index', 'New Home'),
    ('existing_home_price_index', 'Existing Home'),
]
# Shanghai's reported new-home index is known-anomalous (see README); exclude
# it only from new-home stats. Existing-home data for Shanghai is fine.
EXCLUDE = {
    'new_home_price_index': {'Shanghai'},
    'existing_home_price_index': set(),
}
TOP_N = 30
STATS_START = '<!-- STATS_START -->'
STATS_END = '<!-- STATS_END -->'


def compute_drops(df, col):
    """For each city: peak (all-time max cumulative), current (last cumulative),
    drop_pct = (current - peak) / peak * 100 (<= 0), and peak_date YYYY-MM."""
    out = {}
    for city in df['city'].unique():
        city_data = df[df['city'] == city].sort_values(['year', 'month'])
        cum = 100.0
        cum_list = []
        dates = []
        for _, row in city_data.iterrows():
            v = row[col]
            if pd.notna(v):
                cum = cum * (v / 100.0)
            cum_list.append(cum)
            dates.append((int(row['year']), int(row['month'])))
        arr = np.array(cum_list)
        peak_idx = int(arr.argmax())
        peak = float(arr[peak_idx])
        current = float(arr[-1])
        drop_pct = (current - peak) / peak * 100.0
        out[city] = {
            'peak': round(peak, 4),
            'current': round(current, 4),
            'drop_pct': round(drop_pct, 4),
            'peak_date': f'{dates[peak_idx][0]}-{dates[peak_idx][1]:02d}',
        }
    return out


def summarize(drops):
    ranked = sorted(drops.items(), key=lambda kv: kv[1]['drop_pct'])
    n = len(ranked)
    top_n = ranked[:TOP_N]
    top_n_avg = sum(v['drop_pct'] for _, v in top_n) / len(top_n)
    all_avg = sum(v['drop_pct'] for _, v in ranked) / n
    worst_city, worst = ranked[0]
    best_city, best = ranked[-1]
    return {
        'n_cities': n,
        'top_n': TOP_N,
        'top_n_avg_drop_pct': round(top_n_avg, 4),
        'all_avg_drop_pct': round(all_avg, 4),
        'biggest_drop': {'city': worst_city, 'drop_pct': worst['drop_pct'], 'peak_date': worst['peak_date']},
        'smallest_drop': {'city': best_city, 'drop_pct': best['drop_pct'], 'peak_date': best['peak_date']},
    }


def as_of_date(df):
    last = df.sort_values(['year', 'month']).iloc[-1]
    return f'{int(last["year"])}-{int(last["month"]):02d}'


def fmt_pct(p):
    if abs(p) < 0.005:
        return '0.00%'
    return f'{p:+.2f}%'


def build_block(as_of, stats):
    n = stats['new_home_price_index']
    e = stats['existing_home_price_index']
    lines = [
        f'_As of {as_of}. Peak = each city\'s all-time high cumulative index since Dec 2010 (base=100). Drop is expressed as a negative percent; 0% means the city is still at its peak._',
        '',
        '| Metric | New Home | Existing Home |',
        '|---|---|---|',
        f'| Avg drop, {TOP_N} worst-hit cities | {fmt_pct(n["top_n_avg_drop_pct"])} | {fmt_pct(e["top_n_avg_drop_pct"])} |',
        f'| Avg drop, all cities ({n["n_cities"]} / {e["n_cities"]}) | {fmt_pct(n["all_avg_drop_pct"])} | {fmt_pct(e["all_avg_drop_pct"])} |',
        f'| Biggest drop | **{n["biggest_drop"]["city"]}** {fmt_pct(n["biggest_drop"]["drop_pct"])} (peak {n["biggest_drop"]["peak_date"]}) | **{e["biggest_drop"]["city"]}** {fmt_pct(e["biggest_drop"]["drop_pct"])} (peak {e["biggest_drop"]["peak_date"]}) |',
        f'| Smallest drop | **{n["smallest_drop"]["city"]}** {fmt_pct(n["smallest_drop"]["drop_pct"])} (peak {n["smallest_drop"]["peak_date"]}) | **{e["smallest_drop"]["city"]}** {fmt_pct(e["smallest_drop"]["drop_pct"])} (peak {e["smallest_drop"]["peak_date"]}) |',
    ]
    if n['excluded']:
        lines += ['', f'_New Home stats exclude {", ".join(n["excluded"])} due to known data anomalies._']
    return '\n'.join(lines)


def update_readme(block):
    with open(README_PATH, 'r', encoding='utf-8') as f:
        readme = f.read()
    if STATS_START not in readme or STATS_END not in readme:
        raise RuntimeError(f'Markers {STATS_START} / {STATS_END} not found in README.md')
    before, _, rest = readme.partition(STATS_START)
    _, _, after = rest.partition(STATS_END)
    new = f'{before}{STATS_START}\n{block}\n{STATS_END}{after}'
    with open(README_PATH, 'w', encoding='utf-8') as f:
        f.write(new)


def main():
    df = pd.read_csv(CSV_PATH)
    as_of = as_of_date(df)

    summary = {}
    per_city = {}
    for col, _ in INDICES:
        drops = compute_drops(df, col)
        per_city[col] = drops
        filtered = {c: v for c, v in drops.items() if c not in EXCLUDE[col]}
        summary[col] = summarize(filtered)
        summary[col]['excluded'] = sorted(EXCLUDE[col])

    block = build_block(as_of, summary)

    with open(STATS_MD_PATH, 'w', encoding='utf-8') as f:
        f.write(f'# Price Drop from Peak\n\n{block}\n')

    payload = {
        'as_of': as_of,
        'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'summary': summary,
        'per_city': per_city,
    }
    with open(STATS_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)

    update_readme(block)
    print(f'Stats written for as_of={as_of}')


if __name__ == '__main__':
    main()
