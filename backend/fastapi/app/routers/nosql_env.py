from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from models.mcp_nosql import EnvUpdate
from routers.nosql_auth import get_current_user
import crud.nosql as nosql_crud

router = APIRouter(
    prefix="/env",
    tags=["환경 변수"],
    responses={404: {"description": "Not found"}}
)

@router.post("/", response_model=Dict[str, Any])
async def update_env_variable(env_update: EnvUpdate, current_user: dict = Depends(get_current_user)):
    """사용자의 MCP 환경 변수를 업데이트합니다."""
    result = await nosql_crud.update_env_var(str(current_user["_id"]), env_update)
    return result

@router.get("/{public_id}", response_model=Dict[str, Any])
async def get_env_variable(public_id: str, current_user: dict = Depends(get_current_user)):
    """특정 MCP에 대한 사용자의 환경 변수를 조회합니다."""
    env_var = await nosql_crud.get_env_vars(str(current_user["_id"]), public_id)
    if not env_var:
        raise HTTPException(status_code=404, detail="환경 변수를 찾을 수 없습니다.")
    return {"public_id": public_id, "env_settings": env_var}

@router.get("/", response_model=Dict[str, Any])
async def get_all_env_variables(current_user: dict = Depends(get_current_user)):
    """사용자의 모든 환경 변수를 조회합니다."""
    env_vars = await nosql_crud.get_env_vars(str(current_user["_id"]))
    return {"env_settings": env_vars}

@router.delete("/{public_id}", response_model=Dict[str, Any])
async def delete_env_variable(public_id: str, current_user: dict = Depends(get_current_user)):
    """사용자의 MCP 환경 변수를 삭제합니다."""
    success = await nosql_crud.delete_env_var(str(current_user["_id"]), public_id)
    if not success:
        raise HTTPException(status_code=404, detail="환경 변수를 찾을 수 없습니다.")
    return {"success": True}
