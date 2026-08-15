"""
Fetch the latest housing index HTML from stats.gov.cn.
Checks the listing pages for new monthly data, downloads if not already present.
"""

import os
import re
import sys
import time
import urllib.request
import urllib.error

LISTING_URL = "https://www.stats.gov.cn/sj/zxfb/"
# The first listing page only holds ~2 weeks of releases, while the housing
# index comes out around the 15th-18th. A run late in the month can therefore
# miss it entirely (2026-06 data, published 2026-07-15, was lost this way), so
# fall back to the paginated older pages too.
LISTING_PAGES = 3
TITLE_PATTERN = r'(\d{4})年(\d{1,2})月份?70个大中城市商品住宅销售价格变动情况'
# Tempered greedy token (?:(?!</a>).)*? prevents the match from spanning across
# multiple <a> tags — without it, an earlier unrelated link could be paired with
# a later housing-index title elsewhere on the listing page.
LINK_PATTERN = re.compile(
    r'href=["\'](\./\d+/t\d+_\d+\.html)["\'][^>]*>(?:(?!</a>).)*?' + TITLE_PATTERN,
    re.DOTALL
)


def fetch_url(url, retries=3):
    """Fetch URL content with retries."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/120.0.0.0 Safari/537.36'
    }
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.read().decode('utf-8')
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"  Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(5)
    return None


def find_housing_links(html):
    """Find all housing index links on the listing page.
    Returns list of (relative_url, year, month). Deduped — the listing markup
    repeats the title in both the title="..." attribute and the link text.
    """
    seen = set()
    results = []
    for match in LINK_PATTERN.finditer(html):
        rel_url, year, month = match.group(1), int(match.group(2)), int(match.group(3))
        key = (rel_url, year, month)
        if key in seen:
            continue
        seen.add(key)
        results.append(key)
    return results


def listing_page_urls():
    """URLs of the listing pages to scan: the index, then the older pages."""
    yield LISTING_URL
    for page in range(1, LISTING_PAGES):
        yield f"{LISTING_URL}index_{page}.html"


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    links = []
    seen = set()
    fetched_any = False
    for url in listing_page_urls():
        print(f"Fetching listing page: {url}")
        listing_html = fetch_url(url)
        if not listing_html:
            print(f"  WARNING: Failed to fetch {url}")
            continue
        fetched_any = True
        for key in find_housing_links(listing_html):
            if key not in seen:
                seen.add(key)
                links.append(key)

    if not fetched_any:
        print("ERROR: Failed to fetch any listing page")
        sys.exit(1)

    if not links:
        print("No housing index links found on listing pages")
        sys.exit(0)

    print(f"Found {len(links)} housing index link(s)")

    downloaded = 0
    for rel_url, year, month in links:
        filename = f"{year}{month:02d}.html"
        filepath = os.path.join(script_dir, filename)

        if os.path.exists(filepath):
            print(f"  {filename} already exists, skipping")
            continue

        full_url = LISTING_URL + rel_url.lstrip('./')
        print(f"  Downloading {year}-{month:02d} from {full_url}")
        html = fetch_url(full_url)
        if html:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"  Saved to {filename}")
            downloaded += 1
        else:
            print(f"  ERROR: Failed to download {full_url}")

    print(f"\nDownloaded {downloaded} new file(s)")
    return downloaded


if __name__ == '__main__':
    count = main()
    # Exit with code 0 even if nothing new — not an error
