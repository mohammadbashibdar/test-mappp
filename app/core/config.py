from fastapi import HTTPException, status, Depends
from pydantic_settings import BaseSettings
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Annotated, ClassVar
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "map-game Backend FastAPI"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/motor_backend"
    
    
    class Config:
        env_file = ".env"

settings = Settings()

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)
