#!/usr/bin/env python3
import os, re, hashlib, warnings, urllib.parse as up
warnings.filterwarnings("ignore")
import requests
from bs4 import BeautifulSoup

BASE = "https://www.higney-international.com"
OUT = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(OUT, "assets")
os.makedirs(ASSETS, exist_ok=True)

PAGES = {
    "home": "/home",
    "about": "/about",
    "projects": "/projects",
    "fulfillment": "/fulfillment",
    "team": "/team",
    "contact": "/contact-7",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
sess = requests.Session()
sess.headers.update(HEADERS)

asset_map = {}

def fetch(url):
    try:
        r = sess.get(url, timeout=30, verify=False)
        if r.status_code == 200:
            return r
    except Exception as e:
        print("  ! fetch fail", url, e)
    return None

def save_asset(url):
    url = up.urljoin(BASE, url.split("?")[0] if "?" not in url else url)
    if url in asset_map:
        return asset_map[url]
    r = fetch(url)
    if not r:
        return None
    clean = url.split("?")[0]
    ext = os.path.splitext(up.urlparse(clean).path)[1] or ".bin"
    h = hashlib.md5(url.encode()).hexdigest()[:10]
    name = re.sub(r'[^a-zA-Z0-9._-]', '_', os.path.basename(clean))[:40] or "asset"
    fn = f"{h}_{name}{'' if name.endswith(ext) else ext}"
    with open(os.path.join(ASSETS, fn), "wb") as f:
        f.write(r.content)
    rel = f"assets/{fn}"
    asset_map[url] = rel
    print("  + asset", rel, f"({len(r.content)//1024}kb)")
    return rel

for name, path in PAGES.items():
    print("PAGE", name)
    r = fetch(BASE + path)
    if not r:
        continue
    soup = BeautifulSoup(r.text, "html.parser")

    # CSS
    for link in soup.find_all("link", href=True):
        if link.get("rel") and "stylesheet" in link.get("rel") or link["href"].endswith(".css"):
            rel = save_asset(link["href"])
            if rel:
                link["href"] = rel
    # icons / preload images via link
    for link in soup.find_all("link", href=True):
        if "icon" in (" ".join(link.get("rel", []))):
            rel = save_asset(link["href"])
            if rel:
                link["href"] = rel

    # JS
    for s in soup.find_all("script", src=True):
        rel = save_asset(s["src"])
        if rel:
            s["src"] = rel

    # images (src + data-src for lazy)
    for img in soup.find_all("img"):
        for attr in ("src", "data-src", "data-image"):
            if img.get(attr) and img[attr].startswith(("http", "//", "/")):
                rel = save_asset(img[attr])
                if rel:
                    img[attr] = rel
        # srcset
        if img.get("srcset"):
            parts = []
            for piece in img["srcset"].split(","):
                seg = piece.strip().split(" ")
                rel = save_asset(seg[0])
                if rel:
                    parts.append(rel + ((" " + seg[1]) if len(seg) > 1 else ""))
            if parts:
                img["srcset"] = ", ".join(parts)

    # rewrite internal nav links to local html files
    for a in soup.find_all("a", href=True):
        href = a["href"]
        p = up.urlparse(href).path.rstrip("/")
        for n, pa in PAGES.items():
            if p == pa or p == pa.rstrip("/"):
                a["href"] = ("index.html" if n == "home" else f"{n}.html")
                break

    outname = "index.html" if name == "home" else f"{name}.html"
    with open(os.path.join(OUT, outname), "w", encoding="utf-8") as f:
        f.write(str(soup))
    print("  -> wrote", outname)

print("DONE. assets:", len(asset_map))
