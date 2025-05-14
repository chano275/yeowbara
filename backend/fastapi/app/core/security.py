from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
from core.config import settings

# bcrypt 버전 오류 해결
import bcrypt
import sys
sys.modules['bcrypt.__about__'] = type('obj', (object,), {
    '__version__': bcrypt.__version__
})

# 보안 설정
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# 패스워드 해싱 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def get_password_hash(password):
    """비밀번호를 해싱합니다."""
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    """비밀번호가 해시와 일치하는지 검증합니다."""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """JWT 액세스 토큰을 생성합니다."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
