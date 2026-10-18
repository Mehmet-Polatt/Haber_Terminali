import asyncio
import logging
import re
from typing import List, Dict, Any
import httpx
import feedparser
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


from scrapers.utils import clean_html_text, extract_image_url

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


async def scrape_bbc_turkce(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Scrapes political news from BBC News Türkçe -> Türkiye category page (https://www.bbc.com/turkce/turkiye).
    Source name is set to 'BBC Türkiye'.
    """
    urls = [
        "https://www.bbc.com/turkce/turkiye",
        "https://www.bbc.com/turkce/topics/c83q9vz8v2wt"
    ]
    items = []
    seen_urls = set()

    try:
        async with httpx.AsyncClient(verify=False, headers=HEADERS, follow_redirects=True, timeout=30.0) as client:
            for url in urls:
                if len(items) >= limit:
                    break
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        continue
                    soup = BeautifulSoup(resp.text, "html.parser")

                    anchors = soup.select('a[href*="/turkce/articles/"]') or soup.select('a[href*="/articles/"]')
                    for a in anchors:
                        if len(items) >= limit:
                            break
                        href = a.get("href", "").strip()
                        if not href:
                            continue
                        if not href.startswith("http"):
                            href = "https://www.bbc.com" + href

                        clean_url = href.split("?")[0]
                        if clean_url in seen_urls:
                            continue

                        raw_title = a.get_text(strip=True)
                        clean_title = clean_html_text(raw_title)

                        if clean_title and len(clean_title) > 15:
                            parent = a.find_parent(["li", "div", "article"])
                            summary_text = ""
                            if parent:
                                p_tag = parent.find("p")
                                if p_tag:
                                    summary_text = clean_html_text(p_tag.get_text(strip=True))

                            clean_sum = summary_text or clean_title

                            seen_urls.add(clean_url)
                            items.append({
                                "title": clean_title,
                                "source": "BBC Türkiye",
                                "original_url": clean_url,
                                "image_url": None,
                                "summary": clean_sum
                            })
                except Exception as ex:
                    logger.warning(f"Error fetching BBC Türkiye from {url}: {ex}")

            # Fallback to RSS with Türkiye/Siyaset filtering if HTML scraping returned fewer items than requested
            if len(items) < limit:
                try:
                    rss_resp = await client.get("https://feeds.bbci.co.uk/turkce/rss.xml")
                    feed = feedparser.parse(rss_resp.content)
                    for entry in feed.entries:
                        if len(items) >= limit:
                            break
                        link = getattr(entry, "link", "").strip().split("?")[0]
                        if not link or link in seen_urls:
                            continue

                        raw_title = getattr(entry, "title", "").strip()
                        raw_summary = getattr(entry, "summary", "").strip()
                        tags = [t.get("term", "").lower() for t in getattr(entry, "tags", []) if isinstance(t, dict)]

                        clean_title = clean_html_text(raw_title)
                        clean_sum = clean_html_text(raw_summary) or clean_title

                        is_turkey = any(k in t for t in tags for k in ["türkiye", "turkey", "siyaset"]) or \
                                    any(k in clean_title.lower() for k in ["türkiye", "tbmm", "akp", "chp", "mhp", "bakan", "parti", "ankara", "seçim", "hükümet"])

                        if is_turkey and clean_title:
                            seen_urls.add(link)
                            items.append({
                                "title": clean_title,
                                "source": "BBC Türkiye",
                                "original_url": link,
                                "image_url": None,
                                "summary": clean_sum
                            })
                except Exception as ex_rss:
                    logger.warning(f"Error filtering BBC RSS fallback: {ex_rss}")

    except Exception as e:
        logger.error(f"Error scraping BBC Türkiye: {e}", exc_info=True)

    return items



async def scrape_t24(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Scrapes political news from T24 Politika section.
    """
    url = "https://t24.com.tr/politika"
    items = []
    seen_urls = set()
    try:
        async with httpx.AsyncClient(verify=False, headers=HEADERS, follow_redirects=True, timeout=30.0) as client:
            resp = await client.get(url)
            soup = BeautifulSoup(resp.text, "html.parser")

            anchors = soup.select('a[href*="/politika/"]') or soup.select('a[href*="/haber/"]')
            for a in anchors:
                if len(items) >= limit:
                    break
                raw_title = a.get_text(strip=True)
                href = a.get("href", "").strip()
                if not href:
                    continue
                if not href.startswith("http"):
                    href = "https://t24.com.tr" + href

                clean_title = clean_html_text(raw_title)
                if clean_title and len(clean_title) > 12 and href not in seen_urls:
                    seen_urls.add(href)
                    items.append({
                        "title": clean_title,
                        "source": "T24",
                        "original_url": href,
                        "image_url": None,
                        "summary": clean_title
                    })
    except Exception as e:
        logger.error(f"Error scraping T24: {e}", exc_info=True)
    return items


async def scrape_sabah(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Scrapes political/gündem news from Sabah Gazetesi RSS feeds.
    """
    urls = [
        "https://www.sabah.com.tr/rss/gundem.xml",
        "https://www.sabah.com.tr/rss/siyaset.xml"
    ]
    items = []
    seen_urls = set()
    try:
        async with httpx.AsyncClient(verify=False, headers=HEADERS, follow_redirects=True, timeout=30.0) as client:
            for url in urls:
                if len(items) >= limit:
                    break
                try:
                    resp = await client.get(url)
                    feed = feedparser.parse(resp.content)
                    for entry in feed.entries:
                        if len(items) >= limit:
                            break
                        raw_title = getattr(entry, "title", "").strip()
                        raw_summary = getattr(entry, "summary", "").strip()
                        link = getattr(entry, "link", "").strip()

                        clean_title = clean_html_text(raw_title)
                        clean_sum = clean_html_text(raw_summary) or clean_title

                        if clean_title and link and link not in seen_urls:
                            seen_urls.add(link)
                            items.append({
                                "title": clean_title,
                                "source": "Sabah",
                                "original_url": link,
                                "image_url": extract_image_url(entry),
                                "summary": clean_sum
                            })
                except Exception as ex:
                    logger.warning(f"Failed fetching Sabah RSS {url}: {ex}")
    except Exception as e:
        logger.error(f"Error scraping Sabah: {e}", exc_info=True)
    return items


async def scrape_sozcu(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Scrapes political/gündem news from Sözcü Gazetesi RSS feeds.
    """
    urls = [
        "https://www.sozcu.com.tr/rss/siyaset.xml",
        "https://www.sozcu.com.tr/rss/gundem.xml"
    ]
    items = []
    seen_urls = set()
    try:
        async with httpx.AsyncClient(verify=False, headers=HEADERS, follow_redirects=True, timeout=30.0) as client:
            for url in urls:
                if len(items) >= limit:
                    break
                try:
                    resp = await client.get(url)
                    feed = feedparser.parse(resp.content)
                    for entry in feed.entries:
                        if len(items) >= limit:
                            break
                        raw_title = getattr(entry, "title", "").strip()
                        raw_summary = getattr(entry, "summary", "").strip()
                        link = getattr(entry, "link", "").strip()

                        clean_title = clean_html_text(raw_title)
                        clean_sum = clean_html_text(raw_summary) or clean_title

                        if clean_title and link and link not in seen_urls:
                            seen_urls.add(link)
                            items.append({
                                "title": clean_title,
                                "source": "Sözcü",
                                "original_url": link,
                                "image_url": extract_image_url(entry),
                                "summary": clean_sum
                            })
                except Exception as ex:
                    logger.warning(f"Failed fetching Sözcü RSS {url}: {ex}")
    except Exception as e:
        logger.error(f"Error scraping Sözcü: {e}", exc_info=True)
    return items


async def scrape_gazete_oksijen(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Scrapes news from Gazete Oksijen website.
    """
    url = "https://gazeteoksijen.com"
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

                if not href or href.startswith("javascript"):
                    continue
                if not href.startswith("http"):
                    href = "https://gazeteoksijen.com" + href

                clean_title = clean_html_text(raw_title)
                if clean_title and len(clean_title) > 18 and re.search(r'-\d+$', href) and href not in seen_urls:
                    seen_urls.add(href)
                    items.append({
                        "title": clean_title,
                        "source": "Gazete Oksijen",
                        "original_url": href,
                        "image_url": None,
                        "summary": clean_title
                    })
    except Exception as e:
        logger.error(f"Error scraping Gazete Oksijen: {e}", exc_info=True)
    return items


async def scrape_tbmm_news(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Scrapes legislative news directly from TBMM's official news page (https://www.tbmm.gov.tr/meclis-haber/yasama).
    Uses Playwright to render JavaScript content and BeautifulSoup to parse news cards.
    """
    url = "https://www.tbmm.gov.tr/meclis-haber/yasama"
    items = []
    seen_urls = set()

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle")
            await page.wait_for_timeout(3000)

            html = await page.content()
            await browser.close()

            soup = BeautifulSoup(html, "html.parser")
            anchors = [
                a for a in soup.find_all("a", href=True)
                if "/Haber/Detay" in a["href"] or "/haber/detay" in a["href"].lower()
            ]

            for a in anchors:
                if len(items) >= limit:
                    break

                href = a["href"].strip()
                if not href.startswith("http"):
                    href = "https://www.tbmm.gov.tr" + href

                if href in seen_urls:
                    continue
                seen_urls.add(href)

                title_el = a.find("div", class_="arb") or a.find(["h1", "h2", "h3", "h4", "strong", "b"])
                raw_title = title_el.get_text(strip=True) if title_el else a.get_text(strip=True)

                summary_el = a.find("div", class_="ard") or a.find("p")
                raw_summary = summary_el.get_text(strip=True) if summary_el else raw_title

                title = " ".join(raw_title.split())
                summary = " ".join(raw_summary.split())

                img_el = a.find("img")
                img_url = None
                if img_el:
                    img_url = img_el.get("src") or img_el.get("data-src")
                    if img_url and not img_url.startswith("http"):
                        img_url = "https://www.tbmm.gov.tr" + img_url

                if title and len(title) > 10:
                    items.append({
                        "title": title,
                        "summary": summary or title,
                        "source": "TBMM",
                        "original_url": href,
                        "image_url": img_url
                    })

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error scraping TBMM news with Playwright: {e}")

    return items


async def scrape_sondakika_politika_local(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Scrapes political news from Sondakika Politika (https://www.sondakika.com/politika/).
    """
    from scrapers.sondakika import scrape_sondakika_politika
    return await scrape_sondakika_politika(limit=limit)


async def fetch_all_politics_news(limit_per_source: int = 5) -> Dict[str, List[Dict[str, Any]]]:
    """
    Executes all political news scrapers concurrently using asyncio.gather.
    Returns a dictionary mapping source keys to lists of news items.
    """
    bbc_task = scrape_bbc_turkce(limit=limit_per_source)
    t24_task = scrape_t24(limit=limit_per_source)
    sabah_task = scrape_sabah(limit=limit_per_source)
    sozcu_task = scrape_sozcu(limit=limit_per_source)
    oksijen_task = scrape_gazete_oksijen(limit=limit_per_source)
    tbmm_task = scrape_tbmm_news(limit=limit_per_source)
    sondakika_task = scrape_sondakika_politika_local(limit=limit_per_source)

    bbc_res, t24_res, sabah_res, sozcu_res, oksijen_res, tbmm_res, sondakika_res = await asyncio.gather(
        bbc_task, t24_task, sabah_task, sozcu_task, oksijen_task, tbmm_task, sondakika_task,
        return_exceptions=True
    )

    return {
        "bbc_turkce": bbc_res if isinstance(bbc_res, list) else [],
        "t24": t24_res if isinstance(t24_res, list) else [],
        "sabah": sabah_res if isinstance(sabah_res, list) else [],
        "sozcu": sozcu_res if isinstance(sozcu_res, list) else [],
        "gazete_oksijen": oksijen_res if isinstance(oksijen_res, list) else [],
        "tbmm_gundemi": tbmm_res if isinstance(tbmm_res, list) else [],
        "sondakika_politika": sondakika_res if isinstance(sondakika_res, list) else [],
    }

