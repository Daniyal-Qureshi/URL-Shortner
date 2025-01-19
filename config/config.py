from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from requests import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging
import os

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
SECRET_KEY = os.getenv("SECRET_KEY", "secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
REDIRECT_URL = os.getenv("REDIRECT_URL", "http://localhost:8000")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Configure logging
logger = logging.getLogger("app")
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler("QED.log")
fh.setLevel(logging.ERROR)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
fh.setFormatter(formatter)
ch.setFormatter(formatter)

logger.addHandler(fh)
logger.addHandler(ch)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
