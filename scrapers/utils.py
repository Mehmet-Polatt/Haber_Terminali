from bs4 import BeautifulSoup
import re


def clean_html_text(raw_html: str) -> str:
    """
    Strips HTML tags, scripts, style blocks, and normalizes spaces from a string.
    """
    if not raw_html or not raw_html.strip():
        return ""
    
    # Fast regex cleanup for common HTML patterns
    soup = BeautifulSoup(raw_html, "html.parser")
    for element in soup(["script", "style", "head", "title", "meta", "[document]"]):
        element.extract()
        
    text = soup.get_text(separator=" ")
    # Replace multiple whitespaces and newlines with a single space
    clean_text = re.sub(r'\s+', ' ', text).strip()
    return clean_text


async def get_translated_preview(url: str, raw_title: str) -> dict:
    """
    Legacy helper function maintained for backward compatibility.
    Strips HTML from raw title and summary without deep-translator overhead.
    """
    clean_title = clean_html_text(raw_title)
    return {
        "tr_title": clean_title or raw_title,
        "tr_summary": clean_title or raw_title
    }


def extract_image_url(entry: dict) -> str | None:
    """Extracts an image URL from an RSS feedparser entry."""
    # Check media_content
    if 'media_content' in entry and len(entry['media_content']) > 0:
        return entry['media_content'][0].get('url')
    
    # Check links for enclosures
    if 'links' in entry:
        for link in entry['links']:
            if link.get('rel') == 'enclosure' and 'image' in link.get('type', ''):
                return link.get('href')
    
    # Try to extract from raw summary using regex if needed (basic extraction)
    raw_summary = entry.get('summary', '') or entry.get('description', '')
    img_match = re.search(r'<img[^>]+src=["\'](.*?)["\']', raw_summary, re.IGNORECASE)
    if img_match:
        return img_match.group(1)
        
    return None
