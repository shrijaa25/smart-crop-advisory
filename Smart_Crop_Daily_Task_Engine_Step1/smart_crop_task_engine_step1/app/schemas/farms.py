from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FarmCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    village: str | None = Field(default=None, max_length=120)
    district: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    area_value: float | None = Field(default=None, gt=0)
    area_unit: str = Field(default="acre", min_length=1, max_length=20)
    soil_type: str | None = Field(default=None, max_length=80)
    irrigation_method: str | None = Field(default=None, max_length=80)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class FarmOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    village: str | None
    district: str | None
    state: str | None
    latitude: float | None
    longitude: float | None
    area_value: float | None
    area_unit: str
    soil_type: str | None
    irrigation_method: str | None


class CropCycleCreate(BaseModel):
    crop_name: Literal["tomato", "chilli"]
    variety: str | None = Field(default=None, max_length=120)
    planting_date: date
    planting_method: str = Field(default="transplanting", min_length=1, max_length=30)
    area_value: float = Field(gt=0)
    area_unit: str = Field(min_length=1, max_length=20)
    notes: str | None = None

    @field_validator("planting_date")
    @classmethod
    def planting_date_not_in_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Transplanting date cannot be in the future.")
        return value


class CropCycleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    farm_id: int
    crop_name: str
    variety: str | None
    planting_date: date
    planting_method: str
    area_value: float | None
    area_unit: str
    status: str
    notes: str | None
