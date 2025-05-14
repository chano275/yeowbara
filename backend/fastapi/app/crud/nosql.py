from datetime import datetime
from typing import List, Dict, Any, Optional
import uuid
import random
import string
import os
from cryptography.fernet import Fernet
from base64 import urlsafe_b64encode
import hashlib
from models.mcp_nosql import UserCreate, MCPCreate, MCPUpdate, EnvUpdate
from core.security import get_password_hash, verify_password
from core.database import async_db, codec_options
from core.config import settings

# 공개 ID 생성 함수
def generate_public_id(prefix="mcp_", length=6):
    """지정된 길이의 난수 문자열을 생성합니다."""
    chars = string.ascii_lowercase + string.digits
    random_str = ''.join(random.choice(chars) for _ in range(length))
    return f"{prefix}{random_str}"

# 환경변수 암호화를 위한 함수
def get_encryption_key(api_secret_key):
    """
    API_SECRET_KEY를 사용하여 Fernet 암호화에 사용할 32바이트 키를 생성합니다.
    API_SECRET_KEY가 짧은 경우에도 안전한 키를 생성합니다.
    """
    # API_SECRET_KEY를 SHA-256으로 해시하여 32바이트 값을 생성
    hashed_key = hashlib.sha256(api_secret_key.encode()).digest()
    # base64 인코딩하여 Fernet에서 사용 가능한 형식으로 변환
    return urlsafe_b64encode(hashed_key)

# 환경변수에서 API_SECRET_KEY 가져오기
def get_api_secret_key():
    """환경변수에서 API_SECRET_KEY 가져오기"""
    api_secret_key = settings.API_SECRET_KEY
    if not api_secret_key:
        raise ValueError("API_SECRET_KEY 환경변수가 설정되지 않았습니다.")
    return api_secret_key

# 암호화 함수
def encrypt_value(value: str):
    """문자열을 암호화합니다."""
    try:
        if not value:  # None 또는 빈 문자열은 암호화하지 않음
            return value
            
        api_secret_key = get_api_secret_key()
        key = get_encryption_key(api_secret_key)
        cipher = Fernet(key)
        encrypted_value = cipher.encrypt(value.encode())
        return encrypted_value.decode()
    except Exception as e:
        print(f"값 암호화 중 오류: {e}")
        # 오류 발생 시 원본 값 반환 (암호화 실패)
        return value

# 복호화 함수
def decrypt_value(encrypted_value: str):
    """암호화된 문자열을 복호화합니다."""
    try:
        if not encrypted_value:  # None 또는 빈 문자열은 복호화하지 않음
            return encrypted_value
            
        api_secret_key = get_api_secret_key()
        key = get_encryption_key(api_secret_key)
        cipher = Fernet(key)
        # 주어진 값이 이미 암호화되어 있는지 확인
        try:
            decrypted_value = cipher.decrypt(encrypted_value.encode())
            return decrypted_value.decode()
        except Exception:
            # 복호화 오류는 암호화되지 않은 값일 수 있으므로 원본 반환
            return encrypted_value
    except Exception as e:
        print(f"값 복호화 중 오류: {e}")
        # 오류 발생 시 원본 값 반환 (복호화 실패)
        return encrypted_value

# 컬렉션 정의
users = async_db.get_collection("users_nosql", codec_options=codec_options)
mcps = async_db.get_collection("mcps_nosql", codec_options=codec_options)
# 대화 컬렉션 추가
conversations = async_db.get_collection("conversations", codec_options=codec_options)

# MongoDB는 컬렉션이 없으면 자동으로 생성하므로 미리 만들 필요 없음

# 인덱스 생성 함수
async def create_nosql_indexes():
    # 사용자 인덱스
    await users.create_index("username", unique=True)
    await users.create_index("email", unique=True)
    
    # MCP 인덱스
    await mcps.create_index("name")
    # 처음 실행 시에는 public_id 인덱스를 생성하지 않음
    # 메인 파일에서 성공적으로 서버를 시작한 후
    # migration_public_id.py 스크립트를 실행하여 값을 추가하고 인덱스를 생성해야 함
    # await mcps.create_index("public_id", unique=True)  # 공개 ID에 유니크 인덱스 추가
    
    # 대화 인덱스 추가
    await conversations.create_index("user_id")
    await conversations.create_index([("user_id", 1), ("updated_at", -1)])

