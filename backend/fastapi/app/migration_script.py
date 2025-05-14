import asyncio
from bson import ObjectId
from core.database import async_db
from datetime import datetime

# 컬렉션 정의
users = async_db["users_nosql"]
mcps = async_db["mcps_nosql"]

async def migrate_mcp_data():
    """
    기존 데이터 구조에서 새 데이터 구조로 마이그레이션합니다.
    기존: selected_mcps 배열에 MCP ID 문자열만 저장
    새로운 구조: selected_mcps 배열에 {id, name, description, selected_at} 객체 저장
    """
    print("MCP 데이터 마이그레이션을 시작합니다...")
    
    # 모든 사용자 조회
    all_users = await users.find({}).to_list(length=1000)
    
    update_count = 0
    for user in all_users:
        # 사용자가 선택한 MCP 목록이 있는지 확인
        if "selected_mcps" in user and isinstance(user["selected_mcps"], list) and user["selected_mcps"]:
            
            # ID 목록에서 객체 목록으로 변환해야 하는지 확인
            if all(isinstance(item, str) for item in user["selected_mcps"]):
                print(f"사용자 {user['username']}의 데이터를 마이그레이션합니다...")
                
                # MCP ID 목록
                mcp_ids = user["selected_mcps"]
                new_selected_mcps = []
                
                # 각 MCP ID에 대해 추가 정보 조회 및 객체 생성
                for mcp_id in mcp_ids:
                    try:
                        mcp = await mcps.find_one({"_id": ObjectId(mcp_id)})
                        if mcp:
                            mcp_info = {
                                "id": mcp_id,
                                "name": mcp.get("name", "알 수 없는 MCP"),
                                "description": mcp.get("description", ""),
                                "selected_at": datetime.utcnow()  # 기존 선택 시간 정보가 없으므로 현재 시간 사용
                            }
                            new_selected_mcps.append(mcp_info)
                    except Exception as e:
                        print(f"MCP ID {mcp_id} 처리 중 오류 발생: {e}")
                
                # 사용자 정보 업데이트
                if new_selected_mcps:
                    await users.update_one(
                        {"_id": user["_id"]},
                        {"$set": {"selected_mcps": new_selected_mcps}}
                    )
                    update_count += 1
    
    print(f"마이그레이션 완료: {update_count}명의 사용자 데이터를 업데이트했습니다.")

# 스크립트 실행
if __name__ == "__main__":
    asyncio.run(migrate_mcp_data())
