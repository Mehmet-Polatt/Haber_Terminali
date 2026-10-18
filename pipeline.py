import json
import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from models import TechCard, PoliticsCard, FootballCard
from scrapers.runner import fetch_all_tech_news
from scrapers.politics_scrapers import fetch_all_politics_news
from scrapers.football_scrapers import fetch_all_football_news

logger = logging.getLogger(__name__)


def normalize_turkish(text: str) -> str:
    if not text: return ""
    # Önce tırnak ve gereksiz noktalama işaretlerini temizle
    text = text.replace('"', '').replace("'", '').replace('.', '')
    # Türkçe karakterleri doğru küçült
    text = text.replace("İ", "i").replace("I", "ı").replace("Ş", "ş").replace("Ç", "ç").replace("Ğ", "ğ").replace("Ö", "ö").replace("Ü", "ü")
    return text.lower().strip()


async def run_pipeline(db: AsyncSession, limit_per_source: int = 5) -> Dict[str, Any]:
    """
    Executes the fast, raw news collection pipeline (On-Demand Analysis Architecture):
    1. Scrapes news items from Hacker News, Lobste.rs, and DonanımHaber.
    2. Deduplicates against existing DB records by original_url or title.
    3. Saves raw news cards directly to the database with is_analyzed = False (No background Gemini API calls!).
    """
    print("[Pipeline] Haber tarayıcılar çalıştırılıyor...")
    scraped_data = await fetch_all_tech_news(limit_per_source=limit_per_source)
    
    total_scraped = 0
    skipped_duplicates = 0
    saved_count = 0
    failed_count = 0
    saved_cards: List[TechCard] = []
    
    all_items = []
    for source_key, items in scraped_data.items():
        for item in items:
            all_items.append((source_key, item))
            
    total_items = len(all_items)
    print(f"[Pipeline] Toplam {total_items} adet ham haber toplandı. Veritabanı kaydı başlanıyor...")

    for idx, (source_key, item) in enumerate(all_items, start=1):
        total_scraped += 1
        raw_title = item.get("title", "").strip()
        raw_url = item.get("original_url", "").strip()
        source = item.get("source", source_key)
        raw_summary = item.get("summary", "").strip()
        
        if not raw_title or not raw_url:
            continue
            
        try:
            # Deduplication Check
            query = select(TechCard).where(
                or_(
                    TechCard.original_url == raw_url,
                    TechCard.title == raw_title
                )
            )
            existing_res = await db.execute(query)
            existing_card = existing_res.scalars().first()
            
            if existing_card:
                print(f"[Pipeline] ⏭️ Zaten var, atlanıyor: '{raw_title}'")
                skipped_duplicates += 1
                continue

            # Directly create raw TechCard with is_analyzed = False
            tech_card = TechCard(
                title=raw_title,
                source=source,
                original_url=raw_url,
                image_url=item.get("image_url", None),
                summary=raw_summary,
                replaces_or_differs_from=None,
                technical_tradeoffs=None,
                core_concept=None,
                concept_definition=None,
                is_analyzed=False
            )
            
            db.add(tech_card)
            await db.commit()
            await db.refresh(tech_card)
            
            saved_cards.append(tech_card)
            saved_count += 1
            print(f"[Pipeline Başarılı] 📥 Ham Haber Kaydedildi (#{tech_card.id}): '{tech_card.title}'")

        except Exception as e:
            await db.rollback()
            failed_count += 1
            print(f"[Pipeline Hata] ❌ Ham haber kaydı sırasında hata: {e}")
            logger.error(f"Pipeline error for '{raw_title}': {e}", exc_info=True)
            continue
            
    summary_report = {
        "status": "success",
        "total_scraped": total_scraped,
        "saved_count": saved_count,
        "skipped_duplicates": skipped_duplicates,
        "failed_count": failed_count,
        "details": {k: len(v) for k, v in scraped_data.items()}
    }
    
    print("\n[Pipeline Tamamlandı] Özet:")
    print(f"  - Toplam Haber: {total_scraped}")
    print(f"  - Başarıyla Kaydedilen (Ham): {saved_count}")
    print(f"  - Atlanan (Zaten Var): {skipped_duplicates}")
    print(f"  - Başarısız/Hatalı: {failed_count}")
    
    return summary_report