# ======== 사용자 관련 CRUD ========

async def get_user_by_username(username: str):
    """사용자 이름으로 사용자를 조회합니다."""
    return await users.find_one({"username": username})

async def get_user_by_email(email: str):
    """이메일로 사용자를 조회합니다."""
    return await users.find_one({"email": email})

async def get_user_by_id(user_id: str):
    """ID로 사용자를 조회합니다."""
    try:
        uuid_id = uuid.UUID(user_id)
        return await users.find_one({"_id": uuid_id})
    except:
        return None

async def create_user(user: UserCreate):
    """새 사용자를 생성합니다."""
    # 사용자 존재 여부 확인
    existing_user = await get_user_by_username(user.username)
    if existing_user:
        return None
    
    # 이메일 중복 확인
    email_user = await get_user_by_email(user.email)
    if email_user:
        return None
    
    # 새 사용자 생성
    hashed_password = get_password_hash(user.password)
    user_id = uuid.uuid4()
    user_dict = {
        "_id": user_id,
        "username": user.username,
        "email": user.email,
        "is_admin": False,  # 기본적으로 일반 사용자로 설정
        "hashed_password": hashed_password,
        "created_at": datetime.utcnow(),
        "selected_mcps": [],
        "env_settings": {},
        "pod_name": None  # pod_name 초기화
    }
    
    await users.insert_one(user_dict)
    return user_dict

async def authenticate_user(email: str, password: str):
    """사용자 인증을 수행합니다."""
    user = await get_user_by_email(email)
    if not user:
        return False
    if not verify_password(password, user["hashed_password"]):
        return False
    return user

async def delete_user(user_id: str):
    """사용자를 삭제합니다."""
    try:
        uuid_id = uuid.UUID(user_id)
        result = await users.delete_one({"_id": uuid_id})
        return result.deleted_count > 0
    except Exception as e:
        print(f"사용자 삭제 중 오류 발생: {e}")
        return False

# ======== MCP 관련 CRUD ========

