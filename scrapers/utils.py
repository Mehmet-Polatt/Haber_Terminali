from bs4 import BeautifulSoup
import re
import httpx
import logging

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# ---------------------------------------------------------------------------
# Siyaset kategorisi için geçerlilik / alaka düzeyi filtresi
# ---------------------------------------------------------------------------

# Siyaset haberi olduğunu destekleyen anahtar kelimeler
_POLITICS_KEYWORDS = [
    "türkiye", "turkey", "siyaset", "siyasi", "tbmm", "meclis", "parlamento",
    "akp", "chp", "mhp", "hdp", "deva", "iyi parti", "gelecek partisi",
    "bakan", "bakanı", "bakanlık", "cumhurbaşkanı", "erdoğan", "başbakan",
    "hükümet", "muhalefet", "seçim", "oy", "koalisyon", "anayasa",
    "milletvekili", "parti", "ankara", "büyükşehir", "belediye başkanı",
    "ysk", "millet ittifakı", "cumhur ittifakı", "ekonomi bakanı",
    "savunma", "dışişleri", "içişleri", "kamu", "devlet", "yönetim",
    "referandum", "sandık", "ittifak", "muhtıra", "kabine",
]

# Siyasetle açıkça alakasız içeriklerin filtre kelimesi kalıpları
_NON_POLITICS_PATTERNS = [
    r'\bskor\b', r'\bgol\b', r'\bmaç\b', r'\bfutbol\b',
    r'\bchampions\b', r'\bliga\b', r'\btransfer\b',
    r'\bfilm\b', r'\bdizi\b', r'\bmüzik\b', r'\bkonser\b',
    r'\bteknoloji\b', r'\byapay zeka\b', r'\bai\b', r'\bbitcoin\b',
]

_NON_POLITICS_RE = re.compile(
    '|'.join(_NON_POLITICS_PATTERNS), re.IGNORECASE | re.UNICODE
)


def is_politics_relevant(
    title: str,
    summary: str = "",
    tags: list[str] | None = None
) -> bool:
    """
    Bir haberin siyaset kategorisine uygun olup olmadığını kontrol eder.
    Tüm siyaset kaynaklarında (BBC, T24, Sabah, Sözcü, vb.) ortak kullanılır.

    Kurallar:
    - Başlık veya özette en az bir siyaset anahtar kelimesi geçmeli.
    - Açıkça siyasetle alakasız (spor, eğlence, teknoloji) kelime varsa False döner.
    - RSS tag listesi varsa tag bazlı kontrolü de yapar.
    - Boş/çok kısa başlıklar (< 8 karakter) kabul edilmez.

    Returns:
        True  → haber siyaset kategorisine uygun
        False → haber siyaset kategorisine uygun değil
    """
    combined = f"{title} {summary}".lower()

    # Çok kısa içerikleri ele
    if len(title.strip()) < 8:
        return False

    # Açıkça siyasetle alakasız içerikler
    if _NON_POLITICS_RE.search(combined):
        return False

    # En az bir anahtar kelime eşleşmesi gerekli
    if any(kw in combined for kw in _POLITICS_KEYWORDS):
        return True

    # RSS tag tabanlı kontrol
    if tags:
        tags_combined = " ".join(tags).lower()
        if any(kw in tags_combined for kw in _POLITICS_KEYWORDS):
            return True

    return False


# ---------------------------------------------------------------------------
# Gelişmiş görsel çekme fonksiyonları
# ---------------------------------------------------------------------------

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
    img_match = re.search(r'<img[^>]+src=[\"\'](.+?)[\"\']', raw_summary, re.IGNORECASE)
    if img_match:
        return img_match.group(1)

    return None


