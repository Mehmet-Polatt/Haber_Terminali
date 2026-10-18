import json
import asyncio
from contextlib import asynccontextmanager
from typing import List, Dict, Any
import traceback
import logging
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import init_db, get_db, AsyncSessionLocal
from models import TechCard, PoliticsCard, FootballCard
from schemas import (
    TechCardCreate, TechCardResponse,
    PoliticsCardCreate, PoliticsCardResponse,
    FootballCardCreate, FootballCardResponse
)
from scrapers.runner import fetch_all_tech_news
from scrapers.politics_scrapers import fetch_all_politics_news
from scrapers.football_scrapers import fetch_all_football_news
from pipeline import run_pipeline, run_politics_pipeline, run_football_pipeline, normalize_turkish
import gemini_service


logger = logging.getLogger(__name__)


# --- BACKGROUND & SCHEDULED PIPELINE WRAPPERS ---

async def run_tech_pipeline_bg():
    async with AsyncSessionLocal() as session:
        try:
            print("[Background Task] 🚀 Teknoloji pipeline'ı anlık olarak çalıştırılıyor...")
            await run_pipeline(db=session, limit_per_source=5)
        except Exception as e:
            print(f"[Background Task Hata - Teknoloji]: {e}")
            logger.error(f"Background tech pipeline error: {e}")


async def run_politics_pipeline_bg():
    async with AsyncSessionLocal() as session:
        try:
            print("[Background Task] 🚀 Siyaset/TBMM pipeline'ı anlık olarak çalıştırılıyor...")
            await run_politics_pipeline(db=session, limit_per_source=5)
        except Exception as e:
            print(f"[Background Task Hata - Siyaset]: {e}")
            logger.error(f"Background politics pipeline error: {e}")


async def run_football_pipeline_bg():
    async with AsyncSessionLocal() as session:
        try:
            print("[Background Task] 🚀 Futbol pipeline'ı anlık olarak çalıştırılıyor...")
            await run_football_pipeline(db=session, limit_per_source=5)
        except Exception as e:
            print(f"[Background Task Hata - Futbol]: {e}")
            logger.error(f"Background football pipeline error: {e}")


async def run_all_pipelines_bg():
    print("\n[Scheduler] ⏰ Saatlik (every 1 hour) tüm haber boru hatları (Teknoloji, Siyaset, Futbol, TBMM) başlatılıyor...")
    async with AsyncSessionLocal() as session:
        try:
            await run_pipeline(db=session, limit_per_source=5)
            await run_politics_pipeline(db=session, limit_per_source=5)
            await run_football_pipeline(db=session, limit_per_source=5)
            print("[Scheduler] ✅ Saatlik tüm haber boru hatları başarıyla tamamlandı.")
        except Exception as e:
            print(f"[Scheduler Hata]: {e}")
            logger.error(f"Scheduled pipelines error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB tables if reachable
    try:
        await init_db()
    except Exception as e:
        print(f"[Warning] Could not initialize DB on startup: {e}")

    # Start Hourly Scheduler (Every 1 hour)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_all_pipelines_bg, 'interval', hours=1)
    scheduler.start()
    print("[Scheduler] ⏰ Saatlik (hourly / every 1 hour) zamanlayıcı başarıyla başlatıldı.")

    yield

    scheduler.shutdown()


app = FastAPI(
    title="Haber Terminali API",
    description="Asenkron Haber Toplama & İsteğe Bağlı Gemini AI Analizi Backend Altyapısı",
    version="6.0.0",
    lifespan=lifespan
)

# CORS Configuration for Mobile / Cross-Origin Connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "online",
        "app": "Haber Terminali",
        "version": "6.0.0",
        "endpoints": {
            "get_cards": "/api/cards",
            "get_card_by_id": "/api/cards/{id}",
            "analyze_card": "/api/cards/{id}/analyze (POST)",
            "create_card": "/api/cards (POST)",
            "trigger_pipeline": "/api/scrape (POST)",
            "refresh_all_news": "/api/refresh (POST)",
            "get_politics_cards": "/api/politics/cards",
            "get_politics_card_by_id": "/api/politics/cards/{id}",
            "analyze_politics_card": "/api/politics/cards/{id}/analyze (POST)",
            "trigger_politics_pipeline": "/api/scrape-politics (POST)",
            "get_football_cards": "/api/football/cards",
            "get_football_card_by_id": "/api/football/cards/{id}",
            "analyze_football_card": "/api/football/cards/{id}/analyze (POST)",
            "trigger_football_pipeline": "/api/scrape-football (POST)",
            "preview_scrapers": "/api/scrape/preview (GET)"
        }
    }


