from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict, Any
from models.mcp_nosql import MCPCreate, MCPUpdate
from routers.nosql_auth import get_current_user, get_admin_user
import crud.nosql as nosql_crud

router = APIRouter(
    prefix="/mcps",
    tags=["MCP"],
    responses={404: {"description": "Not found"}}
)

@router.post("/", response_model=Dict[str, Any])
async def create_mcp(mcp: MCPCreate, _: dict = Depends(get_admin_user)):
    """새 MCP를 생성합니다. (관리자 권한 필요)"""
    mcp_data = await nosql_crud.create_mcp(mcp)
    if not mcp_data:
        raise HTTPException(status_code=400, detail="MCP 생성에 실패했습니다.")
    return {
        "success": True,
        "public_id": mcp_data["public_id"]
    }

@router.get("/", response_model=List[Dict[str, Any]])
async def read_mcps(current_user: dict = Depends(get_current_user)):
    """모든 MCP를 조회합니다. 로그인한 사용자가 선택한 MCP는 is_selected 필드가 true로 표시됩니다."""
    # 모든 MCP 조회
    mcps = await nosql_crud.get_all_mcps()
    
    # 사용자가 선택한 MCP 정보 조회
    selected_mcps = await nosql_crud.get_user_selected_mcps(str(current_user["_id"]))
    selected_mcp_public_ids = [mcp["public_id"] for mcp in selected_mcps if "public_id" in mcp]
    
    result = []
    for mcp in mcps:
        # MCP public_id가 사용자가 선택한 MCP 목록에 있는지 확인
        is_selected = mcp.get("public_id", "") in selected_mcp_public_ids
        
        result.append({
            "public_id": mcp.get("public_id", ""),
            "name": mcp["name"],
            "mcp_type": mcp.get("mcp_type", ""),
            "description": mcp.get("description", ""),
            "required_env_vars": mcp.get("required_env_vars", []),
            # "env_vars_count": len(mcp.get("required_env_vars", [])),
            "is_selected": is_selected  # 사용자가 선택한 MCP인지 여부
        })
    return result

@router.get("/{public_id}", response_model=Dict[str, Any])
async def read_mcp(public_id: str):
    """특정 MCP를 공개 ID로 조회합니다."""
    mcp = await nosql_crud.get_mcp(public_id)
    if not mcp:
        raise HTTPException(status_code=404, detail="MCP를 찾을 수 없습니다.")
    
    return {
        "public_id": mcp.get("public_id", ""),
        "name": mcp["name"],
        "description": mcp.get("description", ""),
        "script": mcp.get("script"),
        "mcp_type": mcp.get("mcp_type", ""),
        "required_env_vars": mcp.get("required_env_vars", []),
        "created_at": mcp.get("created_at", "").isoformat() if mcp.get("created_at") else None,
        "updated_at": mcp.get("updated_at", "").isoformat() if mcp.get("updated_at") else None
    }

@router.put("/{public_id}", response_model=Dict[str, Any])
async def update_mcp(public_id: str, mcp_data: MCPUpdate, _: dict = Depends(get_admin_user)):
    """MCP 정보를 업데이트합니다. (관리자 권한 필요)"""
    success = await nosql_crud.update_mcp(public_id, mcp_data)
    if not success:
        raise HTTPException(status_code=404, detail="MCP를 찾을 수 없습니다.")
    return {"success": True}

@router.delete("/{public_id}", response_model=Dict[str, Any])
async def delete_mcp(public_id: str, _: dict = Depends(get_admin_user)):
    """MCP를 삭제합니다. (관리자 권한 필요)"""
    success = await nosql_crud.delete_mcp(public_id)
    if not success:
        raise HTTPException(status_code=404, detail="MCP를 찾을 수 없습니다.")
    return {"success": True}