def extract_image_from_html(html: str, base_url: str = "") -> str | None:
    """
    Verilen HTML içeriğinden en uygun görsel URL'sini çıkarır.

    Öncelik sırası:
    1. <meta property="og:image">          (Open Graph — en güvenilir)
    2. <meta name="twitter:image">         (Twitter Card)
    3. <link rel="image_src">              (eski standart)
    4. <meta itemprop="image">             (Schema.org)
    5. <figure> veya article içindeki ilk anlamlı <img>
    6. Sayfanın tamamındaki ilk anlamlı <img> (boyut filtresi ile)

    Args:
        html:     Sayfa HTML'i
        base_url: Göreli URL'leri mutlak URL'ye çevirmek için site kök adresi

    Returns:
        Görsel URL string veya None
    """
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # 1. og:image
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        return _make_absolute(og["content"].strip(), base_url)

    # 2. twitter:image
    tw = soup.find("meta", attrs={"name": "twitter:image"})
    if tw and tw.get("content"):
        return _make_absolute(tw["content"].strip(), base_url)

    # 3. link rel="image_src"
    link_img = soup.find("link", rel="image_src")
    if link_img and link_img.get("href"):
        return _make_absolute(link_img["href"].strip(), base_url)

    # 4. itemprop="image"
    itemprop = soup.find("meta", itemprop="image")
    if itemprop and itemprop.get("content"):
        return _make_absolute(itemprop["content"].strip(), base_url)

    # 5 & 6. İçerik alanındaki img etiketlerini tara
    # Önce article / figure / main / .content gibi anlamlı kaplar içinde ara
    content_containers = soup.select(
        "article, figure, main, .article-body, .news-body, "
        ".content, .post-content, .entry-content, #content"
    )

    candidates: list[str] = []
    search_scope = content_containers if content_containers else [soup]

    for container in search_scope:
        for img in container.find_all("img"):
            src = (
                img.get("src")
                or img.get("data-src")
                or img.get("data-lazy-src")
                or img.get("data-original")
            )
            if not src:
                continue
            # Küçük simge/ikon/tracker piksellerini atla
            if _is_likely_icon(src, img):
                continue
            candidates.append(_make_absolute(src.strip(), base_url))

    if candidates:
        return candidates[0]

    return None


async def fetch_article_image(article_url: str) -> str | None:
    """
    Verilen makale URL'sine HTTP isteği atarak sayfanın HTML'inden
    `extract_image_from_html` aracılığıyla görsel URL'si çeker.

    Yalnızca image_url=None durumunda fallback olarak kullanılmalı.

    Returns:
        Görsel URL string veya None
    """
    try:
        async with httpx.AsyncClient(
            verify=False,
            headers=HEADERS,
            follow_redirects=True,
            timeout=15.0
        ) as client:
            resp = await client.get(article_url)
            if resp.status_code != 200:
                return None
            base_url = f"{resp.url.scheme}://{resp.url.host}"
            return extract_image_from_html(resp.text, base_url=base_url)
    except Exception as e:
        logger.debug(f"[fetch_article_image] Görsel çekme başarısız ({article_url}): {e}")
        return None


# ---------------------------------------------------------------------------
# Yardımcı (özel) fonksiyonlar
# ---------------------------------------------------------------------------

def _make_absolute(url: str, base_url: str) -> str:
    """Göreli URL'yi mutlak URL'ye çevirir."""
    if not url:
        return url
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/") and base_url:
        return base_url.rstrip("/") + url
    return url


def _is_likely_icon(src: str, img_tag) -> bool:
    """
    Küçük simge/ikon/tracker piksellerini ve logo küçük resimlerini filtreler.
    True döndürürse bu görsel atlanmalı.
    """
    # URL bazlı: ortak ikon yolu kalıpları
    icon_patterns = [
        r'/icon', r'/logo', r'/sprite', r'/pixel', r'/tracking',
        r'/ads/', r'/banner', r'\.gif$', r'1x1', r'blank',
    ]
    for pat in icon_patterns:
        if re.search(pat, src, re.IGNORECASE):
            return True

    # Boyut bazlı: width/height attribute varsa küçük görselleri ele
    try:
        w = int(img_tag.get("width", 0) or 0)
        h = int(img_tag.get("height", 0) or 0)
        if (w and w < 80) or (h and h < 80):
            return True
    except (ValueError, TypeError):
        pass

    return False


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


def clean_html_text(raw_html: str) -> str:
    """
    Strips HTML tags, scripts, style blocks, and normalizes spaces from a string.
    """
    if not raw_html or not raw_html.strip():
        return ""

    soup = BeautifulSoup(raw_html, "html.parser")
    for element in soup(["script", "style", "head", "title", "meta", "[document]"]):
        element.extract()

    text = soup.get_text(separator=" ")
    clean_text = re.sub(r'\s+', ' ', text).strip()
    return clean_text