@app.post("/api/refresh", tags=["Pipeline"])
async def refresh_all_news():
    """Fetch fresh news across all categories when the mobile app is opened."""
    await run_all_pipelines_bg()
    return {"status": "completed", "message": "Tüm haber kaynakları yenilendi."}


@app.get("/api/cards", response_model=List[TechCardResponse], tags=["TechCards"])
async def list_tech_cards(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    List stored TechCard items ordered by creation date descending (ORDER BY created_at DESC)
    with pagination support.
    """
    result = await db.execute(
        select(TechCard)
        .order_by(TechCard.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    cards = result.scalars().all()
    return cards


@app.get("/api/cards/{card_id}", response_model=TechCardResponse, tags=["TechCards"])
async def get_tech_card_by_id(
    card_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve full details of a specific TechCard by its unique ID.
    """
    card = await db.get(TechCard, card_id)
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"TechCard with ID {card_id} not found."
        )
    return card


@app.post("/api/cards/{card_id}/analyze", response_model=TechCardResponse, tags=["On-Demand AI Analysis"])
async def analyze_tech_card_on_demand(
    card_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    On-Demand Gemini AI Analysis for a specific TechCard:
    If card is already analyzed, returns card.
    If is_analyzed is False, triggers Gemini AI analysis, updates fields, sets is_analyzed = True, and saves to DB.
    Comprehensive traceback error handling and explicit detail error response.
    """
    try:
        card = await db.get(TechCard, card_id)
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"TechCard with ID {card_id} not found."
            )

        # Return immediately if already analyzed
        if card.is_analyzed:
            return card

        # Perform Gemini AI Analysis (gemini-1.5-flash)
        ai_result = await gemini_service.analyze_tech_news(
            raw_title=card.title,
            raw_content=card.summary or "",
            source=card.source
        )

        # Safely extract attributes whether ai_result is Pydantic model or dict
        if isinstance(ai_result, dict):
            summary_val = ai_result.get("summary")
            replaces_val = ai_result.get("replaces_or_differs_from")
            tradeoffs_val = ai_result.get("technical_tradeoffs")
            concept_val = ai_result.get("core_concept")
            concept_def_val = ai_result.get("concept_definition")
            title_val = ai_result.get("title")
        else:
            summary_val = getattr(ai_result, "summary", None)
            replaces_val = getattr(ai_result, "replaces_or_differs_from", None)
            tradeoffs_val = getattr(ai_result, "technical_tradeoffs", None)
            concept_val = getattr(ai_result, "core_concept", None)
            concept_def_val = getattr(ai_result, "concept_definition", None)
            title_val = getattr(ai_result, "title", None)

        card.title = title_val or card.title
        card.summary = summary_val or card.summary
        card.replaces_or_differs_from = replaces_val
        card.technical_tradeoffs = tradeoffs_val
        card.core_concept = concept_val
        card.concept_definition = concept_def_val
        card.is_analyzed = True

        await db.commit()
        await db.refresh(card)
        return card

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"\n[Analyze Error in /api/cards/{card_id}/analyze]: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/api/cards", response_model=TechCardResponse, status_code=status.HTTP_201_CREATED, tags=["TechCards"])
async def create_tech_card(
    card_in: TechCardCreate,
    db: AsyncSession = Depends(get_db)
):
    """Manually insert a new TechCard item into the database."""
    card = TechCard(
        title=card_in.title,
        source=card_in.source,
        original_url=card_in.original_url,
        summary=card_in.summary,
        replaces_or_differs_from=card_in.replaces_or_differs_from,
        technical_tradeoffs=card_in.technical_tradeoffs,
        core_concept=card_in.core_concept,
        concept_definition=card_in.concept_definition,
        is_analyzed=card_in.is_analyzed,
    )
    db.add(card)
    await db.commit()
    await db.refresh(card)
    return card


@app.get("/api/scrape/preview", tags=["Scrapers"])
async def preview_scrapers(limit_per_source: int = 5) -> Dict[str, List[Dict[str, Any]]]:
    """
    Triggers scrapers (DonanımHaber, Webrazzi, Anadolu Ajansı) asynchronously 
    and returns parsed raw results without writing to DB.
    """
    scraped_data = await fetch_all_tech_news(limit_per_source=limit_per_source)
    return scraped_data


@app.post("/api/scrape", tags=["Pipeline"])
async def trigger_pipeline(
    limit_per_source: int = 5,
    db: AsyncSession = Depends(get_db)
):
    """
    Triggers raw news collection pipeline (Scrapes -> Deduplicates -> Saves raw TechCards with is_analyzed=False).
    """
    result = await run_pipeline(db=db, limit_per_source=limit_per_source)
    return result


# --- POLITICS ENDPOINTS ---

@app.get("/api/politics/cards", response_model=List[PoliticsCardResponse], tags=["PoliticsCards"])
async def list_politics_cards(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    List stored PoliticsCard items (excluding TBMM) ordered by creation date descending
    with pagination support.
    """
    result = await db.execute(
        select(PoliticsCard)
        .where(PoliticsCard.source != "TBMM")
        .order_by(PoliticsCard.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    cards = result.scalars().all()
    return cards


@app.get("/api/tbmm/cards", response_model=List[PoliticsCardResponse], tags=["PoliticsCards"])
async def list_tbmm_cards(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    List stored PoliticsCard items where source is 'TBMM' ordered by creation date descending
    with pagination support.
    """
    result = await db.execute(
        select(PoliticsCard)
        .where(PoliticsCard.source == "TBMM")
        .order_by(PoliticsCard.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    cards = result.scalars().all()
    return cards


@app.get("/api/politics/cards/{card_id}", response_model=PoliticsCardResponse, tags=["PoliticsCards"])
async def get_politics_card_by_id(
    card_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve full details of a specific PoliticsCard by its unique ID.
    """
    card = await db.get(PoliticsCard, card_id)
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PoliticsCard with ID {card_id} not found."
        )
    return card


@app.post("/api/politics/cards/{card_id}/analyze", response_model=PoliticsCardResponse, tags=["On-Demand AI Analysis"])
async def analyze_politics_card_on_demand(
    card_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    On-Demand Gemini AI Analysis for a specific PoliticsCard:
    If card is already analyzed, returns card.
    If is_analyzed is False, triggers analyze_politics_news, updates fields, sets is_analyzed = True, and saves to DB.
    """
    try:
        card = await db.get(PoliticsCard, card_id)
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"PoliticsCard with ID {card_id} not found."
            )

        if card.is_analyzed:
            return card

        ai_result = await gemini_service.analyze_politics_news(
            title=card.title,
            summary=card.summary or "",
            source=card.source
        )

        if isinstance(ai_result, dict):
            today_sum = ai_result.get("today_summary")
            rational_args = ai_result.get("rational_arguments")
            hist_bg = ai_result.get("historical_background")
            concept = ai_result.get("core_concept")
            concept_def = ai_result.get("concept_definition")
        else:
            today_sum = getattr(ai_result, "today_summary", None)
            rational_args = getattr(ai_result, "rational_arguments", None)
            hist_bg = getattr(ai_result, "historical_background", None)
            concept = getattr(ai_result, "core_concept", None)
            concept_def = getattr(ai_result, "concept_definition", None)

        card.today_summary = today_sum or card.today_summary or card.summary
        card.rational_arguments = rational_args
        card.historical_background = hist_bg
        card.core_concept = concept
        card.concept_definition = concept_def
        card.is_analyzed = True

        await db.commit()
        await db.refresh(card)
        return card

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"\n[Analyze Error in /api/politics/cards/{card_id}/analyze]: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/api/politics/cards", response_model=PoliticsCardResponse, status_code=status.HTTP_201_CREATED, tags=["PoliticsCards"])
async def create_politics_card(
    card_in: PoliticsCardCreate,
    db: AsyncSession = Depends(get_db)
):
    """Manually insert a new PoliticsCard item into the database."""
    card = PoliticsCard(
        title=card_in.title,
        source=card_in.source,
        original_url=card_in.original_url,
        summary=card_in.summary,
        today_summary=card_in.today_summary,
        rational_arguments=card_in.rational_arguments,
        historical_background=card_in.historical_background,
        core_concept=card_in.core_concept,
        concept_definition=card_in.concept_definition,
        is_analyzed=card_in.is_analyzed,
    )
    db.add(card)
    await db.commit()
    await db.refresh(card)
    return card


@app.get("/api/scrape-politics/preview", tags=["Scrapers"])
async def preview_politics_scrapers(limit_per_source: int = 5) -> Dict[str, List[Dict[str, Any]]]:
    """
    Triggers politics scrapers asynchronously and returns parsed raw results without writing to DB.
    """
    scraped_data = await fetch_all_politics_news(limit_per_source=limit_per_source)
    return scraped_data


@app.post("/api/scrape-politics", tags=["Pipeline"])
async def trigger_politics_pipeline(
    limit_per_source: int = 5,
    db: AsyncSession = Depends(get_db)
):
    """
    Triggers raw politics news collection pipeline.
    """
    result = await run_politics_pipeline(db=db, limit_per_source=limit_per_source)
    return result


# --- FOOTBALL ENDPOINTS ---

@app.get("/api/football/cards", response_model=List[FootballCardResponse], tags=["FootballCards"])
async def list_football_cards(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    List stored FootballCard items ordered by creation date descending (ORDER BY created_at DESC)
    with pagination support.
    """
    result = await db.execute(
        select(FootballCard)
        .order_by(FootballCard.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    cards = result.scalars().all()
    return cards


@app.get("/api/football/cards/{card_id}", response_model=FootballCardResponse, tags=["FootballCards"])
async def get_football_card_by_id(
    card_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve full details of a specific FootballCard by its unique ID.
    """
    card = await db.get(FootballCard, card_id)
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"FootballCard with ID {card_id} not found."
        )
    return card


@app.post("/api/football/cards/{card_id}/analyze", response_model=FootballCardResponse, tags=["On-Demand AI Analysis"])
async def analyze_football_card_on_demand(
    card_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    On-Demand Gemini AI Analysis for a specific FootballCard:
    If card is already analyzed, returns card.
    If is_analyzed is False, triggers analyze_football_news, updates fields, sets is_analyzed = True, and saves to DB.
    """
    try:
        card = await db.get(FootballCard, card_id)
        if not card:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"FootballCard with ID {card_id} not found."
            )

        if card.is_analyzed:
            return card

        ai_result = await gemini_service.analyze_football_news(
            title=card.title,
            summary=card.summary or "",
            source=card.source
        )

        if isinstance(ai_result, dict):
            today_sum = ai_result.get("today_summary")
            rational_args = ai_result.get("rational_arguments")
            hist_bg = ai_result.get("historical_background")
            concept = ai_result.get("core_concept")
            concept_def = ai_result.get("concept_definition")
        else:
            today_sum = getattr(ai_result, "today_summary", None)
            rational_args = getattr(ai_result, "rational_arguments", None)
            hist_bg = getattr(ai_result, "historical_background", None)
            concept = getattr(ai_result, "core_concept", None)
            concept_def = getattr(ai_result, "concept_definition", None)

        card.today_summary = today_sum or card.today_summary or card.summary
        card.rational_arguments = rational_args
        card.historical_background = hist_bg
        card.core_concept = concept
        card.concept_definition = concept_def
        card.is_analyzed = True

        await db.commit()
        await db.refresh(card)
        return card

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"\n[Analyze Error in /api/football/cards/{card_id}/analyze]: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/api/football/cards", response_model=FootballCardResponse, status_code=status.HTTP_201_CREATED, tags=["FootballCards"])
async def create_football_card(
    card_in: FootballCardCreate,
    db: AsyncSession = Depends(get_db)
):
    """Manually insert a new FootballCard item into the database."""
    card = FootballCard(
        title=card_in.title,
        source=card_in.source,
        original_url=card_in.original_url,
        summary=card_in.summary,
        today_summary=card_in.today_summary,
        rational_arguments=card_in.rational_arguments,
        historical_background=card_in.historical_background,
        core_concept=card_in.core_concept,
        concept_definition=card_in.concept_definition,
        is_analyzed=card_in.is_analyzed,
    )
    db.add(card)
    await db.commit()
    await db.refresh(card)
    return card


@app.get("/api/scrape-football/preview", tags=["Scrapers"])
async def preview_football_scrapers(limit_per_source: int = 5) -> Dict[str, List[Dict[str, Any]]]:
    """
    Triggers football scrapers asynchronously and returns parsed raw results without writing to DB.
    """
    scraped_data = await fetch_all_football_news(limit_per_source=limit_per_source)
    return scraped_data


@app.post("/api/scrape-football", tags=["Pipeline"])
async def trigger_football_pipeline(
    limit_per_source: int = 5,
    db: AsyncSession = Depends(get_db)
):
    """
    Triggers raw football news collection pipeline.
    """
    result = await run_football_pipeline(db=db, limit_per_source=limit_per_source)
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)



