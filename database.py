from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")

print(f"DATABASE_URL from env: {DATABASE_URL[:50] if DATABASE_URL else 'Not set'}...")

if not DATABASE_URL:
    DB_TYPE = os.getenv("DB_TYPE", "sqlite")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "wiki_quiz")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    if DB_TYPE == "mysql":
        DATABASE_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    elif DB_TYPE == "postgresql":
        DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"
    else:
        DATABASE_URL = "sqlite:///./wiki_quiz.db"
    print(f"Built DATABASE_URL from env vars: {DATABASE_URL[:50]}...")

# Create engine - sslmode is already in the URL for Neon PostgreSQL
if DATABASE_URL.startswith("postgresql"):
    print("🐘 Connecting to PostgreSQL (Neon)...")
    engine = create_engine(DATABASE_URL)
else:
    print("📁 Using SQLite database...")
    engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()