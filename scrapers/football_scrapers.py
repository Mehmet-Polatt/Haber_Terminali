import asyncio
import logging
import re
from typing import List, Dict, Any
import httpx
import feedparser
from bs4 import BeautifulSoup

from scrapers.utils import clean_html_text, extract_image_url

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

FOOTBALL_KEYWORDS = [
    "futbol", "fenerbahçe", "galatasaray", "beşiktaş", "trabzonspor", 
    "milli takım", "tff", "transfer", "süper lig", "uefa", "şampiyonlar ligi", 
    "maç", "kulüp", "skor", "arda güler", "mbappe", "montella", "zidane", 
    "forma", "penaltı", "gol", "teknik direktör", "hakem", "derbi"
]

STANDINGS_KEYWORDS = [
    "puan", "fikstür", "canlı sonuç", "hangi kanalda", "saat kaçta", "maç programı", "canlı yayın"
]


def _clean_and_sanitize(text: str) -> str:
    cleaned = clean_html_text(text)
    return cleaned.replace("\ufffd", "").strip()


async def scrape_gzt_spor(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Scrapes football news from GZT Zpor (https://www.gzt.com/zpor).
    Filters out standings tables, match schedules, and non-article links.
    Source name is set to 'GZT Spor'.
    """
    url = "https://www.gzt.com/zpor"
    items = []
    seen_urls = set()

    try:
        async with httpx.AsyncClient(verify=False, headers=HEADERS, follow_redirects=True, timeout=30.0) as client:
            resp = await client.get(url)
            soup = BeautifulSoup(resp.text, "html.parser")

            anchors = soup.find_all("a", href=True)
            for a in anchors:
                if len(items) >= limit:
                    break
                href = a.get("href", "").strip()
                raw_title = a.get_text(strip=True)

                if not href or href.startswith("javascript") or href == "#":
                    continue

                # Exclude standings, team rosters, and photo gallery navigation links
                if any(p in href.lower() for p in ["/takim/", "/puandurumu", "/fikstur", "/canli-yayin", "/foto-galeri", "/resmi-ilanlar"]):
                    continue

                if not href.startswith("http"):
                    href = "https://www.gzt.com" + href

                clean_url = href.split("?")[0]
                clean_title = _clean_and_sanitize(raw_title)

                if not clean_title or len(clean_title) <= 20 or clean_url in seen_urls:
                    continue

                title_lower = clean_title.lower()

                # Filter out titles with standings table structures, point lists, or schedule headers
                if (
                    any(k in title_lower for k in STANDINGS_KEYWORDS)
                    or re.search(r"^\d+şl", title_lower)
                    or re.search(r"\d+puan", title_lower)
                ):
                    continue

                seen_urls.add(clean_url)
                items.append({
                    "title": clean_title,
                    "source": "GZT Spor",
                    "original_url": clean_url,
                    "image_url": None,
                    "summary": clean_title
                })
    except Exception as e:
        logger.error(f"Error scraping GZT Spor: {e}", exc_info=True)
    return items


async def scrape_sporx_futbol(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Scrapes football news from Sporx Futbol section (https://www.sporx.com/futbol).
    Enforces Turkish encoding ('windows-1254') to prevent replacement character corruption.
    Source name is set to 'Sporx Futbol'.
    """
    url = "https://www.sporx.com/futbol"
    items = []
    seen_urls = set()

    try:
        async with httpx.AsyncClient(verify=False, headers=HEADERS, follow_redirects=True, timeout=30.0) as client:
            resp = await client.get(url)
            
            # Explicit Turkish encoding handling for Sporx
            try:
                content_text = resp.content.decode("windows-1254")
            except Exception:
                try:
                    content_text = resp.content.decode("iso-8859-9", errors="replace")
                except Exception:
                    resp.encoding = "utf-8"
                    content_text = resp.text

            soup = BeautifulSoup(content_text, "html.parser")

            anchors = soup.find_all("a", href=True)
            for a in anchors:
                if len(items) >= limit:
                    break
                href = a.get("href", "").strip()
                raw_title = a.get_text(strip=True)

                if not href or not ("SXHB" in href or "/futbol/" in href):
                    continue
                if not href.startswith("http"):
                    href = "https://www.sporx.com" + href

                clean_url = href.split("?")[0]
                clean_title = _clean_and_sanitize(raw_title)

                # Ignore titles corrupted by replacement characters or standings headers
                if not clean_title or len(clean_title) <= 18 or clean_url in seen_urls:
                    continue

                title_lower = clean_title.lower()
                if any(k in title_lower for k in ["puan durumu", "fikstür", "maç programı"]) or re.search(r"^\d+şl", title_lower):
                    continue

                seen_urls.add(clean_url)
                items.append({
                    "title": clean_title,
                    "source": "Sporx Futbol",
                    "original_url": clean_url,
                    "image_url": None,
                    "summary": clean_title
                })
    except Exception as e:
        logger.error(f"Error scraping Sporx Futbol: {e}", exc_info=True)
    return items


async def scrape_dha_spor(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Scrapes sports news from DHA (https://www.dha.com.tr/spor) filtered specifically for football content.
    Source name is set to 'DHA Spor'.
    """
    url = "https://www.dha.com.tr/spor"
    items = []
    seen_urls = set()

    try:
        async with httpx.AsyncClient(verify=False, headers=HEADERS, follow_redirects=True, timeout=30.0) as client:
            resp = await client.get(url)
            soup = BeautifulSoup(resp.text, "html.parser")

            anchors = soup.find_all("a", href=True)
            for a in anchors:
                if len(items) >= limit:
                    break
                href = a.get("href", "").strip()
                raw_title = a.get_text(strip=True)

                if not href or "/spor/" not in href or href.endswith("booking.dha.com.tr"):
                    continue
                if not href.startswith("http"):
                    href = "https://www.dha.com.tr" + href

                clean_url = href.split("?")[0]
                clean_title = _clean_and_sanitize(raw_title)

                if (
                    clean_title
                    and len(clean_title) > 18
                    and clean_url not in seen_urls
                    and any(k in clean_title.lower() for k in FOOTBALL_KEYWORDS)
                ):
                    seen_urls.add(clean_url)
                    items.append({
                        "title": clean_title,
                        "source": "DHA Spor",
                        "original_url": clean_url,
                        "image_url": None,
                        "summary": clean_title
                    })
    except Exception as e:
        logger.error(f"Error scraping DHA Spor: {e}", exc_info=True)
    return items


async def scrape_transfer_radar(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Scrapes transfer news & rumors from football RSS feeds / Transfer Radar.
    Source name is set to 'Transfer Radar'.
    """
    rss_urls = [
        "https://www.fotomac.com.tr/rss/transfer.xml",
        "https://www.fotomac.com.tr/rss/futbol.xml"
    ]
    items = []
    seen_urls = set()

    try:
        async with httpx.AsyncClient(verify=False, headers=HEADERS, follow_redirects=True, timeout=30.0) as client:
            for url in rss_urls:
                if len(items) >= limit:
                    break
                try:
                    resp = await client.get(url)
                    feed = feedparser.parse(resp.content)

                    for entry in feed.entries:
                        if len(items) >= limit:
                            break
                        link = getattr(entry, "link", "").strip()
                        raw_title = getattr(entry, "title", "").strip()
                        raw_summary = getattr(entry, "summary", "").strip()

                        clean_url = link.split("?")[0]
                        clean_title = _clean_and_sanitize(raw_title)
                        clean_sum = _clean_and_sanitize(raw_summary) or clean_title

                        if clean_title and clean_url and clean_url not in seen_urls:
                            seen_urls.add(clean_url)
                            items.append({
                                "title": clean_title,
                                "source": "Transfer Radar",
                                "original_url": clean_url,
                                "image_url": extract_image_url(entry),
                                "summary": clean_sum
                            })
                except Exception as ex:
                    logger.warning(f"Error fetching Transfer Radar RSS {url}: {ex}")
    except Exception as e:
        logger.error(f"Error scraping Transfer Radar: {e}", exc_info=True)
    return items


async def scrape_ntv_spor(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Scrapes football news from NTV Spor (https://www.ntvspor.net/futbol).
    """
    url = "https://www.ntvspor.net/futbol"
    items = []
    seen_urls = set()

    try:
        async with httpx.AsyncClient(verify=False, headers=HEADERS, follow_redirects=True, timeout=30.0) as client:
            resp = await client.get(url)
            soup = BeautifulSoup(resp.text, "html.parser")

            # NTV Spor article cards
            article_cards = soup.find_all(["article", "div"], class_=re.compile(r"card|news|article|item", re.I))
            seen_titles = set()

            for card in article_cards:
                if len(items) >= limit:
                    break
                a = card.find("a", href=True)
                if not a:
                    continue

                href = a.get("href", "").strip()
                if not href:
                    continue
                if not href.startswith("http"):
                    href = "https://www.ntvspor.net" + href

                if "/futbol/" not in href and "ntvspor.net" not in href:
                    continue

                clean_url = href.split("?")[0]
                if clean_url in seen_urls:
                    continue

                # Get title from heading or link text
                h_tag = card.find(["h1", "h2", "h3", "h4"])
                raw_title = h_tag.get_text(strip=True) if h_tag else a.get_text(strip=True)
                clean_title = _clean_and_sanitize(raw_title)

                if not clean_title or len(clean_title) <= 15 or clean_title in seen_titles:
                    continue

                # Try to get image
                img = card.find("img")
                image_url = None
                if img:
                    image_url = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
                    if image_url and not image_url.startswith("http"):
                        image_url = "https://www.ntvspor.net" + image_url

                # Get summary
                p = card.find("p")
                summary = _clean_and_sanitize(p.get_text(strip=True)) if p else clean_title

                seen_urls.add(clean_url)
                seen_titles.add(clean_title)
                items.append({
                    "title": clean_title,
                    "source": "NTV Spor",
                    "original_url": clean_url,
                    "image_url": image_url,
                    "summary": summary or clean_title
                })

            # Fallback: plain anchor scraping if card approach found nothing
            if not items:
                for a in soup.find_all("a", href=True):
                    if len(items) >= limit:
                        break
                    href = a.get("href", "").strip()
                    if "/futbol/" not in href:
                        continue
                    if not href.startswith("http"):
                        href = "https://www.ntvspor.net" + href
                    clean_url = href.split("?")[0]
                    if clean_url in seen_urls:
                        continue
                    clean_title = _clean_and_sanitize(a.get_text(strip=True))
                    if not clean_title or len(clean_title) <= 15:
                        continue
                    seen_urls.add(clean_url)
                    items.append({
                        "title": clean_title,
                        "source": "NTV Spor",
                        "original_url": clean_url,
                        "image_url": None,
                        "summary": clean_title
                    })

    except Exception as e:
        logger.error(f"Error scraping NTV Spor: {e}", exc_info=True)
    return items[:limit]


async def scrape_futboo(limit: int = 5) -> List[Dict[str, Any]]:
    """Scrapes football news from Futboo's homepage."""
    return await _scrape_football_section(
        "https://www.futboo.com/", "www.futboo.com", "Futboo", limit,
        ("/haber/", "/futbol/", "/transfer/")
    )


async def scrape_fanatik_futbol(limit: int = 5) -> List[Dict[str, Any]]:
    """Scrapes football news from Fanatik's football section."""
    return await _scrape_football_section(
        "https://www.fanatik.com.tr/futbol/", "www.fanatik.com.tr", "Fanatik", limit,
        ("/futbol/",)
    )


async def _scrape_football_section(url: str, domain: str, source: str, limit: int,
                                   path_markers: tuple[str, ...]) -> List[Dict[str, Any]]:
    items = []
    seen_urls = set()
    try:
        async with httpx.AsyncClient(verify=False, headers=HEADERS, follow_redirects=True, timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            for anchor in soup.find_all("a", href=True):
                href = anchor["href"].strip()
                if not href or href.startswith(("#", "javascript:")):
                    continue
                if href.startswith("/"):
                    href = f"https://{domain}{href}"
                if not href.startswith(f"https://{domain}/"):
                    continue
                clean_url = href.split("?")[0].rstrip("/")
                if not any(marker in clean_url.lower() for marker in path_markers):
                    continue
                title = _clean_and_sanitize(anchor.get_text(" ", strip=True))
                if len(title) < 20 or clean_url in seen_urls:
                    continue
                seen_urls.add(clean_url)
                items.append({
                    "title": title,
                    "source": source,
                    "original_url": clean_url,
                    "image_url": None,
                    "summary": title,
                })
                if len(items) >= limit:
                    break
    except Exception as e:
        logger.error(f"Error scraping {source}: {e}", exc_info=True)
    return items


async def fetch_all_football_news(limit_per_source: int = 5) -> Dict[str, List[Dict[str, Any]]]:
    """
    Executes all football news scrapers concurrently using asyncio.gather.
    Returns a dictionary mapping source keys to lists of news items.
    """
    gzt_task = scrape_gzt_spor(limit=limit_per_source)
    sporx_task = scrape_sporx_futbol(limit=limit_per_source)
    dha_task = scrape_dha_spor(limit=limit_per_source)
    radar_task = scrape_transfer_radar(limit=limit_per_source)
    ntv_task = scrape_ntv_spor(limit=limit_per_source)
    futboo_task = scrape_futboo(limit=limit_per_source)
    fanatik_task = scrape_fanatik_futbol(limit=limit_per_source)

    gzt_res, sporx_res, dha_res, radar_res, ntv_res, futboo_res, fanatik_res = await asyncio.gather(
        gzt_task, sporx_task, dha_task, radar_task, ntv_task, futboo_task, fanatik_task,
        return_exceptions=True
    )

    return {
        "gzt_spor": gzt_res if isinstance(gzt_res, list) else [],
        "sporx_futbol": sporx_res if isinstance(sporx_res, list) else [],
        "dha_spor": dha_res if isinstance(dha_res, list) else [],
        "transfer_radar": radar_res if isinstance(radar_res, list) else [],
        "ntv_spor": ntv_res if isinstance(ntv_res, list) else [],
        "futboo": futboo_res if isinstance(futboo_res, list) else [],
        "fanatik_futbol": fanatik_res if isinstance(fanatik_res, list) else [],
    }
