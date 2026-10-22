from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CropName = Literal["tomato", "chilli"]


class KnowledgeSourceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=250)
    file_name: str | None = None
    page_or_section: str | None = None
    publisher: str | None = None
    notes: str | None = None
    verification_status: str = "needs_review"


class KnowledgeSourceOut(KnowledgeSourceCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class FertilizerRuleCreate(BaseModel):
    crop_name: CropName
    variety: str | None = None
    stage_name: str | None = None
    day_start: int | None = Field(default=None, ge=0)
    day_end: int | None = Field(default=None, ge=0)
    days_basis: str = "after_transplanting"
    fertilizer_name: str = Field(min_length=1, max_length=160)
    nutrient_grade: str | None = None
    amount: float | None = Field(default=None, ge=0)
    unit: str | None = None
    area_basis: str | None = None
    application_method: str | None = None
    frequency: str | None = None
    one_time_day: int | None = Field(default=None, ge=0)
    instructions: str | None = None
    source_file: str | None = None
    source_page: str | None = None
    verification_status: str = "needs_review"
    is_active: bool = False


class FertilizerRuleOut(FertilizerRuleCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)
