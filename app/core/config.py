from fastapi import HTTPException, status, Depends
from pydantic_settings import BaseSettings
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Annotated, ClassVar, Dict
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "GIS Map Game Backend FastAPI"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/gis_backend")
    # تنظیمات برای داده‌های خلیج فارس
    PERSIAN_GULF_BOUNDS: Dict[str, float] = {
        "minx": 48.0,  # غربی‌ترین نقطه
        "miny": 24.0,  # جنوبی‌ترین نقطه  
        "maxx": 60.0,  # شرقی‌ترین نقطه
        "maxy": 31.0   # شمالی‌ترین نقطه
    }
    DEFAULT_CRS: str = "EPSG:4326"
    TILE_CRS: str = "EPSG:3857"
    
    
    class Config:
        env_file = ".env"

settings = Settings()

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)
