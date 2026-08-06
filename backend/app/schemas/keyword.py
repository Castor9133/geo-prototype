"""
拓词模块 Schemas
"""
from typing import Any, List
from uuid import UUID

from pydantic import BaseModel, Field


class KeywordExpandRequest(BaseModel):
    seeds: List[str] = Field(default_factory=list, min_length=1, max_length=8)
    knowledge_base_id: UUID | None = None


class KeywordItemResponse(BaseModel):
    keyword: str
    recommendation_score: int
    business_score: int
    reason: str | None = None


class KeywordDimensionResponse(BaseModel):
    key: str
    name: str
    icon: str
    description: str
    count: int
    items: List[KeywordItemResponse]


class KeywordSummaryResponse(BaseModel):
    total_keywords: int
    average_recommendation_score: int
    average_business_score: int
    high_recommendation_ratio: int
    high_business_ratio: int


class KeywordProfileResponse(BaseModel):
    name: str
    company_hint: str
    business_model: str
    target_users: List[str]
    keyword_strategy: str


class KeywordPlatformMetaResponse(BaseModel):
    platform: str
    generation_focus: str = ""
    avoid: List[str] = Field(default_factory=list)


class KeywordPlatformTitleHintResponse(BaseModel):
    platform: str
    generation_focus: str = ""
    avoid: List[str] = Field(default_factory=list)
    titles: List[str] = Field(default_factory=list)


class KeywordAiFocusResponse(BaseModel):
    disclaimer: str = ""
    platforms: List[str] = Field(default_factory=list)
    items: List[KeywordPlatformMetaResponse] = Field(default_factory=list)


class KeywordExpandResponse(BaseModel):
    seeds: List[str]
    profile: KeywordProfileResponse
    dimensions: List[KeywordDimensionResponse]
    summary: KeywordSummaryResponse
    platform_title_hints: List[KeywordPlatformTitleHintResponse] = Field(default_factory=list)
    ai_focus: KeywordAiFocusResponse | None = None
    knowledge_meta: dict[str, Any] | None = None
