from sqlalchemy import create_engine

from .models import Base

DATABASE_URL = "postgresql+psycopg://admin:admin@localhost:5432/project_db"

engine = create_engine(DATABASE_URL)