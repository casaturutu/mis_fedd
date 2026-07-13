#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generar_feeds.py — Genera feeds RSS a partir de una lista de URLs (fuentes.txt)
y los guarda en la carpeta feeds/. Pensado para ejecutarse automáticamente
con GitHub Actions y servir los XML mediante URLs públicas (raw.githubusercontent.com),
que luego se añaden a un lector online como feedreader.com.

Admite:
  * Perfiles públicos de Instagram (via espejo imginn.com)
  * Perfiles de imginn.com
  * Blogs/webs genéricas (extracción heurística de artículos)

Uso local:   python generar_feeds.py
Requisitos:  pip install requests beautifulsoup4
"""

import os
import re
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from urllib.parse import urljoin, urlparse
from xml.sax.saxutils import escape

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}
MAX_ITEMS = 20
FUENTES = "fuentes.txt"
CARPETA_SALIDA = "feeds"


def log(msg):
    print(msg, flush=True)


def fetch(url):
    resp = requests.get(url, headers=HEADERS, timeout=25)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def instagram_to_imginn(url):
    path = urlparse(url).path.strip("/")
    username = path.split("/")[0] if path else ""
    if not username:
        raise ValueError(f"No se pudo extraer el usuario de: {url}")
    return f"https://imginn.com/{username}/"


def now_rfc822():
    return format_datetime(datetime.now(timezone.utc))


def slug(url):
    """Nombre de archivo seguro a partir de la URL."""
    p = urlparse(url)
    s = (p.netloc + p.path).strip("/").replace("/", "-")
    s = re.sub(r"[^\w\-.]", "_", s)
    return s[:80] or "feed"


# ---------------- extractores ----------------
def extract_imginn(url):
    soup = fetch(url)
    username = urlparse(url).path.strip("/").split("/")[0]
    title_tag = soup.find("title")
    feed_title = title_tag.get_text(strip=True) if title_tag else f"Instagram @{username}"

    items, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not re.search(r"/(p|reel|tv)/[\w\-]+", href):
            continue
        link = urljoin(url, href)
        if link in seen:
            continue
        seen.add(link)

        img = a.find("img")
        caption, img_src = "", ""
        if img:
            caption = (img.get("alt") or "").strip()
            img_src = img.get("data-src") or img.get("src") or ""

        parent = a.find_parent()
        time_tag = (parent.find("time") if parent else None) or a.find("time")
        pub = ""
        if time_tag and time_tag.get("datetime"):
            try:
                dt = datetime.fromisoformat(time_tag["datetime"].replace("Z", "+00:00"))
                pub = format_datetime(dt)
            except ValueError:
                pass

        title = caption[:120] if caption else f"Publicación de @{username}"
        desc = f'<img src="{escape(img_src)}" /><br/>{escape(caption)}' if img_src else caption
        items.append({"title": title, "link": link, "description": desc, "pubDate": pub})
        if len(items) >= MAX_ITEMS:
            break

    if not items:
        raise RuntimeError("Sin publicaciones (perfil privado, inexistente o bloqueo de imginn).")
    return {"title": feed_title, "link": url,
            "description": f"Feed generado desde {url}", "items": items}


def extract_generic(url):
    soup = fetch(url)
    title_tag = soup.find("title")
    feed_title = title_tag.get_text(strip=True) if title_tag else url

    alt = soup.find("link", attrs={"type": re.compile(r"application/(rss|atom)\+xml")})
    if alt and alt.get("href"):
        log(f"  AVISO: esta web ya tiene feed propio: {urljoin(url, alt['href'])}")

    items, seen = [], set()
    for art in soup.find_all("article"):
        h = art.find(["h1", "h2", "h3"])
        a = (h.find("a", href=True) if h else None) or art.find("a", href=True)
        if not a:
            continue
        link = urljoin(url, a["href"])
        if link in seen:
            continue
        seen.add(link)
        title = (h.get_text(strip=True) if h else a.get_text(strip=True)) or link
        p = art.find("p")
        desc = p.get_text(strip=True) if p else ""
        t = art.find("time")
        pub = ""
        if t and t.get("datetime"):
            try:
                dt = datetime.fromisoformat(t["datetime"].replace("Z", "+00:00"))
                pub = format_datetime(dt)
            except ValueError:
                pass
        items.append({"title": title, "link": link, "description": desc, "pubDate": pub})
        if len(items) >= MAX_ITEMS:
            break

    if not items:
        for h in soup.find_all(["h2", "h3"]):
            a = h.find("a", href=True)
            if not a:
                continue
            link = urljoin(url, a["href"])
            if link in seen or urlparse(link).netloc != urlparse(url).netloc:
                continue
            seen.add(link)
            title = h.get_text(strip=True)
            if len(title) < 15:
                continue
            items.append({"title": title, "link": link, "description": "", "pubDate": ""})
            if len(items) >= MAX_ITEMS:
                break

    if not items:
        raise RuntimeError("No se detectaron entradas (¿contenido cargado con JavaScript?).")
    return {"title": feed_title, "link": url,
            "description": f"Feed generado desde {url}", "items": items}


# ---------------- RSS ----------------
def build_rss(feed):
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0">',
        "<channel>",
        f"<title>{escape(feed['title'])}</title>",
        f"<link>{escape(feed['link'])}</link>",
        f"<description>{escape(feed['description'])}</description>",
        f"<lastBuildDate>{now_rfc822()}</lastBuildDate>",
        "<generator>generar_feeds.py</generator>",
    ]
    for it in feed["items"]:
        parts.append("<item>")
        parts.append(f"<title>{escape(it['title'])}</title>")
        parts.append(f"<link>{escape(it['link'])}</link>")
        parts.append(f'<guid isPermaLink="true">{escape(it["link"])}</guid>')
        if it["description"]:
            parts.append(f"<description><![CDATA[{it['description']}]]></description>")
        parts.append(f"<pubDate>{it['pubDate'] or now_rfc822()}</pubDate>")
        parts.append("</item>")
    parts += ["</channel>", "</rss>"]
    return "\n".join(parts)


# ---------------- principal ----------------
def main():
    if not os.path.exists(FUENTES):
        log(f"No existe {FUENTES}. Crea el archivo con una URL por línea.")
        sys.exit(1)

    os.makedirs(CARPETA_SALIDA, exist_ok=True)

    with open(FUENTES, encoding="utf-8") as f:
        urls = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]

    errores = 0
    for url in urls:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        log(f"Procesando: {url}")
        try:
            host = urlparse(url).netloc.lower()
            if "instagram.com" in host:
                url_real = instagram_to_imginn(url)
                log(f"  Instagram → {url_real}")
                feed = extract_imginn(url_real)
            elif "imginn.com" in host:
                feed = extract_imginn(url)
            else:
                feed = extract_generic(url)

            nombre = slug(url) + ".xml"
            ruta = os.path.join(CARPETA_SALIDA, nombre)
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(build_rss(feed))
            log(f"  ✔ {len(feed['items'])} entradas → {ruta}")
        except Exception as e:
            errores += 1
            log(f"  ✖ Error: {e}")

    log(f"Terminado. {len(urls) - errores}/{len(urls)} feeds generados.")
    # No fallar el workflow si alguna fuente puntual da error:
    sys.exit(0)


if __name__ == "__main__":
    main()
