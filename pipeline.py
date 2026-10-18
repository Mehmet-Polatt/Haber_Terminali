import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, delete

from models import TechCard, PoliticsCard, FootballCard
from scrapers.runner import fetch_all_tech_news
from scrapers.politics_scrapers import fetch_all_politics_news
from scrapers.football_scrapers import fetch_all_football_news
from scrapers.utils import is_politics_relevant, fetch_article_image

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sabitler
# ---------------------------------------------------------------------------

NEWS_RETENTION_DAYS = 7  # Haberler bu kadar gün sonra otomatik silinir


# ---------------------------------------------------------------------------
# Yardımcı fonksiyonlar
# ---------------------------------------------------------------------------

def normalize_turkish(text: str) -> str:
    if not text:
        return ""
    # Önce tırnak ve gereksiz noktalama işaretlerini temizle
    text = text.replace('"', '').replace("'", '').replace('.', '')
    # Türkçe karakterleri doğru küçült
    text = (
        text.replace("İ", "i").replace("I", "ı")
            .replace("Ş", "ş").replace("Ç", "ç")
            .replace("Ğ", "ğ").replace("Ö", "ö").replace("Ü", "ü")
    )
    return text.lower().strip()


def _cutoff_dt() -> datetime:
    """7 gün öncesinin UTC datetime değerini döndürür (retention sınırı)."""
    return datetime.now(tz=timezone.utc) - timedelta(days=NEWS_RETENTION_DAYS)


# ---------------------------------------------------------------------------
# Retention (7 günlük otomatik temizlik) fonksiyonları
# ---------------------------------------------------------------------------

async def delete_expired_tech_cards(db: AsyncSession) -> int:
    """7 günden eski TechCard kayıtlarını siler. Silinen satır sayısını döndürür."""
    cutoff = _cutoff_dt()
    result = await db.execute(
        delete(TechCard).where(TechCard.created_at < cutoff)
    )
    await db.commit()
    deleted = result.rowcount or 0
    if deleted:
        print(f"[Retention] 🗑️  {deleted} eski TechCard silindi (>{NEWS_RETENTION_DAYS} gün).")
    return deleted


async def delete_expired_politics_cards(db: AsyncSession) -> int:
    """7 günden eski PoliticsCard kayıtlarını siler. Silinen satır sayısını döndürür."""
    cutoff = _cutoff_dt()
    result = await db.execute(
        delete(PoliticsCard).where(PoliticsCard.created_at < cutoff)
    )
    await db.commit()
    deleted = result.rowcount or 0
    if deleted:
        print(f"[Retention] 🗑️  {deleted} eski PoliticsCard silindi (>{NEWS_RETENTION_DAYS} gün).")
    return deleted


async def delete_expired_football_cards(db: AsyncSession) -> int:
    """7 günden eski FootballCard kayıtlarını siler. Silinen satır sayısını döndürür."""
    cutoff = _cutoff_dt()
    result = await db.execute(
        delete(FootballCard).where(FootballCard.created_at < cutoff)
    )
    await db.commit()
    deleted = result.rowcount or 0
    if deleted:
        print(f"[Retention] 🗑️  {deleted} eski FootballCard silindi (>{NEWS_RETENTION_DAYS} gün).")
    return deleted


async def run_retention_cleanup(db: AsyncSession) -> Dict[str, int]:
    """
    Tüm kategorilerde 7 günden eski haberleri siler.
    Saatlik scheduler tarafından çağrılır; bağımsız olarak da tetiklenebilir.

    Returns:
        Her kategori için silinen kayıt sayısını içeren dict
    """
    print(f"\n[Retention] ♻️  7 günlük veritabanı temizliği başlatıldı ({datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')})...")
    tech_del = await delete_expired_tech_cards(db)
    politics_del = await delete_expired_politics_cards(db)
    football_del = await delete_expired_football_cards(db)
    total = tech_del + politics_del + football_del
    print(f"[Retention] ✅ Temizlik tamamlandı — toplam {total} kayıt silindi.")
    return {
        "deleted_tech": tech_del,
        "deleted_politics": politics_del,
        "deleted_football": football_del,
        "total_deleted": total,
    }


# ---------------------------------------------------------------------------
# Pipeline: Teknoloji
# ---------------------------------------------------------------------------

