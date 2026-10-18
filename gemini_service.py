import os
import json
import logging
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

load_dotenv(override=True)

logger = logging.getLogger(__name__)

STRENGTHENED_SYSTEM_PROMPT = (
    "Sen kıdemli bir yazılım mimarı ve Türkçe içerik üreten teknik bir editörsün. "
    "Girdiğin metin İngilizce olsa bile BÜTÜN YANITLARINI KESİNLİKLE TÜRKÇE (Turkish) VERMELİSİN.\n\n"
    "Kurallar ve Alan Detayları:\n"
    "1. 'title': Haberin reklam ve hype dilinden arındırılmış net teknik Türkçe başlığı.\n"
    "2. 'summary' (Bugün Ne Oldu?): Haberin özünü, teknik detayları ve mühendislik değerini KAPSAMLI ve DETAYLI bir paragraf ile Türkçe anlat. Metadata döndürme!\n"
    "3. 'replaces_or_differs_from' (Farkı): Bu teknolojinin piyasadaki rakiplerinden veya eski yöntemlerden somut mimari farklarını açıkla.\n"
    "4. 'technical_tradeoffs' (Trade-off): Avantaj ve dezavantajlarını teknik bir dille detaylandır.\n"
    "5. 'core_concept': Temel bilgisayar bilimleri kavramı veya mimari terim.\n"
    "6. 'concept_definition' (Entelektüel Sözlük): Seçtiğin temel bilgisayar bilimleri kavramını derinlemesine ve öğretici bir şekilde Türkçe tanımla."
)


class TechNewsAnalysisSchema(BaseModel):
    title: str = Field(description="Teknik haber başlığı")
    summary: str = Field(description="Haberin detaylı teknik özeti")
    replaces_or_differs_from: str = Field(description="Alternatiflerden farkları")
    technical_tradeoffs: str = Field(description="Teknik avantaj ve dezavantajlar")
    core_concept: str = Field(description="Temel bilgisayar bilimleri kavramı")
    concept_definition: str = Field(description="Temel kavramın açıklaması")


def _get_genai_client() -> genai.Client:
    load_dotenv(override=True)
    api_key = os.getenv("AI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Neither AI_API_KEY nor GEMINI_API_KEY environment variable is set.")
    return genai.Client(api_key=api_key)


async def analyze_tech_news(raw_title: str, raw_content: str, source: str) -> TechNewsAnalysisSchema:
    """
    Asynchronously analyzes technical news using Google Gemini API (preferred model: gemini-1.5-flash).
    Returns a valid TechNewsAnalysisSchema Pydantic object.
    """
    client = _get_genai_client()
    
    user_prompt = (
        f"Kaynak: {source}\n"
        f"Başlık: {raw_title}\n"
        f"Haber İçeriği / Notlar: {raw_content}\n\n"
        "Lütfen bu haberi bir yazılım mimarı gözüyle incele ve TÜM ALANLARI TÜRKÇE olarak doldurup JSON olarak döndür."
    )

    models_to_try = ["gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash"]
    last_exception = None

    for model_name in models_to_try:
        try:
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=STRENGTHENED_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=TechNewsAnalysisSchema,
                    temperature=0.2,
                ),
            )

            if hasattr(response, "parsed") and response.parsed is not None:
                if isinstance(response.parsed, TechNewsAnalysisSchema):
                    return response.parsed
                elif isinstance(response.parsed, dict):
                    return TechNewsAnalysisSchema(**response.parsed)

            if response.text:
                return TechNewsAnalysisSchema.model_validate_json(response.text)
                
        except Exception as e:
            last_exception = e
            logger.warning(f"Model '{model_name}' call failed: {e}. Trying next fallback...")

    logger.error(f"Gemini API analysis failed for '{raw_title}': {last_exception}")
    raise last_exception or ValueError("Gemini API empty response or unparseable output.")


POLITICS_SYSTEM_PROMPT = (
    "Sen tarafsız bir siyaset bilimci ve stratejistsin. Amacın siyasi haberlerdeki partizan gürültüyü, "
    "abartıyı ve ajitatif dili tamamen temizleyerek saf gerçeği sunmaktır. Çıktı kesinlikle JSON olmalı ve şu alanları içermeli:\n"
    "- `today_summary`: Olayın doğrudan, yalın ve tarafsız çekirdeği (1-2 cümle).\n"
    "- `rational_arguments`: Tarafların içi boş polemikleri yerine, arkalarındaki gerçek, rasyonel ve stratejik argümanlar neler?\n"
    "- `historical_background`: Bu konu geçmişte nasıl gündeme geldi? DİKKAT: Tarihsel arka planı çıkarırken KESİNLİKLE 2005 yılı ve sonrasındaki olayları baz al. 2005'ten önceki hiçbir olayı, tarihi veya dönüm noktasını analize dahil ETME. Kronolojik 3 kilit madde ver.\n"
    "- `core_concept`: Haberi kavramak için bilinmesi gereken temel siyasi/hukuki terim veya kurum (Örn: Torba yasa, Gensoru, Venedik Komisyonu vb.)\n"
    "- `concept_definition`: Bu terimin net ve akademik tanımı."
)


class PoliticsAnalysisSchema(BaseModel):
    today_summary: str = Field(description="Olayın doğrudan, yalın ve tarafsız çekirdeği (1-2 cümle)")
    rational_arguments: str = Field(description="Tarafların rasyonel ve stratejik argümanları")
    historical_background: str = Field(description="2005 ve sonrası tarihsel zaman tüneli (kronolojik 3 kilit madde)")
    core_concept: str = Field(description="Temel siyasi/hukuki terim veya kurum")
    concept_definition: str = Field(description="Terimin net ve akademik tanımı")


