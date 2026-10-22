from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.v1.auth import router as auth_router, get_current_farmer
from app.api.v1.tasks import router as tasks_router
from app.api.v1.farms import router as farms_router
from app.models import (
    CropStageRule,
    DiseasePestRule,
    FertilizerRule,
    IrrigationRule,
    KnowledgeSource,
    Farmer,
)
from app.api.v1.excel_knowledge import router as excel_knowledge_router
from app.api.v1.weather import router as weather_router
from app.api.v1.disease import router as disease_router
from app.schemas.knowledge import (
    FertilizerRuleCreate,
    FertilizerRuleOut,
    KnowledgeSourceCreate,
    KnowledgeSourceOut,
)

router = APIRouter()
router.include_router(auth_router)
router.include_router(tasks_router)
router.include_router(farms_router)
router.include_router(excel_knowledge_router)
router.include_router(weather_router)
router.include_router(disease_router)
SUPPORTED_CROPS = {"tomato", "chilli"}


def validate_crop(crop: str | None) -> None:
    if crop is not None and crop not in SUPPORTED_CROPS:
        raise HTTPException(status_code=400, detail="Unsupported crop. Use tomato or chilli.")


@router.get("/knowledge/summary")
def knowledge_summary(db: Session = Depends(get_db)):
    return {
        "supported_crops": ["tomato", "chilli"],
        "database": "SQLite",
        "tables": {
            "knowledge_sources": db.query(KnowledgeSource).count(),
            "crop_stage_rules": db.query(CropStageRule).count(),
            "fertilizer_rules": db.query(FertilizerRule).count(),
            "disease_pest_rules": db.query(DiseasePestRule).count(),
            "irrigation_rules": db.query(IrrigationRule).count(),
        },
    }


@router.post("/knowledge/sources", response_model=KnowledgeSourceOut, status_code=status.HTTP_201_CREATED)
def create_knowledge_source(payload: KnowledgeSourceCreate, farmer: Farmer = Depends(get_current_farmer), db: Session = Depends(get_db)):
    values = payload.model_dump()
    values["verification_status"] = "needs_review"
    source = KnowledgeSource(**values)
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.get("/knowledge/sources", response_model=list[KnowledgeSourceOut])
def list_knowledge_sources(db: Session = Depends(get_db)):
    return db.query(KnowledgeSource).order_by(KnowledgeSource.id).all()


@router.get("/knowledge/fertilizer-rules", response_model=list[FertilizerRuleOut])
def list_fertilizer_rules(
    crop: str | None = Query(default=None), db: Session = Depends(get_db)
):
    validate_crop(crop)
    query = db.query(FertilizerRule)
    if crop:
        query = query.filter(FertilizerRule.crop_name == crop)
    return query.order_by(FertilizerRule.id).all()


@router.post("/knowledge/fertilizer-rules", response_model=FertilizerRuleOut, status_code=status.HTTP_201_CREATED)
def create_fertilizer_rule(payload: FertilizerRuleCreate, farmer: Farmer = Depends(get_current_farmer), db: Session = Depends(get_db)):
    values = payload.model_dump()
    values["verification_status"] = "needs_review"
    values["is_active"] = False
    rule = FertilizerRule(**values)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule
