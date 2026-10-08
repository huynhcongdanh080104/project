from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .database import engine
from .models import RevokedToken
from .jwt_utils import decode_access_token


security = HTTPBearer()

def get_current_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    try:
        return decode_access_token(credentials.credentials)

    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> int:
    try:
        payload = decode_access_token(credentials.credentials)

        user_id = payload.get("sub")
        jti = payload.get("jti")

        if user_id is None or jti is None:
            raise ValueError("Invalid token")

        with engine.connect() as connection:
            result = connection.execute(
                RevokedToken.__table__.select().where(
                    RevokedToken.__table__.c.jti == jti
                )
            )

            revoked_token = result.fetchone()

        if revoked_token is not None:
            raise ValueError("Token has been revoked")

        return int(user_id)

    except (ValueError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )