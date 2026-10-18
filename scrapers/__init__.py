from .donanimhaber import fetch_donanimhaber
from .webrazzi import fetch_webrazzi
from .aa_teknoloji import fetch_aa_teknoloji
from .sondakika import scrape_sondakika_politika, scrape_sondakika_teknoloji

__all__ = [
    "fetch_donanimhaber",
    "fetch_webrazzi",
    "fetch_aa_teknoloji",
    "scrape_sondakika_politika",
    "scrape_sondakika_teknoloji",
]
