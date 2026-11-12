<p align="center">
  <a href="https://fusionproxy.net/?utm_source=github&utm_medium=scrape-sitemap-python">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/FusionProxies/.github/main/assets/logo-on-dark.png">
      <img src="https://raw.githubusercontent.com/FusionProxies/.github/main/assets/logo-on-light.png" alt="Fusion Proxy" height="52">
    </picture>
  </a>
</p>

# How to get all URLs of a website from its sitemap (Python)

Before you crawl a site link by link, read its sitemap: most websites publish a list of every page they want found, often with the date each page last changed. [`sitemap_urls.py`](sitemap_urls.py) finds the sitemaps through `robots.txt`, follows sitemap indexes, opens `.gz` sitemaps, filters by date and path, checks `robots.txt` rules and saves the result.

```bash
pip install -r requirements.txt
python sitemap_urls.py https://fusionproxy.net
```

```
1 sitemap(s) in robots.txt, 8 sitemap files, 639 URLs
639 after filters, 639 allowed by robots.txt
    130  sitemap-residential-locations.xml
    130  sitemap-mobile-locations.xml
    115  sitemap-datacenter-locations.xml
    ...
```

Only what changed recently, in one section, as CSV:

```bash
python sitemap_urls.py https://fusionproxy.net --since 2026-11-10 --match /proxies/ --csv urls.csv
```

```
7 after filters, 7 allowed by robots.txt
  2026-11-10  /proxies/residential
  2026-11-10  /proxies/isp
  ...
saved 7 URLs to urls.csv
```

## How sitemaps work

**Where to find them.** `robots.txt` lists them on `Sitemap:` lines. If there are none, try `/sitemap.xml`, `/sitemap_index.xml` or `/sitemap-index.xml`.

**Two kinds of files.** A *sitemap index* lists other sitemaps; a *urlset* lists pages. Big sites nest them, split by section or by month:

```xml
<sitemapindex>
  <sitemap><loc>https://example.com/sitemap-products-1.xml.gz</loc></sitemap>
</sitemapindex>

<urlset>
  <url><loc>https://example.com/product/42</loc><lastmod>2026-11-10</lastmod></url>
</urlset>
```

**Compressed files.** Sitemaps ending in `.gz` are gzip files; the script recognises them by name or by their first two bytes and decompresses them.

The core is a few lines of the standard library:

```python
import xml.etree.ElementTree as ET
NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

root = ET.fromstring(xml_bytes)
if root.tag.endswith("sitemapindex"):
    children = [loc.text for loc in root.findall("sm:sitemap/sm:loc", NS)]   # read each one
else:
    pages = [(u.find("sm:loc", NS).text, u.findtext("sm:lastmod", "", NS)) for u in root.findall("sm:url", NS)]
```

## Why use the sitemap

- **Complete**: pages that no menu links to are often still in the sitemap.
- **Cheap**: one request per sitemap instead of one per page to discover links.
- **Incremental**: `lastmod` tells you what changed since your last run, so you re-scrape only those pages.

`lastmod` is only as good as the site's generator: some sites stamp every URL with today's date. Compare with your own previous run if dates look suspicious.

## Respect robots.txt

The script fetches `robots.txt` once, reads the sitemaps and the rules from it, and keeps only URLs your user agent may fetch (`urllib.robotparser`). If a site has no `robots.txt` (a `4xx` answer) everything is allowed; if the server fails (`5xx`) the script fetches nothing, which is how search engines behave too. Set a descriptive User-Agent with a way to contact you.

## Through a proxy

Large sites rate-limit sitemap downloads like any other request. With `FUSION_USER` and `FUSION_PASS` set, the script uses a residential proxy with one sticky IP for the run.

## Next steps

Feed the URL list to a scraper: [python-web-scraping](https://github.com/FusionProxies/python-web-scraping) for a few hundred pages, [python-async-scraping](https://github.com/FusionProxies/python-async-scraping) or [scrapy-proxy-middleware](https://github.com/FusionProxies/scrapy-proxy-middleware) for many thousands.

[Fusion Proxy residential proxies](https://fusionproxy.net/proxies/residential?utm_source=github&utm_medium=scrape-sitemap-python) from $2.95/GB, with a [free trial](https://fusionproxy.net/free-trial?utm_source=github&utm_medium=scrape-sitemap-python).

## License

MIT, see [LICENSE](LICENSE).
