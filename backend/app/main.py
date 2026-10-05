from fastapi import FastAPI
from .database import engine
from .models import User
from .schemas import UserCreate

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Project API is running!"}


@app.get("/db-test")
def db_test():
    try:
        with engine.connect():
            return {"database": "connected"}
    except Exception as e:
        return {"database": "error", "detail": str(e)}


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