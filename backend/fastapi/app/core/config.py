import json
from pydantic import Field
from pydantic_settings import BaseSettings
from typing import List
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class Settings(BaseSettings):
    # MongoDB 설정
    MONGODB_URL: str = os.getenv("MONGODB_URL")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME")
    MONGO_DB_USER_NAME: str = os.getenv("MONGO_DB_USER_NAME")
    MONGO_DB_PASSWORD: str = os.getenv("MONGO_DB_PASSWORD")
    
    # JWT 설정
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    ALGORITHM: str = os.getenv("ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))
    
    # API 암호화
    API_SECRET_KEY: str = os.getenv("API_SECRET_KEY")

    # POD 생성 URL
    DEPLOY_SERVER_URL: str = os.getenv("DEPLOY_SERVER_URL")

    # GMS API KEY
    GMS_API_KEY: str = os.getenv("GMS_API_KEY")

    # OPEN API KEY
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")

    # AGENT
    AGENT_URL: str = os.getenv("AGENT_URL")

    # CORS 설정
    CORS_ORIGINS: List[str] = Field(
    default_factory=lambda: json.loads(os.getenv("CORS_ORIGINS", "[]"))
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"

# 설정 인스턴스 생성
settings = Settings()
