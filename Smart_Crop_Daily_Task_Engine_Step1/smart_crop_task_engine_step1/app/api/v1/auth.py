import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import (
    ACCESS_TOKEN_MINUTES,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models import Farmer
from app.schemas.auth import FarmerProfile, FarmerRegister, TokenResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_farmer(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Farmer:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired access token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        farmer_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise credentials_error from exc

    farmer = db.get(Farmer, farmer_id)
    if farmer is None:
        raise credentials_error
    return farmer


@router.post(
    "/register",
    response_model=FarmerProfile,
    status_code=status.HTTP_201_CREATED,
)
def register_farmer(payload: FarmerRegister, db: Session = Depends(get_db)):
    phone = payload.phone.strip()
    if not phone:
        raise HTTPException(status_code=422, detail="Phone number is required.")

    existing = db.scalar(select(Farmer.id).where(Farmer.phone == phone))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Phone number is already registered.")

    farmer = Farmer(
        full_name=payload.full_name.strip(),
        phone=phone,
        preferred_language=payload.preferred_language,
        password_hash=hash_password(payload.password),
    )
    db.add(farmer)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="Phone number is already registered."
        ) from exc
    db.refresh(farmer)
    return farmer


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    phone = form_data.username.strip()
    farmer = db.scalar(select(Farmer).where(Farmer.phone == phone))
    if (
        farmer is None
        or farmer.password_hash is None
        or not verify_password(form_data.password, farmer.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect phone number or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenResponse(
        access_token=create_access_token(farmer.id),
        expires_in=ACCESS_TOKEN_MINUTES * 60,
    )


@router.get("/me", response_model=FarmerProfile)
def read_current_farmer(
    current_farmer: Farmer = Depends(get_current_farmer),
):
    return current_farmer
