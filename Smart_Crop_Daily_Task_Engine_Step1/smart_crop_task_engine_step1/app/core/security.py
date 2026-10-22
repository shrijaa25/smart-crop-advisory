import secrets
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from pwdlib import PasswordHash

# Load the ignored local .env before reading the application settings.
load_dotenv()

from app.core.config import settings

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 15
_password_hash = PasswordHash.recommended()


def get_jwt_secret() -> str:
    secret = settings.jwt_secret_key
    if len(secret) < 32:
        raise RuntimeError(
            "JWT_SECRET_KEY must be configured with a strong secret "
            "of at least 32 characters."
        )
    return secret


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)


def create_access_token(farmer_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(farmer_id),
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
        "jti": secrets.token_urlsafe(16),
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        get_jwt_secret(),
        algorithms=[JWT_ALGORITHM],
        options={"require": ["sub", "iat", "exp", "jti"]},
    )
