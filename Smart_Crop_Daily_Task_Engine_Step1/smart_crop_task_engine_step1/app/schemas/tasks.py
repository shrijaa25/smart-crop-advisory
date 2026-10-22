from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class DailyTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    crop_cycle_id: int
    task_date: date
    title: str
    description: str | None = None
    status: str
    source_rule_type: str | None = None
    source_rule_id: int | None = None
    completed_at: datetime | None = None
    weather_context: dict | None = None


class GenerateTasksResponse(BaseModel):
    target_date: date
    tasks_created: int
    fertilizer_review_alerts_created: int = 0
    message: str