async def analyze_politics_news(title: str, summary: str, source: str) -> PoliticsAnalysisSchema:
    """
    Asynchronously analyzes political news using Google Gemini API (preferred model: gemini-1.5-flash).
    Returns a valid PoliticsAnalysisSchema Pydantic object.
    """
    client = _get_genai_client()

    user_prompt = (
        f"Kaynak: {source}\n"
        f"Başlık: {title}\n"
        f"Haber İçeriği / Özet: {summary}\n\n"
        "Lütfen bu haberi tarafsız bir siyaset bilimci gözüyle incele ve TÜM ALANLARI TÜRKÇE olarak doldurup JSON olarak döndür."
    )

    models_to_try = ["gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash"]
    last_exception = None

    for model_name in models_to_try:
        try:
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=POLITICS_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=PoliticsAnalysisSchema,
                    temperature=0.2,
                ),
            )

            if hasattr(response, "parsed") and response.parsed is not None:
                if isinstance(response.parsed, PoliticsAnalysisSchema):
                    return response.parsed
                elif isinstance(response.parsed, dict):
                    return PoliticsAnalysisSchema(**response.parsed)

            if response.text:
                return PoliticsAnalysisSchema.model_validate_json(response.text)

        except Exception as e:
            last_exception = e
            logger.warning(f"Politics Model '{model_name}' call failed: {e}. Trying next fallback...")

    logger.error(f"Gemini API politics analysis failed for '{title}': {last_exception}")
    raise last_exception or ValueError("Gemini API empty response or unparseable output.")


FOOTBALL_SYSTEM_PROMPT = (
    "Sen tarafsız bir sportif direktör, taktiksel analist ve spor ekonomistisin. Türk ve dünya futbolundaki "
    "holiganizmi, dedikoduyu, taraftar polemiklerini ve clickbait spor medyasını tamamen temizle. Çıktı kesinlikle JSON olmalı ve şu alanları içermeli:\n"
    "- `today_summary`: Transferin, maçın veya TFF/Kulüp kararının saf ve abartısız gerçeği (1-2 cümle).\n"
    "- `rational_arguments`: Taraftar tartışmaları yerine, bu olayın arkasındaki teknik/taktik gereksinimler, kulübün mali (ekonomik) stratejisi veya rasyonel argümanlar neler?\n"
    "- `historical_background`: Bu kulüp, oyuncu veya benzer krizler geçmişte nasıl gelişti? DİKKAT: Tarihsel arka planı çıkarırken KESİNLİKLE 2005 yılı ve sonrasındaki olayları baz al. 2005'ten önceki hiçbir olayı, transferi veya maç sonucunu analize dahil ETME. Kronolojik 3 kilit madde ver.\n"
    "- `core_concept`: Haberi tam kavramak için bilinmesi gereken futbol/spor yönetimi terimi (Örn: Finansal Fair Play, Bosman Kuralı, Gegenpressing, Opsiyonlu Kiralama vb.)\n"
    "- `concept_definition`: Bu terimin net ve profesyonel tanımı."
)


class FootballAnalysisSchema(BaseModel):
    today_summary: str = Field(description="Transferin, maçın veya TFF/Kulüp kararının saf ve abartısız gerçeği (1-2 cümle)")
    rational_arguments: str = Field(description="Teknik/taktik gereksinimler, kulübün mali/ekonomik stratejisi veya rasyonel argümanlar")
    historical_background: str = Field(description="2005 ve sonrası tarihsel zaman tüneli (kronolojik 3 kilit madde)")
    core_concept: str = Field(description="Futbol/spor yönetimi terimi")
    concept_definition: str = Field(description="Terimin net ve profesyonel tanımı")


async def analyze_football_news(title: str, summary: str, source: str) -> FootballAnalysisSchema:
    """
    Asynchronously analyzes football news using Google Gemini API (preferred model: gemini-1.5-flash).
    Returns a valid FootballAnalysisSchema Pydantic object.
    """
    client = _get_genai_client()

    user_prompt = (
        f"Kaynak: {source}\n"
        f"Başlık: {title}\n"
        f"Haber İçeriği / Özet: {summary}\n\n"
        "Lütfen bu haberi tarafsız bir sportif direktör ve taktiksel analist gözüyle incele ve TÜM ALANLARI TÜRKÇE olarak doldurup JSON olarak döndür."
    )

    models_to_try = ["gemini-3.6-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash"]
    last_exception = None

    for model_name in models_to_try:
        try:
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=FOOTBALL_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=FootballAnalysisSchema,
                    temperature=0.2,
                ),
            )

            if hasattr(response, "parsed") and response.parsed is not None:
                if isinstance(response.parsed, FootballAnalysisSchema):
                    return response.parsed
                elif isinstance(response.parsed, dict):
                    return FootballAnalysisSchema(**response.parsed)

            if response.text:
                return FootballAnalysisSchema.model_validate_json(response.text)

        except Exception as e:
            last_exception = e
            logger.warning(f"Football Model '{model_name}' call failed: {e}. Trying next fallback...")

    logger.error(f"Gemini API football analysis failed for '{title}': {last_exception}")
    raise last_exception or ValueError("Gemini API empty response or unparseable output.")






