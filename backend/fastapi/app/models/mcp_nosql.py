from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid

# 사용자 모델
class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: Optional[uuid.UUID] = None
    is_admin: bool = False
    selected_mcps: List[Dict[str, Any]] = []
    pod_name: Optional[str] = None
    def model_dump(self):
        return {
            "id": str(self.id) if self.id else None, 
            "username": self.username, 
            "email": self.email, 
            "is_admin": self.is_admin,
            "selected_mcps": self.selected_mcps,
            "pod_name": self.pod_name
        }

class UserInDB(UserBase):
    id: uuid.UUID
    is_admin: bool = False
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    # 사용자가 선택한 MCP 목록 (기본 정보를 포함한 객체 저장)
    selected_mcps: List[Dict[str, Any]] = []
    # 사용자의 MCP별 환경 변수 설정 (MCP ID를 키로 사용)
    env_settings: Dict[str, Dict[str, str]] = {}
    # 사용자의 Pod 이름
    pod_name: Optional[str] = None

# MCP 모델
class MCPBase(BaseModel):
    name: str
    description: Optional[str] = None
    mcp_type: str  # MCP 타입 (예: "notion", "gitlab" 등)

class MCPCreate(MCPBase):
    required_env_vars: Optional[List[str]] = None  # 필요한 환경변수 이름 목록

class MCPUpdate(MCPBase):
    required_env_vars: Optional[List[str]] = None

class MCP(MCPBase):
    id: uuid.UUID
    public_id: str  # 공개용 식별자
    required_env_vars: Optional[List[str]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
# MCP 환경변수 업데이트를 위한 모델
class EnvUpdate(BaseModel):
    public_id: str  # public_id 사용
    env_vars: Dict[str, str]  # 키-값 쌍으로 여러 환경변수 지원

# 인증 토큰 모델
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# 채팅 메시지 스키마
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None  # 세션 ID 추가

# 채팅 응답 스키마
class ChatResponse(BaseModel):
    response: str
    timestamp: datetime

# 비밀번호 변경 스키마
class PasswordChange(BaseModel):
    current_password: str
    new_password: str

# 대화 메시지 모델
class ConversationMessage(BaseModel):
    user_message: str
    assistant_message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# 세션 기반 대화 모델
class ConversationSession(BaseModel):
    user_id: str
    session_id: str
    session_name: str = "새 대화"
    messages: List[ConversationMessage] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# 세션 생성 요청 모델
class SessionCreateRequest(BaseModel):
    session_name: str = "새 대화"

# 세션 업데이트 요청 모델
class SessionUpdateRequest(BaseModel):
    session_name: str

# 세션 정보 응답 모델
class SessionInfo(BaseModel):
    session_id: str
    session_name: str
    message_count: int
    created_at: str
    updated_at: str
    last_message: Optional[Dict[str, Any]] = None

# 세션 목록 응답 모델
class SessionListResponse(BaseModel):
    sessions: List[SessionInfo]

# 사용자별 대화 컬렉션 모델 (하위 호환성)
class UserConversation(BaseModel):
    user_id: str
    messages: List[ConversationMessage] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 최근 메시지만 유지 (메모리 효율성)
    max_messages: int = 50

# 대화 응답 모델 (세션 정보 포함)
class ConversationalChatResponse(BaseModel):
    response: str
    timestamp: datetime
    session_id: str
    session_name: str
    conversation_count: int = 0  # 총 대화 수
    used_history: bool = False   # 히스토리를 사용했는지 여부