import asyncio
from typing import List, Dict, Any
from .donanimhaber import fetch_donanimhaber
from .webrazzi import fetch_webrazzi
from .aa_teknoloji import fetch_aa_teknoloji
from .sondakika import scrape_sondakika_teknoloji


async def fetch_all_tech_news(limit_per_source: int = 5) -> Dict[str, List[Dict[str, Any]]]:
    """
    Executes all Turkish tech news scrapers concurrently using asyncio.gather.
    Returns a dictionary mapping source keys to lists of news items.
    """
    dh_task = fetch_donanimhaber(limit=limit_per_source)
    webrazzi_task = fetch_webrazzi(limit=limit_per_source)
    aa_task = fetch_aa_teknoloji(limit=limit_per_source)
    sondakika_task = scrape_sondakika_teknoloji(limit=limit_per_source)

    dh_results, webrazzi_results, aa_results, sondakika_results = await asyncio.gather(
        dh_task, webrazzi_task, aa_task, sondakika_task, return_exceptions=True
    )

    return {
        "donanimhaber": dh_results if isinstance(dh_results, list) else [],
        "webrazzi": webrazzi_results if isinstance(webrazzi_results, list) else [],
        "anadolu_ajansi": aa_results if isinstance(aa_results, list) else [],
        "sondakika_teknoloji": sondakika_results if isinstance(sondakika_results, list) else [],
    }
