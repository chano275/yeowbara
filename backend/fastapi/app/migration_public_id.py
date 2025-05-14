"""
이 스크립트는 기존의 MCP 문서들에 public_id 필드를 추가합니다.
"""
import asyncio
import random
import string
import os
from motor.motor_asyncio import AsyncIOMotorClient
from bson.codec_options import CodecOptions
from bson.binary import UuidRepresentation

# MongoDB 연결 설정
MONGO_URI = os.getenv("MONGODB_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME")

# 코덱 옵션 설정
codec_options = CodecOptions(uuid_representation=UuidRepresentation.STANDARD)

# 공개 ID 생성 함수
def generate_public_id(prefix="mcp_", length=6):
    """지정된 길이의 난수 문자열을 생성합니다."""
    chars = string.ascii_lowercase + string.digits
    random_str = ''.join(random.choice(chars) for _ in range(length))
    return f"{prefix}{random_str}"

async def migrate_public_id():
    # 데이터베이스 연결
    client = AsyncIOMotorClient(MONGO_URI)
    db = client[DATABASE_NAME]
    mcps = db.get_collection("mcps_nosql", codec_options=codec_options)
    
    # 공개 ID가 없는 모든 MCP 조회
    mcps_without_public_id = await mcps.find({"public_id": {"$exists": False}}).to_list(length=1000)
    
    print(f"총 {len(mcps_without_public_id)}개의 MCP에 public_id를 추가합니다.")
    
    # 각 MCP에 고유한 public_id 추가
    for mcp in mcps_without_public_id:
        while True:
            # 고유한 public_id 생성
            public_id = generate_public_id()
            
            # 이미 존재하는 public_id인지 확인
            existing = await mcps.find_one({"public_id": public_id})
            if not existing:
                break
        
        # public_id 업데이트
        await mcps.update_one(
            {"_id": mcp["_id"]},
            {"$set": {"public_id": public_id}}
        )
        print(f"MCP '{mcp.get('name', str(mcp['_id']))}' 에 public_id '{public_id}'를 추가했습니다.")
    
    # 인덱스 생성 시도
    try:
        await mcps.create_index("public_id", unique=True)
        print("public_id에 유니크 인덱스를 생성했습니다.")
    except Exception as e:
        print(f"인덱스 생성 중 오류 발생: {e}")
    
    # 연결 종료
    client.close()
    print("마이그레이션이 완료되었습니다.")

if __name__ == "__main__":
    asyncio.run(migrate_public_id())
