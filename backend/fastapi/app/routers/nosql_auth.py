from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Dict, Any, Optional
from jose import jwt, JWTError
from core.security import SECRET_KEY, ALGORITHM
import crud.nosql as nosql_crud

router = APIRouter(
    tags=["인증"],
    responses={401: {"description": "인증되지 않음"}}
)

# /users/login 경로로 변경
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")

# 인증 관련 함수
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """현재 인증된 사용자 정보를 가져옵니다."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보가 유효하지 않습니다",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await nosql_crud.get_user_by_email(email)
    if user is None:
        raise credentials_exception
    
    return user

async def get_admin_user(current_user: dict = Depends(get_current_user)):
    """관리자 권한이 있는 사용자를 확인합니다."""
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="이 작업을 수행하기 위한 권한이 없습니다"
        )
    return current_user
