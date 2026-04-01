"""
Parse housing index HTML files from China's National Bureau of Statistics
and append new data to merged_housing_data_eng.csv.
"""

import os
import re
import csv
from bs4 import BeautifulSoup

# City name cleaning: remove spaces, asterisks, rename
CITY_NAME_MAPPING = {'襄樊': '襄阳'}

CITY_CN_TO_EN = {
    "三亚": "Sanya", "上海": "Shanghai", "丹东": "Dandong",
    "乌鲁木齐": "Urumqi", "九江": "Jiujiang", "兰州": "Lanzhou",
    "包头": "Baotou", "北京": "Beijing", "北海": "Beihai",
    "南京": "Nanjing", "南充": "Nanchong", "南宁": "Nanning",
    "南昌": "Nanchang", "厦门": "Xiamen", "合肥": "Hefei",
    "吉林": "Jilin", "呼和浩特": "Hohhot", "哈尔滨": "Harbin",
    "唐山": "Tangshan", "大理": "Dali", "大连": "Dalian",
    "天津": "Tianjin", "太原": "Taiyuan", "宁波": "Ningbo",
    "安庆": "Anqing", "宜昌": "Yichang", "岳阳": "Yueyang",
    "常德": "Changde", "平顶山": "Pingdingshan", "广州": "Guangzhou",
    "徐州": "Xuzhou", "惠州": "Huizhou", "成都": "Chengdu",
    "扬州": "Yangzhou", "无锡": "Wuxi", "昆明": "Kunming",
    "杭州": "Hangzhou", "桂林": "Guilin", "武汉": "Wuhan",
    "沈阳": "Shenyang", "泉州": "Quanzhou", "泸州": "Luzhou",
    "洛阳": "Luoyang", "济南": "Jinan", "济宁": "Jining",
    "海口": "Haikou", "深圳": "Shenzhen", "温州": "Wenzhou",
    "湛江": "Zhanjiang", "烟台": "Yantai", "牡丹江": "Mudanjiang",
    "石家庄": "Shijiazhuang", "福州": "Fuzhou", "秦皇岛": "Qinhuangdao",
    "蚌埠": "Bengbu", "襄阳": "Xiangyang", "西宁": "Xining",
    "西安": "Xi'an", "贵阳": "Guiyang", "赣州": "Ganzhou",
    "遵义": "Zunyi", "郑州": "Zhengzhou", "重庆": "Chongqing",
    "金华": "Jinhua", "银川": "Yinchuan", "锦州": "Jinzhou",
    "长春": "Changchun", "长沙": "Changsha", "青岛": "Qingdao",
    "韶关": "Shaoguan",
}


def clean_city_name(raw):
    """Remove spaces, asterisks, and apply name mapping."""
    name = re.sub(r'\s+', '', raw).replace('*', '').strip()
    return CITY_NAME_MAPPING.get(name, name)


def get_cell_text(td):
    """Extract text from a <td>, stripping whitespace."""
    return td.get_text(strip=True)


def parse_float(s):
    """Parse a float from string, return empty string if invalid."""
    try:
        return float(s)
    except (ValueError, TypeError):
        return ''


def parse_table_1_2(table):
    """
    Parse Table 1 or 2 (new/used housing price index).
    January layout (6 cols): [city1 | 环比 | 同比 | city2 | 环比 | 同比]
    Other months (8 cols): [city1 | 环比 | 同比 | 1-X月平均 | city2 | 环比 | 同比 | 1-X月平均]
    Skip first 2 header rows. Returns dict: {city_cn: huanbi_value}
    """
    rows = table.find_all('tr')
    result = {}
    for row in rows[2:]:  # skip 2 header rows
        cells = row.find_all('td')
        ncols = len(cells)
        if ncols == 8:  # months 2-12: has 1-X月平均 column
            city1_idx, val1_idx, city2_idx, val2_idx = 0, 1, 4, 5
        elif ncols == 6:  # January: no average column
            city1_idx, val1_idx, city2_idx, val2_idx = 0, 1, 3, 4
        else:
            continue
        # Left city
        city1 = clean_city_name(get_cell_text(cells[city1_idx]))
        val1 = parse_float(get_cell_text(cells[val1_idx]))
        if city1 and city1 != '城市':
            result[city1] = val1
        # Right city
        city2 = clean_city_name(get_cell_text(cells[city2_idx]))
        val2 = parse_float(get_cell_text(cells[val2_idx]))
        if city2 and city2 != '城市':
            result[city2] = val2
    return result


