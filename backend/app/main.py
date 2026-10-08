from fastapi import FastAPI, HTTPException, Depends, Request
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone, timedelta
from .database import engine
from .models import User, RevokedToken, PasswordResetToken
from .schemas import (
    UserCreate,
    RegisterRequest,
    LoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from .rate_limit import check_rate_limit
from .auth import hash_password, verify_password
import os
import secrets
from dotenv import load_dotenv
from .jwt_utils import create_access_token
from .dependencies import get_current_user_id, get_current_token_payload

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
app = FastAPI()


@app.get("/")
def root():
    return {"message": "Project API is running!"}


@app.get("/db-test")
def db_test():
    try:
        with engine.connect():
            return {"database": "connected"}

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Database connection failed"
        )


@app.post("/users")
def create_user(user: UserCreate):
    with engine.connect() as connection:
        result = connection.execute(
            User.__table__.insert().values(name=user.name)
        )
        connection.commit()

        user_id = result.inserted_primary_key[0]

    return {
        "id": user_id,
        "name": user.name
    }

@app.get("/users")
def get_users():
    with engine.connect() as connection:
        result = connection.execute(
            User.__table__.select()
        )

        users = [
            {
                "id": row.id,
                "name": row.name
            }
            for row in result
        ]

    return users

@app.post("/auth/register")
def register(user: RegisterRequest):
    hashed_password = hash_password(user.password)

    try:
        with engine.begin() as connection:
            result = connection.execute(
                User.__table__.insert().values(
                    name=user.name,
                    email=user.email,
                    password_hash=hashed_password
                )
            )

            user_id = result.inserted_primary_key[0]

    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Email already exists"
        )

    return {
        "id": user_id,
        "name": user.name,
        "email": user.email
    }

@app.post("/auth/login")
def login(user: LoginRequest):
    with engine.connect() as connection:
        result = connection.execute(
            User.__table__.select().where(
                User.__table__.c.email == user.email
            )
        )

        db_user = result.fetchone()

    if db_user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not verify_password(user.password, db_user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    access_token = create_access_token(db_user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@app.get("/me")
def get_me(user_id: int = Depends(get_current_user_id)):
    with engine.connect() as connection:
        result = connection.execute(
            User.__table__.select().where(
                User.__table__.c.id == user_id
            )
        )
        db_user = result.fetchone()

    if db_user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return {
        "id": db_user.id,
        "name": db_user.name,
        "email": db_user.email
    }

@app.post("/auth/logout")
def logout(
    payload: dict = Depends(get_current_token_payload)
):
    jti = payload.get("jti")
    exp = payload.get("exp")

    if jti is None or exp is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    expires_at = datetime.fromtimestamp(
        exp,
        tz=timezone.utc
    )

    with engine.begin() as connection:
        result = connection.execute(
            RevokedToken.__table__.select().where(
                RevokedToken.__table__.c.jti == jti
            )
        )

        existing_token = result.fetchone()

        if existing_token is None:
            connection.execute(
                RevokedToken.__table__.insert().values(
                    jti=jti,
                    expires_at=expires_at
                )
            )

    return {
        "message": "Logged out successfully"
    }

@app.post("/auth/forgot-password")
def forgot_password(
    request: ForgotPasswordRequest,
    http_request: Request
):
    client_ip = http_request.client.host

    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many requests",
            headers={"Retry-After": "60"}
        )
    with engine.connect() as connection:
        result = connection.execute(
            User.__table__.select().where(
                User.__table__.c.email == request.email
            )
        )

        db_user = result.fetchone()

    if db_user is None:
        return {
            "message": "If the email exists, a password reset token will be created"
        }

    reset_token = secrets.token_urlsafe(32)

    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    with engine.begin() as connection:
        connection.execute(
            PasswordResetToken.__table__.delete().where(
                PasswordResetToken.__table__.c.user_id == db_user.id
            )
        )

        connection.execute(
            PasswordResetToken.__table__.insert().values(
                token=reset_token,
                user_id=db_user.id,
                expires_at=expires_at
            )
        )

    return {
        "message": "Password reset token created",
        "token": reset_token
    }

@app.post("/auth/reset-password")
def reset_password(request: ResetPasswordRequest):
    with engine.connect() as connection:
        result = connection.execute(
            PasswordResetToken.__table__.select().where(
                PasswordResetToken.__table__.c.token == request.token
            )
        )

        reset_token = result.fetchone()

    if reset_token is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset token"
        )

    if reset_token.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset token"
        )

    hashed_password = hash_password(request.new_password)

    with engine.begin() as connection:
        connection.execute(
            User.__table__.update()
            .where(User.__table__.c.id == reset_token.user_id)
            .values(password_hash=hashed_password)
        )

        connection.execute(
            PasswordResetToken.__table__.delete()
            .where(
                PasswordResetToken.__table__.c.id == reset_token.id
            )
        )

    return {
        "message": "Password reset successfully"
    }