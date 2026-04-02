"""
Plot cumulative growth of all 8 housing price indices for 70 Chinese cities.
Base: Dec 2010 = 100. Outputs PNG files to plots/ directory.
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors

PLOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plots')
CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'merged_housing_data_eng.csv')

# All 8 indices and their display titles / filenames
INDICES = [
    ('new_house_price_index',        'New House Price Index (Overall)'),
    ('second_hand_price_index',      'Second-hand House Price Index (Overall)'),
    ('new_small_house_index',        'New House Price Index (≤90m²)'),
    ('new_medium_house_index',       'New House Price Index (90-144m²)'),
    ('new_large_house_index',        'New House Price Index (>144m²)'),
    ('second_small_house_index',     'Second-hand House Price Index (≤90m²)'),
    ('second_medium_house_index',    'Second-hand House Price Index (90-144m²)'),
    ('second_large_house_index',     'Second-hand House Price Index (>144m²)'),
]

# Cities to label: top/bottom performers + major cities
LABEL_CITIES = ['Shenzhen', 'Beijing', 'Shanghai', 'Guangzhou', 'Hefei',
                'Jinzhou', 'Wenzhou', 'Mudanjiang']


def compute_cumulative(df, col):
    """Compute cumulative index (base Dec 2010 = 100) for each city."""
    cumulative = {}
    for city in df['city'].unique():
        city_data = df[df['city'] == city].sort_values(['year', 'month'])
        cum = 100.0
        cum_list = []
        dates = []
        for _, row in city_data.iterrows():
            v = row[col]
            if pd.notna(v):
                cum = cum * (v / 100)
            cum_list.append(cum)
            dates.append(row['year'] + (row['month'] - 1) / 12)
        cumulative[city] = (np.array(dates), np.array(cum_list))
    return cumulative


def plot_index(cumulative, title, filename):
    """Generate one cumulative growth plot."""
    final_values = {city: vals[-1] for city, (_, vals) in cumulative.items()}

    fig, ax = plt.subplots(figsize=(14, 8))

    vmin = min(final_values.values())
    vmax = max(final_values.values())
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    cmap = cm.viridis

    # Draw background cities first, then labeled ones on top
    for city in sorted(cumulative, key=lambda c: c in LABEL_CITIES):
        dates, vals = cumulative[city]
        color = cmap(norm(final_values[city]))
        if city in LABEL_CITIES:
            ax.plot(dates, vals, color=color, linewidth=2.0, alpha=0.95, zorder=3)
            ax.annotate(city, xy=(dates[-1], vals[-1]),
                        xytext=(5, 0), textcoords='offset points',
                        fontsize=10, fontweight='bold', color=color,
                        va='center', zorder=4)
        else:
            ax.plot(dates, vals, color=color, linewidth=0.7, alpha=0.35, zorder=1)

    ax.axhline(y=100, color='gray', linestyle='--', linewidth=0.8, alpha=0.6)

    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, pad=0.02)
    cbar.set_label('Cumulative Growth Rate', fontsize=11)

    ax.set_xlabel('Year', fontsize=12)
    ax.set_ylabel('Cumulative Price Index (Base: Dec 2010=100)', fontsize=12)
    ax.set_title(f'Cumulative Growth of {title} (Base: Dec 2010=100)',
                 fontsize=14, fontweight='bold')
    xlim = ax.get_xlim()
    ax.set_xlim(xlim[0], xlim[1] + 1.0)
    year_end = int(np.floor(xlim[1]))  # use data range, not padded xlim
    xticks = [2011] + list(range(2012, year_end + 1, 2))
    ax.set_xticks(xticks)
    ax.set_xticklabels([str(y) for y in xticks])

    plt.tight_layout()
    png_path = os.path.join(PLOTS_DIR, filename)
    pdf_path = os.path.join(PLOTS_DIR, filename.replace('.png', '.pdf'))
    plt.savefig(png_path, dpi=150, bbox_inches='tight')
    plt.savefig(pdf_path, bbox_inches='tight')
    plt.close(fig)
    print(f'  Saved {filename} + .pdf')


def main():
    os.makedirs(PLOTS_DIR, exist_ok=True)
    df = pd.read_csv(CSV_PATH)
    print(f'Generating {len(INDICES)} plots...')

    for col, title in INDICES:
        cumulative = compute_cumulative(df, col)
        filename = f'{col}_cumulative.png'
        plot_index(cumulative, title, filename)

    print('Done.')


if __name__ == '__main__':
    main()
