from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from typing import Dict, Any
from models.mcp_nosql import UserCreate, User, Token, PasswordChange
from routers.nosql_auth import get_current_user, get_admin_user
from core.security import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from core.password_validator import validate_password
import crud.nosql as nosql_crud
import os
import httpx
import logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/users",
    tags=["사용자"],
    responses={401: {"description": "인증되지 않음"}}
)

@router.post("/signup", response_model=User)
async def signup(user: UserCreate):
    """새로운 사용자를 등록합니다."""
    # 비밀번호 유효성 검사
    is_valid, error_message = validate_password(user.password)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=error_message
        )
        
    db_user = await nosql_crud.create_user(user)
    if db_user is None:
        raise HTTPException(
            status_code=400, 
            detail="이미 사용 중인 아이디 또는 이메일입니다"
        )
    
    return {
        "id": str(db_user["_id"]), 
        "username": db_user["username"], 
        "email": db_user["email"],
        "is_admin": db_user.get("is_admin", False)
    }

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """로그인하고 액세스 토큰을 발급합니다."""
    # OAuth2PasswordRequestForm은 username 필드를 사용하지만 이메일로 간주함
    user = await nosql_crud.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"]}, # username 대신 email 사용
        expires_delta=access_token_expires
    )

    ##################### Pod 생성 호출 #####################
    # 사용자 정보
    user_id = str(user["_id"])
    
    # Pod 생성 함수 호출
    from core.create_pod import create_pod
    try:
        # user_id만 전달하여 Pod 생성 함수 호출
        pod_result = await create_pod(user_id)
        
        if pod_result.get("success", False):
            logger.info(f"Pod 생성 성공 - 사용자: {user_id}, Pod: {pod_result.get('pod_name')}")
        else:
            logger.warning(f"Pod 생성 실패 - 사용자: {user_id}, 오류: {pod_result.get('message')}")
    
    except Exception as e:
        # Pod 생성 오류가 로그인을 방해하지 않도록 예외 처리
        logger.error(f"Pod 생성 중 예외 발생 - 사용자: {user_id}, 오류: {str(e)}")
    ##################### Pod 생성 호출 #####################
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=User)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    """현재 인증된 사용자의 정보를 조회합니다."""
    return {
        "id": current_user["_id"], 
        "username": current_user["username"], 
        "email": current_user["email"],
        "is_admin": current_user.get("is_admin", False),
        "selected_mcps":current_user.get("selected_mcps",[])
    }

@router.delete("/me", response_model=Dict[str, Any])
async def delete_current_user(current_user: dict = Depends(get_current_user)):
    """현재 인증된 사용자를 삭제합니다."""
    user_id = str(current_user["_id"])
    success = await nosql_crud.delete_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자 삭제 중 오류가 발생했습니다"
        )
    
    return {"success": True, "message": "사용자가 성공적으로 삭제되었습니다"}

@router.put("/change-password", response_model=Dict[str, Any])
async def change_password(password_data: PasswordChange, current_user: dict = Depends(get_current_user)):
    """로그인한 사용자의 비밀번호를 변경합니다."""
    # 새 비밀번호 유효성 검사
    is_valid, error_message = validate_password(password_data.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=error_message
        )
        
    user_id = str(current_user["_id"])
    result = await nosql_crud.change_user_password(
        user_id, 
        password_data.current_password, 
        password_data.new_password
    )
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    
    return result

@router.delete("/{user_id}", response_model=Dict[str, Any])
async def delete_user_by_id(user_id: str, _: dict = Depends(get_admin_user)):
    """특정 사용자를 삭제합니다. (관리자 권한 필요)"""
    # 사용자 존재 확인
    user = await nosql_crud.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다"
        )
    
    success = await nosql_crud.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자 삭제 중 오류가 발생했습니다"
        )
    
    return {"success": True, "message": "사용자가 성공적으로 삭제되었습니다"}