async def run_politics_pipeline(db: AsyncSession, limit_per_source: int = 5) -> Dict[str, Any]:
    """
    Executes raw politics news collection pipeline:
    1. Scrapes political news from BBC Türkçe, T24, Sabah, Sözcü, Gazete Oksijen, TBMM Gündemi.
    2. Deduplicates against existing DB records by original_url or title.
    3. Saves raw politics cards directly to PoliticsCard table with is_analyzed = False.
    """
    print("[Politics Pipeline] Siyaset haber tarayıcıları çalıştırılıyor...")
    scraped_data = await fetch_all_politics_news(limit_per_source=limit_per_source)
    
    total_scraped = 0
    skipped_duplicates = 0
    saved_count = 0
    failed_count = 0
    saved_cards: List[PoliticsCard] = []
    
    all_items = []
    for source_key, items in scraped_data.items():
        for item in items:
            all_items.append((source_key, item))
            
    total_items = len(all_items)
    print(f"[Politics Pipeline] Toplam {total_items} adet ham siyaset haberi toplandı. Veritabanı kaydı başlanıyor...")

    for idx, (source_key, item) in enumerate(all_items, start=1):
        total_scraped += 1
        raw_title = item.get("title", "").strip()
        raw_url = item.get("original_url", "").strip()
        source = item.get("source", source_key)
        raw_summary = item.get("summary", "").strip()
        
        if not raw_title or not raw_url:
            continue
            
        try:
            # Deduplication Check
            if source == "TBMM":
                query = select(PoliticsCard).where(PoliticsCard.title == raw_title)
            else:
                query = select(PoliticsCard).where(
                    or_(
                        PoliticsCard.original_url == raw_url,
                        PoliticsCard.title == raw_title
                    )
                )
            existing_res = await db.execute(query)
            existing_card = existing_res.scalars().first()
            
            if existing_card:
                print(f"[Politics Pipeline] ⏭️ Zaten var, atlanıyor: '{raw_title}'")
                skipped_duplicates += 1
                continue

            # Create raw PoliticsCard with is_analyzed = False
            politics_card = PoliticsCard(
                title=raw_title,
                source=source,
                original_url=raw_url,
                image_url=item.get("image_url", None),
                summary=raw_summary,
                today_summary=None,
                rational_arguments=None,
                historical_background=None,
                core_concept=None,
                concept_definition=None,
                is_analyzed=False
            )
            
            db.add(politics_card)
            await db.commit()
            await db.refresh(politics_card)
            
            saved_cards.append(politics_card)
            saved_count += 1
            print(f"[Politics Pipeline Başarılı] 📥 Ham Siyaset Haberi Kaydedildi (#{politics_card.id}): '{politics_card.title}'")

        except Exception as e:
            await db.rollback()
            failed_count += 1
            print(f"[Politics Pipeline Hata] ❌ Ham siyaset haberi kaydı sırasında hata: {e}")
            logger.error(f"Politics Pipeline error for '{raw_title}': {e}", exc_info=True)
            continue
            
    summary_report = {
        "status": "success",
        "total_scraped": total_scraped,
        "saved_count": saved_count,
        "skipped_duplicates": skipped_duplicates,
        "failed_count": failed_count,
        "details": {k: len(v) for k, v in scraped_data.items()}
    }
    
    print("\n[Politics Pipeline Tamamlandı] Özet:")
    print(f"  - Toplam Haber: {total_scraped}")
    print(f"  - Başarıyla Kaydedilen (Ham): {saved_count}")
    print(f"  - Atlanan (Zaten Var): {skipped_duplicates}")
    print(f"  - Başarısız/Hatalı: {failed_count}")
    
    return summary_report


async def run_football_pipeline(db: AsyncSession, limit_per_source: int = 5) -> Dict[str, Any]:
    """
    Executes raw football news collection pipeline:
    1. Scrapes football news from GZT Spor, Sporx Futbol, DHA Spor, Transfer Radar.
    2. Deduplicates against existing DB records by original_url or title.
    3. Saves raw football cards directly to FootballCard table with is_analyzed = False.
    """
    print("[Football Pipeline] Futbol haber tarayıcıları çalıştırılıyor...")
    scraped_data = await fetch_all_football_news(limit_per_source=limit_per_source)
    
    total_scraped = 0
    skipped_duplicates = 0
    saved_count = 0
    failed_count = 0
    saved_cards: List[FootballCard] = []
    
    all_items = []
    for source_key, items in scraped_data.items():
        for item in items:
            all_items.append((source_key, item))
            
    total_items = len(all_items)
    print(f"[Football Pipeline] Toplam {total_items} adet ham futbol haberi toplandı. Veritabanı kaydı başlanıyor...")

    for idx, (source_key, item) in enumerate(all_items, start=1):
        total_scraped += 1
        raw_title = item.get("title", "").strip()
        raw_url = item.get("original_url", "").strip()
        source = item.get("source", source_key)
        raw_summary = item.get("summary", "").strip()
        
        if not raw_title or not raw_url:
            continue
            
        try:
            # Deduplication Check
            query = select(FootballCard).where(
                or_(
                    FootballCard.original_url == raw_url,
                    FootballCard.title == raw_title
                )
            )
            existing_res = await db.execute(query)
            existing_card = existing_res.scalars().first()
            
            if existing_card:
                print(f"[Football Pipeline] ⏭️ Zaten var, atlanıyor: '{raw_title}'")
                skipped_duplicates += 1
                continue

            # Create raw FootballCard with is_analyzed = False
            football_card = FootballCard(
                title=raw_title,
                source=source,
                original_url=raw_url,
                image_url=item.get("image_url", None),
                summary=raw_summary,
                today_summary=None,
                rational_arguments=None,
                historical_background=None,
                core_concept=None,
                concept_definition=None,
                is_analyzed=False
            )
            
            db.add(football_card)
            await db.commit()
            await db.refresh(football_card)
            
            saved_cards.append(football_card)
            saved_count += 1
            print(f"[Football Pipeline Başarılı] 📥 Ham Futbol Haberi Kaydedildi (#{football_card.id}): '{football_card.title}'")

        except Exception as e:
            await db.rollback()
            failed_count += 1
            print(f"[Football Pipeline Hata] ❌ Ham futbol haberi kaydı sırasında hata: {e}")
            logger.error(f"Football Pipeline error for '{raw_title}': {e}", exc_info=True)
            continue
            
    summary_report = {
        "status": "success",
        "total_scraped": total_scraped,
        "saved_count": saved_count,
        "skipped_duplicates": skipped_duplicates,
        "failed_count": failed_count,
        "details": {k: len(v) for k, v in scraped_data.items()}
    }
    
    print("\n[Football Pipeline Tamamlandı] Özet:")
    print(f"  - Toplam Haber: {total_scraped}")
    print(f"  - Başarıyla Kaydedilen (Ham): {saved_count}")
    print(f"  - Atlanan (Zaten Var): {skipped_duplicates}")
    print(f"  - Başarısız/Hatalı: {failed_count}")
    
    return summary_report



