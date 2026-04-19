"""
Combined 2x2 visualization of the supplementary platform datasets.

Layout:
  | 58同城 price (log y)         | 安居客 price (log y)         |
  | 58同城 cumulative (base=100) | 安居客 cumulative (base=100) |

All cities are drawn as a pale "cloud"; ~12 highlighted cities are drawn
bold with English labels. The cross-city median is overlaid as an anchor.
Outputs PNG + PDF to supplementary/plots/.
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'add_data'))
from update_data import CITY_CN_TO_EN  # noqa: E402

EXTRA_CN_TO_EN = {
    '珠海': 'Zhuhai', '苏州': 'Suzhou', '莆田': 'Putian', '绍兴': 'Shaoxing',
    '漳州': 'Zhangzhou', '龙岩': 'Longyan', '东莞': 'Dongguan', '南通': 'Nantong',
    '湖州': 'Huzhou', '河源': 'Heyuan', '衢州': 'Quzhou', '台州': 'Taizhou',
    '昆山': 'Kunshan', '三明': 'Sanming', '镇江': 'Zhenjiang', '玉溪': 'Yuxi',
    '保定': 'Baoding', '廊坊': 'Langfang', '宜宾': 'Yibin', '汕头': 'Shantou',
    '泰安': "Tai'an",
}
CN_TO_EN = {**CITY_CN_TO_EN, **EXTRA_CN_TO_EN}

PLOTS_DIR = os.path.join(HERE, 'plots')
BASE_YEAR = 2015
CLOUD_COLOR = '#888888'
CLOUD_ALPHA = 0.08
MEDIAN_COLOR = '#222222'
HIGHLIGHT_CITIES = ['北京', '上海', '深圳', '广州', '杭州', '厦门',
                    '苏州', '南京', '成都', '三亚', '牡丹江', '泸州']

SOURCES = [
    ('58tongcheng_city_avg_price_annual_2010-2024.csv', '58.com'),
    ('anjuke_city_avg_price_annual_2015-2024.csv', 'anjuke.com'),
]


def load_series(csv_name):
    df = pd.read_csv(os.path.join(HERE, csv_name))
    df = df[df['year'] >= BASE_YEAR].dropna(subset=['price_yuan_per_sqm'])
    series = {}
    for city, g in df.groupby('city'):
        g = g.sort_values('year')
        years = g['year'].to_numpy(dtype=float)
        vals = g['price_yuan_per_sqm'].to_numpy(dtype=float)
        series[city] = (years, vals)
    return series


def to_cumulative(series):
    out = {}
    for city, (years, vals) in series.items():
        idx = np.where(years == BASE_YEAR)[0]
        if len(idx) == 0 or vals[idx[0]] == 0:
            continue
        out[city] = (years, vals / vals[idx[0]] * 100)
    return out


def median_by_year(series):
    buckets = {}
    for years, vals in series.values():
        for y, v in zip(years, vals):
            buckets.setdefault(int(y), []).append(v)
    ys = sorted(buckets)
    return np.array(ys, dtype=float), np.array([np.median(buckets[y]) for y in ys])


def draw_panel(ax, series, *, y_label, title, log_y, hline=None, show_labels=True):
    """Draw one subplot: cloud + median + highlighted cities."""
    # Cloud: all cities, pale
    for city, (years, vals) in series.items():
        if city in HIGHLIGHT_CITIES:
            continue
        ax.plot(years, vals, color=CLOUD_COLOR, linewidth=0.4,
                alpha=CLOUD_ALPHA, zorder=1)

    # Median line
    med_years, med_vals = median_by_year(series)
    ax.plot(med_years, med_vals, color=MEDIAN_COLOR,
            linewidth=1.8, alpha=0.85, zorder=2, label='Cross-city median')

    # Highlighted cities: viridis by final value among highlights
    highlights = {c: series[c] for c in HIGHLIGHT_CITIES if c in series}
    if highlights:
        finals = {c: v[-1] for c, (_, v) in highlights.items()}
        norm = mcolors.Normalize(vmin=min(finals.values()), vmax=max(finals.values()))
        cmap = cm.viridis
        for city, (years, vals) in highlights.items():
            color = cmap(norm(finals[city]))
            ax.plot(years, vals, color=color, linewidth=1.8, alpha=0.95, zorder=3)
            if show_labels:
                ax.annotate(CN_TO_EN.get(city, city),
                            xy=(years[-1], vals[-1]),
                            xytext=(5, 0), textcoords='offset points',
                            fontsize=8.5, fontweight='bold',
                            color=color, va='center', zorder=4)

    if hline is not None:
        ax.axhline(y=hline, color='gray', linestyle='--', linewidth=0.7, alpha=0.6)

    if log_y:
        ax.set_yscale('log')

    ax.set_xlabel('Year', fontsize=10)
    ax.set_ylabel(y_label, fontsize=10)
    ax.set_title(title, fontsize=12, fontweight='bold')
    xlim = ax.get_xlim()
    ax.set_xlim(xlim[0], xlim[1] + 1.2)
    year_end = int(np.floor(xlim[1]))
    xticks = list(range(BASE_YEAR, year_end + 1, 2))
    ax.set_xticks(xticks)
    ax.set_xticklabels([str(y) for y in xticks])
    ax.grid(True, linestyle=':', linewidth=0.4, alpha=0.5)
    ax.legend(loc='upper left', fontsize=8, frameon=False)


def main():
    plt.rcParams['font.sans-serif'] = [
        'PingFang HK', 'Heiti TC', 'Hiragino Sans GB',
        'STHeiti', 'Songti SC', 'Arial Unicode MS', 'sans-serif',
    ]
    plt.rcParams['axes.unicode_minus'] = False

    os.makedirs(PLOTS_DIR, exist_ok=True)
    fig, axes = plt.subplots(2, 2, figsize=(16, 11))

    for col, (csv_name, cn_label) in enumerate(SOURCES):
        series = load_series(csv_name)
        cum = to_cumulative(series)

        draw_panel(axes[0, col], series,
                   y_label='Avg Listing Price (RMB/m², log)',
                   title=f'{cn_label} — Avg Listing Price  ({len(series)} cities)',
                   log_y=True)

        draw_panel(axes[1, col], cum,
                   y_label=f'Cumulative Index (Base: {BASE_YEAR}=100)',
                   title=f'{cn_label} — Cumulative Growth  ({len(cum)} cities)',
                   log_y=False, hline=100)

        print(f'{cn_label}: {len(series)} cities (price) / {len(cum)} with {BASE_YEAR} base (cumulative)')

    fig.suptitle('China city-level listing prices: 58.com vs anjuke.com',
                 fontsize=14, fontweight='bold', y=0.995)
    plt.tight_layout(rect=[0, 0, 1, 0.98])

    png_path = os.path.join(PLOTS_DIR, 'platforms_overview_2x2.png')
    pdf_path = os.path.join(PLOTS_DIR, 'platforms_overview_2x2.pdf')
    plt.savefig(png_path, dpi=150, bbox_inches='tight')
    plt.savefig(pdf_path, bbox_inches='tight')
    plt.close(fig)
    print(f'Saved {png_path}')
    print(f'Saved {pdf_path}')


if __name__ == '__main__':
    main()
