"""Get every URL of a website from its sitemaps: robots.txt discovery, sitemap indexes, .gz files.

    pip install -r requirements.txt
    python sitemap_urls.py https://fusionproxy.net
    python sitemap_urls.py https://fusionproxy.net --since 2026-11-01 --match /proxies/ --csv urls.csv
"""
import argparse
import csv
import gzip
import os
import random
import urllib.robotparser
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse

import requests

NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
UA = "Mozilla/5.0 (compatible; sitemap-reader/1.0; +https://github.com/FusionProxies/scrape-sitemap-python)"


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = UA
    user, password = os.environ.get("FUSION_USER"), os.environ.get("FUSION_PASS")
    if user and password:  # optional residential proxy, one sticky IP for the run
        sid = random.randint(1000000, 9999999)
        proxy = f"http://{user}-country-us-sessid-{sid}-sessTime-1800s:{password}@resi.fusionproxy.net:12286"
        s.proxies.update({"http": proxy, "https": proxy})
    return s


def load_robots(session: requests.Session, site: str) -> tuple[urllib.robotparser.RobotFileParser, list[str]]:
    """Fetch robots.txt once: the rules, and the sitemaps it lists ('Sitemap: <url>' lines)."""
    rp = urllib.robotparser.RobotFileParser()
    try:
        r = session.get(urljoin(site, "/robots.txt"), timeout=30)
        status, text = r.status_code, r.text
    except requests.RequestException:
        status, text = 0, ""
    if status == 200:
        rp.parse(text.splitlines())
    elif 400 <= status < 500:
        rp.allow_all = True      # no robots.txt: everything is allowed
    else:
        rp.disallow_all = True   # server error: be careful and fetch nothing
    found = [line.split(":", 1)[1].strip() for line in text.splitlines() if line.lower().startswith("sitemap:")]
    return rp, found or [urljoin(site, "/sitemap.xml")]


def read_sitemap(session: requests.Session, url: str, seen: set) -> list[dict]:
    """Parse one sitemap; follow sitemap indexes recursively; handle .gz."""
    if url in seen:
        return []
    seen.add(url)
    r = session.get(url, timeout=60)
    r.raise_for_status()
    body = r.content
    if url.endswith(".gz") or body[:2] == b"\x1f\x8b":
        body = gzip.decompress(body)
    root = ET.fromstring(body)
    tag = root.tag.split("}")[-1]
    if tag == "sitemapindex":
        urls = []
        for loc in root.findall("sm:sitemap/sm:loc", NS):
            urls += read_sitemap(session, loc.text.strip(), seen)
        return urls
    out = []
    for u in root.findall("sm:url", NS):
        lastmod = u.find("sm:lastmod", NS)
        out.append({"url": u.find("sm:loc", NS).text.strip(), "lastmod": lastmod.text.strip() if lastmod is not None else "",
                    "sitemap": url.rsplit("/", 1)[-1]})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("site", help="site root, for example https://example.com")
    ap.add_argument("--since", help="only URLs with lastmod on or after this date (YYYY-MM-DD)")
    ap.add_argument("--match", help="only URLs containing this text")
    ap.add_argument("--csv", help="write the result to this CSV file")
    a = ap.parse_args()

    session = make_session()
    rp, roots = load_robots(session, a.site)
    urls, seen = [], set()
    for sm in roots:
        try:
            urls += read_sitemap(session, sm, seen)
        except (requests.RequestException, ET.ParseError) as e:
            print(f"cannot read {sm}: {e}")
    print(f"{len(roots)} sitemap(s) in robots.txt, {len(seen)} sitemap files, {len(urls)} URLs")

    if a.since:
        urls = [u for u in urls if u["lastmod"][:10] >= a.since]
    if a.match:
        urls = [u for u in urls if a.match in u["url"]]

    # respect robots.txt: keep only URLs our user agent may fetch
    allowed = [u for u in urls if rp.can_fetch(UA, u["url"])]
    print(f"{len(urls)} after filters, {len(allowed)} allowed by robots.txt")

    by_sitemap = {}
    for u in allowed:
        by_sitemap[u["sitemap"]] = by_sitemap.get(u["sitemap"], 0) + 1
    for name, n in sorted(by_sitemap.items(), key=lambda x: -x[1]):
        print(f"  {n:5}  {name}")
    for u in allowed[:5]:
        print(f"  {u['lastmod'][:10] or '-':10}  {urlparse(u['url']).path}")

    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["url", "lastmod", "sitemap"])
            w.writeheader()
            w.writerows(allowed)
        print(f"saved {len(allowed)} URLs to {a.csv}")


if __name__ == "__main__":
    main()
