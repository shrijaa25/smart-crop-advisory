from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Farmer(Base):
    __tablename__ = "farmers"
    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(30), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(20), default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Farm(Base):
    __tablename__ = "farms"
    id: Mapped[int] = mapped_column(primary_key=True)
    farmer_id: Mapped[int] = mapped_column(ForeignKey("farmers.id"))
    name: Mapped[str] = mapped_column(String(120), default="My Farm")
    village: Mapped[str | None] = mapped_column(String(120))
    district: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(120))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    area_value: Mapped[float | None] = mapped_column(Float)
    area_unit: Mapped[str] = mapped_column(String(20), default="acre")
    soil_type: Mapped[str | None] = mapped_column(String(80))
    irrigation_method: Mapped[str | None] = mapped_column(String(80))


class CropCycle(Base):
    __tablename__ = "crop_cycles"
    id: Mapped[int] = mapped_column(primary_key=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"))
    crop_name: Mapped[str] = mapped_column(String(30))
    variety: Mapped[str | None] = mapped_column(String(120))
    planting_date: Mapped[date] = mapped_column(Date)
    planting_method: Mapped[str] = mapped_column(String(30), default="transplanting")
    area_value: Mapped[float | None] = mapped_column(Float)
    area_unit: Mapped[str] = mapped_column(String(20), default="acre")
    status: Mapped[str] = mapped_column(String(20), default="active")
    notes: Mapped[str | None] = mapped_column(Text)


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(250))
    file_name: Mapped[str | None] = mapped_column(String(250))
    page_or_section: Mapped[str | None] = mapped_column(String(120))
    publisher: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(String(40), default="needs_review")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CropStageRule(Base):
    __tablename__ = "crop_stage_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    crop_name: Mapped[str] = mapped_column(String(30), index=True)
    variety: Mapped[str | None] = mapped_column(String(120))
    stage_number: Mapped[int | None] = mapped_column(Integer)
    stage_name: Mapped[str] = mapped_column(String(120))
    day_start: Mapped[int | None] = mapped_column(Integer)
    day_end: Mapped[int | None] = mapped_column(Integer)
    days_basis: Mapped[str] = mapped_column(String(40), default="after_transplanting")
    source_file: Mapped[str | None] = mapped_column(String(250))
    source_page: Mapped[str | None] = mapped_column(String(120))
    verification_status: Mapped[str] = mapped_column(String(40), default="needs_review")


class FertilizerRule(Base):
    __tablename__ = "fertilizer_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    crop_name: Mapped[str] = mapped_column(String(30), index=True)
    variety: Mapped[str | None] = mapped_column(String(120))
    stage_name: Mapped[str | None] = mapped_column(String(120))
    day_start: Mapped[int | None] = mapped_column(Integer)
    day_end: Mapped[int | None] = mapped_column(Integer)
    days_basis: Mapped[str] = mapped_column(String(40), default="after_transplanting")
    fertilizer_name: Mapped[str] = mapped_column(String(160))
    nutrient_grade: Mapped[str | None] = mapped_column(String(80))
    amount: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(40))
    area_basis: Mapped[str | None] = mapped_column(String(80))
    application_method: Mapped[str | None] = mapped_column(String(120))
    frequency: Mapped[str | None] = mapped_column(String(120))
    one_time_day: Mapped[int | None] = mapped_column(Integer)
    instructions: Mapped[str | None] = mapped_column(Text)
    source_file: Mapped[str | None] = mapped_column(String(250))
    source_page: Mapped[str | None] = mapped_column(String(120))
    verification_status: Mapped[str] = mapped_column(String(40), default="needs_review")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)


