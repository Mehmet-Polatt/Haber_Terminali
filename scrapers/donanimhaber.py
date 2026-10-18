from typing import List, Dict, Any
import httpx
import feedparser
from .utils import clean_html_text, extract_image_url

DONANIMHABER_RSS_URLS = [
    "https://www.donanimhaber.com/rss/tum/",
    "https://www.donanimhaber.com/rss/teknoloji-haberleri/",
]

TECH_KEYWORDS = [
    "yazılım", "donanım", "işlemci", "ekran kartı", "yapay zeka", "ai", "nvidia", 
    "amd", "intel", "apple", "google", "microsoft", "samsung", "python", "linux", 
    "android", "ios", "gpu", "cpu", "chip", "çip", "ram", "ssd", "geliştirici", 
    "teknoloji", "siber", "güvenlik", "kod", "open-source", "açık kaynak"
]


async def fetch_donanimhaber(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Asynchronously fetches RSS feed from DonanımHaber, filters technical items,
    and returns clean HTML-stripped text summaries.
    """
    results: List[Dict[str, Any]] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    async with httpx.AsyncClient(verify=False, timeout=30.0, headers=headers, follow_redirects=True) as client:
        for url in DONANIMHABER_RSS_URLS:
            try:
                response = await client.get(url)
                if response.status_code != 200:
                    continue
                
                feed = feedparser.parse(response.text)
                
                for entry in feed.entries:
                    raw_title = entry.get("title", "")
                    link = entry.get("link", "")
                    raw_summary = entry.get("summary", "") or entry.get("description", "")
                    
                    clean_title = clean_html_text(raw_title)
                    clean_summary = clean_html_text(raw_summary)
                    
                    title_lower = clean_title.lower()
                    summary_lower = clean_summary.lower()
                    
                    is_technical = any(kw in title_lower or kw in summary_lower for kw in TECH_KEYWORDS)
                    
                    if is_technical or not TECH_KEYWORDS:
                        if not any(r["original_url"] == link for r in results):
                            if len(clean_summary) > 250:
                                clean_summary = clean_summary[:247] + "..."

                            results.append({
                                "title": clean_title,
                                "source": "DonanımHaber",
                                "original_url": link,
                                "image_url": extract_image_url(entry),
                                "summary": clean_summary or clean_title,
                                "core_concept": "Donanım & Teknoloji",
                            })
                            
                    if len(results) >= limit:
                        break
                        
            except Exception as e:
                print(f"[Error][DonanimHaber] Failed to fetch RSS feed {url}: {e}")
                
            if len(results) >= limit:
                break
                
    return results[:limit]