async def create_mcp(mcp: MCPCreate):
    """새 MCP를 생성합니다."""
    # UUID 생성
    mcp_id = uuid.uuid4()
    
    # 공개 ID 생성 (중복 체크)
    while True:
        public_id = generate_public_id()
        existing = await mcps.find_one({"public_id": public_id})
        if not existing:
            break
    
    mcp_dict = {
        "_id": mcp_id,
        "public_id": public_id,  # 공개 ID 추가
        "name": mcp.name,
        "description": mcp.description,
        "mcp_type": mcp.mcp_type,
        "required_env_vars": mcp.required_env_vars,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    await mcps.insert_one(mcp_dict)
    return mcp_dict

async def get_mcp(public_id: str):
    """공개 ID로 MCP를 조회합니다."""
    # 공개 ID로 조회
    mcp = await mcps.find_one({"public_id": public_id})
    return mcp

async def get_all_mcps():
    """모든 MCP를 조회합니다."""
    return await mcps.find().to_list(length=100)

async def update_mcp(public_id: str, mcp_data: MCPUpdate):
    """MCP 정보를 업데이트합니다."""
    # 공개 ID로 조회
    mcp = await mcps.find_one({"public_id": public_id})
    if mcp:
        update_dict = {k: v for k, v in mcp_data.model_dump().items() if v is not None}
        update_dict["updated_at"] = datetime.utcnow()
        
        result = await mcps.update_one(
            {"public_id": public_id},
            {"$set": update_dict}
        )
        return result.modified_count > 0
    
    return False

async def delete_mcp(public_id: str):
    """공개 ID로 MCP를 삭제합니다."""
    mcp = await get_mcp(public_id)
    if not mcp:
        return False
    
    # 내부 ID 참조(삭제용)
    uuid_id = mcp["_id"]
    
    try:
        # MCP 삭제
        mcp_result = await mcps.delete_one({"_id": uuid_id})
        
        # 사용자의 선택 목록과 환경 변수 설정에서 이 MCP 제거
        # $pull을 사용하여 선택 목록에서 제거
        await users.update_many(
            {"selected_mcps.public_id": mcp.get("public_id", "")},
            {"$pull": {"selected_mcps": {"public_id": mcp.get("public_id", "")}}}
        )
        
        # unset을 사용하여 환경 변수 설정에서 제거
        # 이전에는 UUID를 키로 사용했을 수 있으므로 두 가지 방법 모두 시도
        await users.update_many(
            {f"env_settings.{str(uuid_id)}": {"$exists": True}},
            {"$unset": {f"env_settings.{str(uuid_id)}": ""}}
        )
        
        await users.update_many(
            {f"env_settings.{mcp.get('public_id', '')}": {"$exists": True}},
            {"$unset": {f"env_settings.{mcp.get('public_id', '')}": ""}}
        )
        
        return mcp_result.deleted_count > 0
    except Exception as e:
        print(f"MCP 삭제 중 오류 발생: {e}")
        return False

# 이름 또는 유형으로 MCP 찾기
async def find_mcps_by_name_or_type(search_term: str):
    """이름 또는 유형으로 MCP를 검색합니다."""
    query = {
        "$or": [
            {"name": {"$regex": search_term, "$options": "i"}},  # 대소문자 구분 없이 검색
            {"mcp_type": {"$regex": search_term, "$options": "i"}}
        ]
    }
    return await mcps.find(query).to_list(length=20)

# ======== MCP 선택 관련 ========

async def select_mcp_for_user(user_id: str, public_id: str):
    """사용자가 MCP를 선택합니다."""
    try:
        # 사용자 ID 파싱
        try:
            uuid_user_id = uuid.UUID(user_id)
        except ValueError as e:
            return {"success": False, "message": f"사용자 ID 파싱 오류: {str(e)}"}
        
        # 공개 ID로 MCP가 존재하는지 확인
        mcp = await get_mcp(public_id)
        if not mcp:
            return {"success": False, "message": "MCP를 찾을 수 없습니다."}
        
        # MCP 정보를 객체로 구성 (public_id, name, mcp_type 포함)
        mcp_info = {
            "public_id": mcp.get("public_id", ""),  # 공개 ID 사용
            "name": mcp["name"],
            "mcp_type": mcp.get("mcp_type", ""),  # MCP 타입 저장
            "required_env_vars": mcp.get("required_env_vars", []),  # 필요한 환경변수 정보
            # "selected_at": datetime.utcnow()
        }
        
        # 기존에 저장된 데이터가 UUID 기반일 수 있으므로, 공개 ID로도 확인
        # 동일한 public_id의 MCP가 이미 있는지 확인하고, 있다면 제거
        try:
            await users.update_one(
                {"_id": uuid_user_id},
                {"$pull": {"selected_mcps": {"public_id": mcp.get("public_id", "")}}}
            )
        except Exception as e:
            print(f"public_id 업데이트 오류: {e}")
        
        # 새 MCP 정보 추가
        try:
            result = await users.update_one(
                {"_id": uuid_user_id},
                {"$push": {"selected_mcps": mcp_info}}
            )
        except Exception as e:
            print(f"MCP 정보 추가 오류: {e}")
            return {"success": False, "message": f"오류 발생: {str(e)}"}
        
        return {"success": True, "message": "MCP 선택이 완료되었습니다."}
    except ValueError as e:
        print(f"UUID 파싱 오류: {e}")
        return {"success": False, "message": f"UUID 파싱 오류: {str(e)}"}
    except Exception as e:
        print(f"MCP 선택 중 오류 발생: {e}")
        return {"success": False, "message": f"오류 발생: {str(e)}"}

async def deselect_mcp(user_id: str, public_id: str):
    """사용자의 MCP 선택을 취소합니다."""
    try:
        uuid_user_id = uuid.UUID(user_id)
        
        # 공개 ID로 MCP 찾기
        mcp = await get_mcp(public_id)
        if mcp:
            # 공개 ID 사용
            result = await users.update_one(
                {"_id": uuid_user_id},
                {"$pull": {"selected_mcps": {"public_id": mcp.get("public_id", "")}}}
            )
            return result.modified_count > 0
        
        # 직접 공개 ID로 시도
        result = await users.update_one(
            {"_id": uuid_user_id},
            {"$pull": {"selected_mcps": {"public_id": public_id}}}
        )
        
        return result.modified_count > 0
    except Exception as e:
        print(f"MCP 선택 취소 중 오류 발생: {e}")
        return False

async def get_user_selected_mcps(user_id: str):
    """사용자가 선택한 모든 MCP를 조회합니다."""
    try:
        user = await get_user_by_id(user_id)
        if not user or "selected_mcps" not in user:
            return []
        
        # 저장된 MCP 정보 사용
        selected_mcps = user["selected_mcps"]
        if not selected_mcps:
            return []
        
        return selected_mcps
    except Exception as e:
        print(f"선택된 MCP 조회 중 오류 발생: {e}")
        return []

# ======== 환경 변수 관련 ========

async def update_env_var(user_id: str, env_update: EnvUpdate):
    """사용자의 MCP 환경 변수를 업데이트합니다."""
    try:
        uuid_user_id = uuid.UUID(user_id)
        
        # 공개 ID로 MCP가 존재하는지 확인
        mcp = await get_mcp(env_update.public_id)
        if not mcp:
            return {"success": False, "message": "MCP를 찾을 수 없습니다."}
        
        # 공개 ID 사용
        public_id = mcp.get("public_id", "")
        
        # 필요한 환경변수 검증 (선택적)
        required_env_vars = mcp.get("required_env_vars", [])
        
        # 필수 환경변수가 제공되었는지 확인 (선택적)
        missing_vars = []
        for var_key in required_env_vars:
            if var_key not in env_update.env_vars:
                missing_vars.append(var_key)
        
        if missing_vars:
            return {
                "success": False, 
                "message": f"다음 환경변수가 누락되었습니다: {', '.join(missing_vars)}"
            }
        
        # 환경변수 암호화
        encrypted_env_vars = {}
        for key, value in env_update.env_vars.items():
            # API_KEY 관련 값만 암호화
            if "key" in key.lower() or "token" in key.lower() or "secret" in key.lower() or "password" in key.lower() or "api" in key.lower():
                encrypted_env_vars[key] = encrypt_value(value)
            else:
                encrypted_env_vars[key] = value
        
        # 환경변수 설정 업데이트 - 공개 ID 사용
        result = await users.update_one(
            {"_id": uuid_user_id},
            {"$set": {f"env_settings.{public_id}": encrypted_env_vars}}
        )
        
        return {"success": True, "message": "환경 변수가 업데이트되었습니다."}
    except Exception as e:
        print(f"환경 변수 업데이트 중 오류 발생: {e}")
        return {"success": False, "message": f"오류 발생: {str(e)}"}

async def get_env_vars(user_id: str, public_id: str = None):
    """사용자의 환경 변수를 조회합니다."""
    try:
        user = await get_user_by_id(user_id)
        if not user or "env_settings" not in user:
            return None if public_id else {}
        
        env_settings = user["env_settings"]
        
        # 특정 MCP에 대한 환경 변수 조회
        if public_id:
            # 공개 ID로 MCP 찾기
            mcp = await get_mcp(public_id)
            if mcp:
                mcp_public_id = mcp.get("public_id", "")
                encrypted_vars = env_settings.get(mcp_public_id, None)
                
                # 암호화된 환경변수 복호화
                if encrypted_vars:
                    decrypted_vars = {}
                    for key, value in encrypted_vars.items():
                        # API_KEY 관련 값만 복호화 시도
                        if "key" in key.lower() or "token" in key.lower() or "secret" in key.lower() or "password" in key.lower() or "api" in key.lower():
                            decrypted_vars[key] = decrypt_value(value)
                        else:
                            decrypted_vars[key] = value
                    return decrypted_vars
                return encrypted_vars
            
            # 직접 공개 ID로 시도
            encrypted_vars = env_settings.get(public_id, None)
            if encrypted_vars:
                decrypted_vars = {}
                for key, value in encrypted_vars.items():
                    # API_KEY 관련 값만 복호화 시도
                    if "key" in key.lower() or "token" in key.lower() or "secret" in key.lower() or "password" in key.lower() or "api" in key.lower():
                        decrypted_vars[key] = decrypt_value(value)
                    else:
                        decrypted_vars[key] = value
                return decrypted_vars
            return encrypted_vars
        
        # 모든 환경 변수 조회 (복호화 포함)
        decrypted_settings = {}
        for mcp_id, vars_dict in env_settings.items():
            decrypted_vars = {}
            for key, value in vars_dict.items():
                # API_KEY 관련 값만 복호화 시도
                if "key" in key.lower() or "token" in key.lower() or "secret" in key.lower() or "password" in key.lower() or "api" in key.lower():
                    decrypted_vars[key] = decrypt_value(value)
                else:
                    decrypted_vars[key] = value
            decrypted_settings[mcp_id] = decrypted_vars
        
        return decrypted_settings
    except Exception as e:
        print(f"환경 변수 조회 중 오류 발생: {e}")
        return None if public_id else {}

async def delete_env_var(user_id: str, public_id: str):
    """사용자의 MCP 환경 변수를 삭제합니다."""
    try:
        uuid_user_id = uuid.UUID(user_id)
        
        # 공개 ID로 MCP 찾기
        mcp = await get_mcp(public_id)
        if mcp:
            # 공개 ID 사용
            mcp_public_id = mcp.get("public_id", "")
            result = await users.update_one(
                {"_id": uuid_user_id},
                {"$unset": {f"env_settings.{mcp_public_id}": ""}}
            )
            return result.modified_count > 0
        
        # 직접 공개 ID로 시도
        result = await users.update_one(
            {"_id": uuid_user_id},
            {"$unset": {f"env_settings.{public_id}": ""}}
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"환경 변수 삭제 중 오류 발생: {e}")
        return False


#####################################################
# 정찬호 추가 crud
# crud/nosql.py ― 파일 맨 아래 “환경 변수 관련” 주석 위 or 원하는 위치
# ================================================================

async def get_user_settings(user_id: str) -> dict:
    """
    사용자가 저장해 둔 세팅(features, api_key 등)을 반환합니다.
    값이 없으면 빈 dict.
    """
    try:
        user = await get_user_by_id(user_id)
        # env_settings, selected_mcps 등 다른 키를 합치고 싶으면 여기서 병합
        return user.get("env_settings", {}) if user else {}
    except Exception as e:
        print(f"유저 세팅 조회 중 오류: {e}")
        return {}
        
async def update_pod_name(user_id: str, pod_name: str) -> bool:
    """
    사용자의 pod_name을 업데이트합니다.
    """
    try:
        uuid_user_id = uuid.UUID(user_id)
        result = await users.update_one(
            {"_id": uuid_user_id},
            {"$set": {"pod_name": pod_name}}
        )
        # 업데이트 결과 확인 - matched_count도 확인
        return result.modified_count > 0 or result.matched_count > 0
    except Exception as e:
        print(f"pod_name 업데이트 중 오류 발생: {e}")
        return False
        
async def get_pod_name(user_id: str) -> str:
    """
    사용자의 pod_name을 반환합니다.
    """
    try:
        user = await get_user_by_id(user_id)
        return user.get("pod_name") if user else None
    except Exception as e:
        print(f"pod_name 조회 중 오류 발생: {e}")
        return None
        
async def change_user_password(user_id: str, current_password: str, new_password: str) -> dict:
    """
    사용자의 비밀번호를 변경합니다.
    1. 현재 비밀번호 확인
    2. 새 비밀번호로 해시 생성
    3. 데이터베이스 업데이트
    """
    try:
        # 사용자 정보 가져오기
        user = await get_user_by_id(user_id)
        if not user:
            return {"success": False, "message": "사용자를 찾을 수 없습니다."}
        
        # 현재 비밀번호 확인
        if not verify_password(current_password, user["hashed_password"]):
            return {"success": False, "message": "현재 비밀번호가 일치하지 않습니다."}
        
        # 새 비밀번호 해시 생성
        hashed_password = get_password_hash(new_password)
        
        # 비밀번호 업데이트
        uuid_id = uuid.UUID(user_id)
        result = await users.update_one(
            {"_id": uuid_id},
            {"$set": {"hashed_password": hashed_password}}
        )
        
        if result.modified_count > 0:
            return {"success": True, "message": "비밀번호가 성공적으로 변경되었습니다."}
        else:
            return {"success": False, "message": "비밀번호 변경 중 오류가 발생했습니다."}
    
    except Exception as e:
        print(f"비밀번호 변경 중 오류 발생: {e}")
        return {"success": False, "message": f"오류 발생: {str(e)}"}

# ======== 대화 관련 CRUD ========

async def get_user_conversation(user_id: str):
    """사용자의 대화 문서 조회"""
    try:
        return await conversations.find_one({"user_id": user_id})
    except Exception as e:
        print(f"사용자 대화 조회 중 오류: {e}")
        return None

async def get_recent_conversations(user_id: str, limit: int = 6) -> List[Dict[str, str]]:
    """
    최신 N개 대화 조회 (Agent에 전달용)
    limit=6이면 최근 3쌍의 대화를 반환
    """
    try:
        conversation = await get_user_conversation(user_id)
        if not conversation or not conversation.get("messages"):
            return []
        
        # 최신 메시지부터 limit 개수만큼 가져오기
        recent_messages = conversation["messages"][-limit:]
        
        # Agent에 전달할 형식으로 변환
        conversation_history = []
        for msg in recent_messages:
            conversation_history.append({
                "user": msg["user_message"],
                "assistant": msg["assistant_message"],
                "timestamp": msg["timestamp"].isoformat() if hasattr(msg["timestamp"], 'isoformat') else str(msg["timestamp"])
            })
        
        return conversation_history
    except Exception as e:
        print(f"최근 대화 조회 중 오류: {e}")
        return []

async def save_conversation_message(user_id: str, user_message: str, assistant_message: str):
    """사용자 대화에 새 메시지 추가"""
    try:
        # 새 메시지 객체
        new_message = {
            "user_message": user_message,
            "assistant_message": assistant_message,
            "timestamp": datetime.utcnow()
        }
        
        # 기존 대화 조회
        conversation = await get_user_conversation(user_id)
        
        if conversation:
            # 기존 대화에 메시지 추가
            messages = conversation.get("messages", [])
            messages.append(new_message)
            
            # 최대 메시지 수 제한 (50개 유지)
            if len(messages) > 50:
                messages = messages[-50:]
            
            # 업데이트
            result = await conversations.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "messages": messages,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        else:
            # 새 대화 문서 생성
            new_conversation = {
                "user_id": user_id,
                "messages": [new_message],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = await conversations.insert_one(new_conversation)
            return result.inserted_id is not None
            
    except Exception as e:
        print(f"대화 저장 중 오류: {e}")
        return False

async def get_conversation_stats(user_id: str) -> Dict[str, Any]:
    """사용자 대화 통계 조회"""
    try:
        conversation = await get_user_conversation(user_id)
        if not conversation:
            return {
                "total_messages": 0,
                "created_at": None,
                "last_activity": None
            }
        
        messages = conversation.get("messages", [])
        return {
            "total_messages": len(messages),
            "created_at": conversation.get("created_at"),
            "last_activity": conversation.get("updated_at")
        }
    except Exception as e:
        print(f"대화 통계 조회 중 오류: {e}")
        return {"total_messages": 0, "created_at": None, "last_activity": None}

async def clear_user_conversation(user_id: str):
    """사용자 대화 초기화"""
    try:
        result = await conversations.delete_one({"user_id": user_id})
        return result.deleted_count > 0
    except Exception as e:
        print(f"대화 초기화 중 오류: {e}")
        return False