async def run_pipeline(db: AsyncSession, limit_per_source: int = 0) -> Dict[str, Any]:
    """
    Hızlı, ham teknoloji haberi toplama pipeline'ı (On-Demand Analysis Mimarisi):
    1. Tüm teknoloji kaynaklarından haber çeker (limit_per_source=0 → sınır yok).
    2. Veritabanındaki mevcut kayıtlara karşı duplicate kontrolü yapar.
    3. Ham TechCard'ları is_analyzed=False olarak kaydeder.
    4. Görsel eksikse makale sayfasından fallback olarak çeker.

    Args:
        limit_per_source: Kaynak başına maksimum haber sayısı.
                          0 veya negatif değer = sınırsız (tüm haberler).
    """
    effective_limit = limit_per_source if limit_per_source and limit_per_source > 0 else 9999

    print("[Pipeline] Haber tarayıcılar çalıştırılıyor...")
    scraped_data = await fetch_all_tech_news(limit_per_source=effective_limit)

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
        image_url = item.get("image_url")

        if not raw_title or not raw_url:
            continue

        try:
            # Duplicate kontrolü
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

            # Görsel yoksa makale sayfasından çekmeyi dene
            if not image_url and raw_url:
                image_url = await fetch_article_image(raw_url)

            tech_card = TechCard(
                title=raw_title,
                source=source,
                original_url=raw_url,
                image_url=image_url,
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


# ---------------------------------------------------------------------------
# Pipeline: Siyaset
# ---------------------------------------------------------------------------

async def run_politics_pipeline(db: AsyncSession, limit_per_source: int = 0) -> Dict[str, Any]:
    """
    Ham siyaset haberi toplama pipeline'ı:
    1. BBC Türkçe, T24, Sabah, Sözcü, Gazete Oksijen, TBMM Gündemi'nden haber çeker.
    2. Tüm kaynaklar için ortak is_politics_relevant filtresi uygular (sadece BBC değil!).
    3. Duplicate kontrolü yapar.
    4. Görsel yoksa makale sayfasından fallback olarak çeker.
    5. Ham PoliticsCard'ları is_analyzed=False olarak kaydeder.

    Args:
        limit_per_source: Kaynak başına maksimum haber sayısı.
                          0 veya negatif değer = sınırsız.
    """
    effective_limit = limit_per_source if limit_per_source and limit_per_source > 0 else 9999

    print("[Politics Pipeline] Siyaset haber tarayıcıları çalıştırılıyor...")
    scraped_data = await fetch_all_politics_news(limit_per_source=effective_limit)

    total_scraped = 0
    skipped_duplicates = 0
    skipped_irrelevant = 0
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
        image_url = item.get("image_url")

        if not raw_title or not raw_url:
            continue

        # -------------------------------------------------------------------
        # 🔒 Ortak siyaset filtresi — tüm kaynaklar için geçerli
        #    TBMM zaten siyasi içerik kaynağı olduğundan filtrelemeden geçirilir.
        # -------------------------------------------------------------------
        if source != "TBMM" and not is_politics_relevant(raw_title, raw_summary):
            print(f"[Politics Pipeline] 🚫 Filtre: Siyasetle alakasız, atlanıyor: '{raw_title[:60]}'")
            skipped_irrelevant += 1
            continue

        try:
            # Duplicate kontrolü
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

            # Görsel yoksa makale sayfasından çekmeyi dene
            if not image_url and raw_url:
                image_url = await fetch_article_image(raw_url)

            politics_card = PoliticsCard(
                title=raw_title,
                source=source,
                original_url=raw_url,
                image_url=image_url,
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
        "skipped_irrelevant": skipped_irrelevant,
        "failed_count": failed_count,
        "details": {k: len(v) for k, v in scraped_data.items()}
    }

    print("\n[Politics Pipeline Tamamlandı] Özet:")
    print(f"  - Toplam Haber: {total_scraped}")
    print(f"  - Başarıyla Kaydedilen (Ham): {saved_count}")
    print(f"  - Atlanan (Zaten Var): {skipped_duplicates}")
    print(f"  - Filtrelenen (Siyasetle Alakasız): {skipped_irrelevant}")
    print(f"  - Başarısız/Hatalı: {failed_count}")

    return summary_report


# ---------------------------------------------------------------------------
# Pipeline: Futbol
# ---------------------------------------------------------------------------

async def run_football_pipeline(db: AsyncSession, limit_per_source: int = 0) -> Dict[str, Any]:
    """
    Ham futbol haberi toplama pipeline'ı:
    1. GZT Spor, Sporx, DHA Spor, Transfer Radar kaynaklarından haber çeker.
    2. Duplicate kontrolü yapar.
    3. Görsel yoksa makale sayfasından fallback olarak çeker.
    4. Ham FootballCard'ları is_analyzed=False olarak kaydeder.

    Args:
        limit_per_source: Kaynak başına maksimum haber sayısı.
                          0 veya negatif değer = sınırsız.
    """
    effective_limit = limit_per_source if limit_per_source and limit_per_source > 0 else 9999

    print("[Football Pipeline] Futbol haber tarayıcıları çalıştırılıyor...")
    scraped_data = await fetch_all_football_news(limit_per_source=effective_limit)

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
        image_url = item.get("image_url")

        if not raw_title or not raw_url:
            continue

        try:
            # Duplicate kontrolü
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

            # Görsel yoksa makale sayfasından çekmeyi dene
            if not image_url and raw_url:
                image_url = await fetch_article_image(raw_url)

            football_card = FootballCard(
                title=raw_title,
                source=source,
                original_url=raw_url,
                image_url=image_url,
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
