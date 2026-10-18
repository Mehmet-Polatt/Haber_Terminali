from typing import List, Dict, Any
import httpx
import feedparser
from .utils import clean_html_text, extract_image_url

WEBRAZZI_RSS_URL = "https://webrazzi.com/feed/"


async def fetch_webrazzi(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Asynchronously fetches the latest Turkish technology & startup news from Webrazzi RSS feed.
    """
    results: List[Dict[str, Any]] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    async with httpx.AsyncClient(verify=False, timeout=30.0, headers=headers, follow_redirects=True) as client:
        try:
            response = await client.get(WEBRAZZI_RSS_URL)
            if response.status_code == 200:
                feed = feedparser.parse(response.text)
                
                for entry in feed.entries[:limit * 2]:
                    if len(results) >= limit:
                        break
                        
                    raw_title = entry.get("title", "")
                    link = entry.get("link", "")
                    raw_summary = entry.get("summary", "") or entry.get("description", "")
                    
                    clean_title = clean_html_text(raw_title)
                    clean_summary = clean_html_text(raw_summary)
                    
                    if len(clean_summary) > 250:
                        clean_summary = clean_summary[:247] + "..."
                        
                    if clean_title and link:
                        if not any(r["original_url"] == link for r in results):
                            results.append({
                                "title": clean_title,
                                "source": "Webrazzi",
                                "original_url": link,
                                "image_url": extract_image_url(entry),
                                "summary": clean_summary or clean_title,
                                "core_concept": "Girişimcilik & Teknoloji",
                            })
        except Exception as e:
            print(f"[Error][Webrazzi] Failed to fetch RSS feed: {e}")
            
    return results[:limit]