def parse_table_3_4_half(table):
    """
    Parse one half (一 or 二) of Table 3 or 4 (housing by size).
    January (7 cols): [city | 90m² 环比 | 同比 | 90-144m² 环比 | 同比 | 144m²+ 环比 | 同比]
    Other months (10 cols): [city | 90m² 环比 | 同比 | avg | 90-144m² 环比 | 同比 | avg | 144m²+ 环比 | 同比 | avg]
    Skip first 3 header rows. Returns dict: {city_cn: (small, medium, large)}
    """
    rows = table.find_all('tr')
    result = {}
    for row in rows[3:]:  # skip 3 header rows
        cells = row.find_all('td')
        ncols = len(cells)
        if ncols == 10:  # months 2-12: has average columns
            small_idx, med_idx, large_idx = 1, 4, 7
        elif ncols == 7:  # January
            small_idx, med_idx, large_idx = 1, 3, 5
        else:
            continue
        city = clean_city_name(get_cell_text(cells[0]))
        if not city or city == '城市':
            continue
        small = parse_float(get_cell_text(cells[small_idx]))
        medium = parse_float(get_cell_text(cells[med_idx]))
        large = parse_float(get_cell_text(cells[large_idx]))
        result[city] = (small, medium, large)
    return result


def parse_html_file(filepath):
    """
    Parse a single HTML file and return list of row dicts.
    """
    basename = os.path.basename(filepath)
    yyyymm = basename.replace('.html', '')
    year = int(yyyymm[:4])
    month = int(yyyymm[4:6])

    with open(filepath, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    tables = soup.find_all('table')
    # HTML has duplicate tables (desktop + mobile). Take first 8.
    # Mapping: [0]=Table1, [1]=Table2, [2]=Table3(一), [3]=Table3(二),
    #          [4]=Table4(一), [5]=Table4(二)
    # But some files may have different counts; let's identify by preceding text.
    # Safer approach: use the first 6 tables only from the first content block.
    if len(tables) < 6:
        print(f"WARNING: {filepath} has only {len(tables)} tables, expected >= 6")
        return []

    # Take first 6 tables (the first content div)
    t1 = tables[0]  # new house price index
    t2 = tables[1]  # used house price index
    t3a = tables[2]  # new by size (一) - first 35 cities
    t3b = tables[3]  # new by size (二) - next 35 cities
    t4a = tables[4]  # used by size (一) - first 35 cities
    t4b = tables[5]  # used by size (二) - next 35 cities

    new_price = parse_table_1_2(t1)
    used_price = parse_table_1_2(t2)
    new_size_a = parse_table_3_4_half(t3a)
    new_size_b = parse_table_3_4_half(t3b)
    used_size_a = parse_table_3_4_half(t4a)
    used_size_b = parse_table_3_4_half(t4b)

    # Merge size tables
    new_size = {**new_size_a, **new_size_b}
    used_size = {**used_size_a, **used_size_b}

    # Collect all cities
    all_cities = set(new_price) | set(used_price) | set(new_size) | set(used_size)

    rows = []
    for city_cn in sorted(all_cities):
        city_en = CITY_CN_TO_EN.get(city_cn)
        if not city_en:
            print(f"WARNING: Unknown city '{city_cn}' in {basename}")
            continue

        new_s = new_size.get(city_cn, ('', '', ''))
        used_s = used_size.get(city_cn, ('', '', ''))

        rows.append({
            'city': city_en,
            'year': year,
            'month': month,
            'new_house_price_index': new_price.get(city_cn, ''),
            'second_hand_price_index': used_price.get(city_cn, ''),
            'new_small_house_index': new_s[0],
            'new_medium_house_index': new_s[1],
            'new_large_house_index': new_s[2],
            'second_small_house_index': used_s[0],
            'second_medium_house_index': used_s[1],
            'second_large_house_index': used_s[2],
        })

    return rows


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.dirname(script_dir)
    csv_path = os.path.join(repo_dir, 'merged_housing_data_eng.csv')

    # Find all HTML files
    html_files = sorted([
        os.path.join(script_dir, f)
        for f in os.listdir(script_dir)
        if f.endswith('.html') and f[:6].isdigit()
    ])

    print(f"Found {len(html_files)} HTML files to process")

    all_new_rows = []
    for filepath in html_files:
        rows = parse_html_file(filepath)
        print(f"  {os.path.basename(filepath)}: {len(rows)} cities")
        all_new_rows.extend(rows)

    print(f"\nTotal new rows: {len(all_new_rows)}")

    # Read existing data to check for duplicates
    existing_keys = set()
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row['city'], int(row['year']), int(row['month']))
            existing_keys.add(key)

    # Filter out duplicates
    new_rows = [
        r for r in all_new_rows
        if (r['city'], r['year'], r['month']) not in existing_keys
    ]
    skipped = len(all_new_rows) - len(new_rows)
    if skipped:
        print(f"Skipped {skipped} duplicate rows")

    # Append to CSV
    if new_rows:
        fieldnames = [
            'city', 'year', 'month', 'new_house_price_index',
            'second_hand_price_index', 'new_small_house_index',
            'new_medium_house_index', 'new_large_house_index',
            'second_small_house_index', 'second_medium_house_index',
            'second_large_house_index'
        ]
        with open(csv_path, 'a', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writerows(new_rows)
        print(f"Appended {len(new_rows)} rows to {csv_path}")
    else:
        print("No new rows to append")


if __name__ == '__main__':
    main()
