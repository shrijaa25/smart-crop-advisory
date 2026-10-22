from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.auth import get_current_farmer
from app.db.session import get_db
from app.models import CropCycle, Farm, Farmer
from app.schemas.farms import CropCycleCreate, CropCycleOut, FarmCreate, FarmOut

router = APIRouter(tags=["Farms and Crops"])


def _owned_farm(db: Session, farm_id: int, farmer_id: int) -> Farm:
    farm = db.scalar(
        select(Farm).where(Farm.id == farm_id, Farm.farmer_id == farmer_id)
    )
    if farm is None:
        raise HTTPException(status_code=404, detail="Farm not found.")
    return farm


@router.post("/farms", response_model=FarmOut, status_code=status.HTTP_201_CREATED)
def create_farm(
    payload: FarmCreate,
    farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    farm = Farm(farmer_id=farmer.id, **payload.model_dump())
    db.add(farm)
    db.commit()
    db.refresh(farm)
    return farm


@router.get("/farms", response_model=list[FarmOut])
def list_farms(
    farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(Farm).where(Farm.farmer_id == farmer.id).order_by(Farm.id)
    ).all()


@router.post(
    "/farms/{farm_id}/crops",
    response_model=CropCycleOut,
    status_code=status.HTTP_201_CREATED,
)
def create_crop_cycle(
    farm_id: int,
    payload: CropCycleCreate,
    farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    _owned_farm(db, farm_id, farmer.id)
    crop_cycle = CropCycle(farm_id=farm_id, **payload.model_dump())
    db.add(crop_cycle)
    db.commit()
    db.refresh(crop_cycle)
    return crop_cycle


@router.get("/farms/{farm_id}/crops", response_model=list[CropCycleOut])
def list_farm_crop_cycles(
    farm_id: int,
    farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    _owned_farm(db, farm_id, farmer.id)
    return db.scalars(
        select(CropCycle)
        .where(CropCycle.farm_id == farm_id)
        .order_by(CropCycle.planting_date.desc(), CropCycle.id)
    ).all()


@router.get("/crop-cycles", response_model=list[CropCycleOut])
def list_crop_cycles(
    farmer: Farmer = Depends(get_current_farmer),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(CropCycle)
        .join(Farm, CropCycle.farm_id == Farm.id)
        .where(Farm.farmer_id == farmer.id)
        .order_by(CropCycle.planting_date.desc(), CropCycle.id)
    ).all()
