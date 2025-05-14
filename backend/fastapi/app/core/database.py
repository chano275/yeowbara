from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from core.config import settings
from bson.codec_options import CodecOptions
from bson.binary import UuidRepresentation

# MongoDB UUID 표현 방식 설정
codec_options = CodecOptions(uuid_representation=UuidRepresentation.STANDARD)
# MongoDB 연결 설정
MONGO_URI = settings.MONGODB_URL
DATABASE_NAME = settings.DATABASE_NAME

# 기본 추가 설정
client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME].with_options(codec_options)

# 비동기식 클라이언트
async_client = AsyncIOMotorClient(MONGO_URI)
async_db = async_client[DATABASE_NAME]

# 컬렉션 정의
users_collection = db["users"]
async_users_collection = async_db["users"]

# MCP 관련 컬렉션
mcps_collection = db["mcps"]
async_mcps_collection = async_db["mcps"]

mcp_manuals_collection = db["mcp_manuals"]
async_mcp_manuals_collection = async_db["mcp_manuals"]

mcp_scripts_collection = db["mcp_scripts"]
async_mcp_scripts_collection = async_db["mcp_scripts"]

envs_collection = db["envs"]
async_envs_collection = async_db["envs"]

select_mcps_collection = db["select_mcps"]
async_select_mcps_collection = async_db["select_mcps"]

# 대화 관련 컨렉션
conversations_collection = db["conversations"]
async_conversations_collection = async_db["conversations"]

# 데이터베이스 연결을 반환하는 함수
def get_database():
    """MongoDB 비동기 데이터베이스 연결을 반환합니다."""
    return async_db

# 인덱스 생성 함수
async def create_indexes():
    # mcp_manuals, mcp_scripts의 mcp_id에 유니크 인덱스 생성 (1:1 관계 강제)
    await async_mcp_manuals_collection.create_index("mcp_id", unique=True)
    await async_mcp_scripts_collection.create_index("mcp_id", unique=True)
    
    # envs의 user_id+mcp_id에 복합 인덱스 생성
    await async_envs_collection.create_index([("user_id", 1), ("mcp_id", 1)], unique=True)
    
    # select_mcps의 user_id+mcp_id에 복합 인덱스 생성
    await async_select_mcps_collection.create_index([("user_id", 1), ("mcp_id", 1)], unique=True)
    
    # conversations에 user_id 인덱스 생성 (대화 히스토리 조회 최적화)
    await async_conversations_collection.create_index("user_id")
    await async_conversations_collection.create_index([("user_id", 1), ("timestamp", -1)])  # 사용자별 + 시간순
