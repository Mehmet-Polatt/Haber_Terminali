import logging
from typing import List, Dict, Any
import httpx
from bs4 import BeautifulSoup
from .utils import clean_html_text

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


async def scrape_sondakika_category(category: str, source_name: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Scrapes news from sondakika.com for a given category (e.g. 'politika' or 'teknoloji').
    """
    url = f"https://www.sondakika.com/{category}/"
    items: List[Dict[str, Any]] = []
    seen = set()

    try:
        async with httpx.AsyncClient(verify=False, headers=HEADERS, follow_redirects=True, timeout=30.0) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                logger.warning(f"SonDakika returned status {resp.status_code} for {url}")
                return items

            soup = BeautifulSoup(resp.text, "html.parser")
            for a in soup.find_all("a", href=True):
                if len(items) >= limit:
                    break
                href = a["href"].strip()
                if not href:
                    continue
                if not href.startswith("http"):
                    href = "https://www.sondakika.com" + href

                clean_url = href.split("?")[0]
                if clean_url in seen:
                    continue

                if not ("/haber-" in clean_url or f"/{category}/" in clean_url):
                    continue

                if any(x in clean_url for x in ["cerez", "kunye", "gizlilik", "iletisim", "foto-galeri"]):
                    continue

                h_tag = a.find(["h1", "h2", "h3", "h4", "span"])
                raw_title = h_tag.get_text(strip=True) if h_tag else a.get_text(strip=True)
                clean_title = clean_html_text(raw_title)

                if len(clean_title) < 15 or "tıklayınız" in clean_title.lower():
                    continue

                img = a.find("img")
                img_url = None
                if img:
                    img_url = img.get("src") or img.get("data-src") or img.get("data-original")
                    if img_url and not img_url.startswith("http"):
                        img_url = "https://www.sondakika.com" + img_url

                p_tag = a.find("p")
                summary = clean_html_text(p_tag.get_text(strip=True)) if p_tag else clean_title

                seen.add(clean_url)
                items.append({
                    "title": clean_title,
                    "source": source_name,
                    "original_url": clean_url,
                    "image_url": img_url,
                    "summary": summary or clean_title,
                })

    except Exception as e:
        logger.error(f"Error scraping SonDakika {category}: {e}", exc_info=True)

    return items[:limit]


async def scrape_sondakika_politika(limit: int = 5) -> List[Dict[str, Any]]:
    return await scrape_sondakika_category("politika", "SonDakika Politika", limit=limit)


async def scrape_sondakika_teknoloji(limit: int = 5) -> List[Dict[str, Any]]:
    return await scrape_sondakika_category("teknoloji", "SonDakika Teknoloji", limit=limit)
