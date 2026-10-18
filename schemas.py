from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class TechCardBase(BaseModel):
    title: str
    source: str
    original_url: str
    image_url: Optional[str] = None
    summary: Optional[str] = None
    replaces_or_differs_from: Optional[str] = None
    technical_tradeoffs: Optional[str] = None
    core_concept: Optional[str] = None
    concept_definition: Optional[str] = None
    is_analyzed: bool = False


class TechCardCreate(TechCardBase):
    pass


class TechCardResponse(TechCardBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PoliticsCardBase(BaseModel):
    title: str
    source: str
    original_url: str
    image_url: Optional[str] = None
    summary: Optional[str] = None
    today_summary: Optional[str] = None
    rational_arguments: Optional[str] = None
    historical_background: Optional[str] = None
    core_concept: Optional[str] = None
    concept_definition: Optional[str] = None
    is_analyzed: bool = False


class PoliticsCardCreate(PoliticsCardBase):
    pass


class PoliticsCardResponse(PoliticsCardBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PoliticsAnalysisSchema(BaseModel):
    today_summary: str = Field(description="Olayın doğrudan, yalın ve tarafsız çekirdeği (1-2 cümle)")
    rational_arguments: str = Field(description="Tarafların rasyonel ve stratejik argümanları")
    historical_background: str = Field(description="2005 ve sonrası tarihsel zaman tüneli (kronolojik 3 kilit madde)")
    core_concept: str = Field(description="Temel siyasi/hukuki terim veya kurum")
    concept_definition: str = Field(description="Terimin net ve akademik tanımı")


class FootballCardBase(BaseModel):
    title: str
    source: str
    original_url: str
    image_url: Optional[str] = None
    summary: Optional[str] = None
    today_summary: Optional[str] = None
    rational_arguments: Optional[str] = None
    historical_background: Optional[str] = None
    core_concept: Optional[str] = None
    concept_definition: Optional[str] = None
    is_analyzed: bool = False


class FootballCardCreate(FootballCardBase):
    pass


class FootballCardResponse(FootballCardBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FootballAnalysisSchema(BaseModel):
    today_summary: str = Field(description="Transferin, maçın veya TFF/Kulüp kararının saf ve abartısız gerçeği (1-2 cümle)")
    rational_arguments: str = Field(description="Teknik/taktik gereksinimler, kulübün mali/ekonomik stratejisi veya rasyonel argümanlar")
    historical_background: str = Field(description="2005 ve sonrası tarihsel zaman tüneli (kronolojik 3 kilit madde)")
    core_concept: str = Field(description="Futbol/spor yönetimi terimi")
    concept_definition: str = Field(description="Terimin net ve profesyonel tanımı")



class ScrapedItem(BaseModel):
    title: str
    source: str
    url: str
    image_url: Optional[str] = None
    summary: Optional[str] = None