class DiseasePestRule(Base):
    __tablename__ = "disease_pest_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    crop_name: Mapped[str] = mapped_column(String(30), index=True)
    problem_type: Mapped[str] = mapped_column(String(40))
    problem_name: Mapped[str] = mapped_column(String(160))
    local_name: Mapped[str | None] = mapped_column(String(160))
    symptoms: Mapped[str | None] = mapped_column(Text)
    prevention: Mapped[str | None] = mapped_column(Text)
    treatment_name: Mapped[str | None] = mapped_column(String(160))
    active_ingredient: Mapped[str | None] = mapped_column(String(160))
    dose_value: Mapped[float | None] = mapped_column(Float)
    dose_unit: Mapped[str | None] = mapped_column(String(40))
    water_volume_litre: Mapped[float | None] = mapped_column(Float)
    application_method: Mapped[str | None] = mapped_column(String(120))
    timing_guidance: Mapped[str | None] = mapped_column(Text)
    weather_restrictions: Mapped[str | None] = mapped_column(Text)
    pre_harvest_interval_days: Mapped[int | None] = mapped_column(Integer)
    source_file: Mapped[str | None] = mapped_column(String(250))
    source_page: Mapped[str | None] = mapped_column(String(120))
    verification_status: Mapped[str] = mapped_column(String(40), default="needs_review")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)


class IrrigationRule(Base):
    __tablename__ = "irrigation_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    crop_name: Mapped[str] = mapped_column(String(30), index=True)
    stage_name: Mapped[str | None] = mapped_column(String(120))
    soil_type: Mapped[str | None] = mapped_column(String(80))
    irrigation_method: Mapped[str | None] = mapped_column(String(80))
    amount_value: Mapped[float | None] = mapped_column(Float)
    amount_unit: Mapped[str | None] = mapped_column(String(40))
    trigger_description: Mapped[str | None] = mapped_column(Text)
    weather_constraints: Mapped[str | None] = mapped_column(Text)
    source_file: Mapped[str | None] = mapped_column(String(250))
    source_page: Mapped[str | None] = mapped_column(String(120))
    verification_status: Mapped[str] = mapped_column(String(40), default="needs_review")
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)


class WeatherRecord(Base):
    __tablename__ = "weather_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    farm_id: Mapped[int] = mapped_column(ForeignKey("farms.id"), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    temperature_c: Mapped[float | None] = mapped_column(Float)
    rainfall_mm: Mapped[float | None] = mapped_column(Float)
    humidity_percent: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str | None] = mapped_column(String(120))


class DailyTask(Base):
    __tablename__ = "daily_tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    crop_cycle_id: Mapped[int] = mapped_column(ForeignKey("crop_cycles.id"), index=True)
    task_date: Mapped[date] = mapped_column(Date, index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    source_rule_type: Mapped[str | None] = mapped_column(String(60))
    source_rule_id: Mapped[int | None] = mapped_column(Integer)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    weather_context: Mapped[dict | None] = mapped_column(
        JSON,
        default=lambda: {
            "status": "unavailable",
            "reason": "Weather context was not available during task generation.",
        },
    )


class TaskHistory(Base):
    __tablename__ = "task_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("daily_tasks.id"), index=True)
    action: Mapped[str] = mapped_column(String(40))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ImagePrediction(Base):
    __tablename__ = "image_predictions"
    id: Mapped[int] = mapped_column(primary_key=True)
    crop_cycle_id: Mapped[int | None] = mapped_column(ForeignKey("crop_cycles.id"))
    image_path: Mapped[str] = mapped_column(String(500))
    predicted_label: Mapped[str | None] = mapped_column(String(160))
    confidence: Mapped[float | None] = mapped_column(Float)
    model_version: Mapped[str | None] = mapped_column(String(80))
    task_id: Mapped[int | None] = mapped_column(ForeignKey("daily_tasks.id"))
    observation_id: Mapped[int | None] = mapped_column(ForeignKey("farmer_observations.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FarmerObservation(Base):
    __tablename__ = "farmer_observations"
    id: Mapped[int] = mapped_column(primary_key=True)
    crop_cycle_id: Mapped[int] = mapped_column(ForeignKey("crop_cycles.id"), index=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("daily_tasks.id"), index=True)
    note: Mapped[str] = mapped_column(Text)
    photo_reference: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AgriculturalSourceRecord(Base):
    __tablename__ = "agricultural_source_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_sources.id"), nullable=False, index=True
    )
    sheet_name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False)
    crop_name: Mapped[str | None] = mapped_column(String(120))
    problem_name: Mapped[str | None] = mapped_column(String(200))
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(30), default="needs_review", nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
