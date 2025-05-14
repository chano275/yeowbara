from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from routers.nosql_auth import get_current_user
import crud.nosql as nosql_crud

router = APIRouter(
    prefix="/select",
    tags=["MCP 선택"],
    responses={404: {"description": "Not found"}}
)

@router.post("/{public_id}", response_model=Dict[str, Any])
async def select_mcp(public_id: str, current_user: dict = Depends(get_current_user)):
    """사용자가 MCP를 선택합니다."""
    result = await nosql_crud.select_mcp_for_user(str(current_user["_id"]), public_id)
    return result

@router.get("/", response_model=List[Dict[str, Any]])
async def get_selected_mcps(current_user: dict = Depends(get_current_user)):
    """사용자가 선택한 모든 MCP를 조회합니다."""
    selected_mcps = await nosql_crud.get_user_selected_mcps(str(current_user["_id"]))
    
    # UUID 등 내부 ID 삭제 및 공개 ID만 반환
    for mcp in selected_mcps:
        if "id" in mcp:
            del mcp["id"]
    
    return selected_mcps

@router.delete("/{public_id}", response_model=Dict[str, Any])
async def deselect_mcp(public_id: str, current_user: dict = Depends(get_current_user)):
    """사용자의 MCP 선택을 취소합니다."""
    success = await nosql_crud.deselect_mcp(str(current_user["_id"]), public_id)
    if not success:
        raise HTTPException(status_code=404, detail="선택된 MCP를 찾을 수 없습니다.")
    return {"success": True}
