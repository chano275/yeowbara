from datetime import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId
from core.database import async_conversations_collection
import uuid

class ConversationManager:
    def __init__(self):
        self.conversations_collection = async_conversations_collection
    
    async def create_session(self, user_id: str, session_name: str = "새 대화") -> str:
        """새로운 대화 세션을 생성합니다."""
        import logging
        logger = logging.getLogger(__name__)
        
        session_id = str(uuid.uuid4())
        
        session_doc = {
            "user_id": user_id,
            "session_id": session_id,
            "session_name": session_name,
            "messages": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        try:
            result = await self.conversations_collection.insert_one(session_doc)
            logger.info(f"새 세션 생성: user_id={user_id}, session_id={session_id}, name={session_name}")
            return session_id
        except Exception as e:
            logger.error(f"세션 생성 실패: {str(e)}")
            raise
    
    async def get_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """사용자의 모든 세션 목록을 가져옵니다."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            cursor = self.conversations_collection.find(
                {"user_id": user_id},
                {"session_id": 1, "session_name": 1, "created_at": 1, "updated_at": 1, "messages": 1}
            ).sort("updated_at", -1)
            
            sessions = []
            async for doc in cursor:
                sessions.append({
                    "session_id": doc["session_id"],
                    "session_name": doc["session_name"],
                    "message_count": len(doc.get("messages", [])),
                    "created_at": doc["created_at"].isoformat(),
                    "updated_at": doc["updated_at"].isoformat(),
                    "last_message": doc["messages"][-1] if doc.get("messages") else None
                })
            
            logger.info(f"세션 목록 조회: user_id={user_id}, 세션 수={len(sessions)}")
            return sessions
        except Exception as e:
            logger.error(f"세션 목록 조회 실패: {str(e)}")
            return []
    
    async def update_session_name(self, user_id: str, session_id: str, new_name: str) -> bool:
        """세션 이름을 변경합니다."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            result = await self.conversations_collection.update_one(
                {"user_id": user_id, "session_id": session_id},
                {"$set": {"session_name": new_name, "updated_at": datetime.now()}}
            )
            
            if result.modified_count > 0:
                logger.info(f"세션 이름 변경: user_id={user_id}, session_id={session_id}, new_name={new_name}")
                return True
            else:
                logger.warning(f"세션 이름 변경 실패: 세션을 찾을 수 없음")
                return False
        except Exception as e:
            logger.error(f"세션 이름 변경 실패: {str(e)}")
            return False
    
    async def delete_session(self, user_id: str, session_id: str) -> bool:
        """세션을 삭제합니다."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            result = await self.conversations_collection.delete_one(
                {"user_id": user_id, "session_id": session_id}
            )
            
            if result.deleted_count > 0:
                logger.info(f"세션 삭제: user_id={user_id}, session_id={session_id}")
                return True
            else:
                logger.warning(f"세션 삭제 실패: 세션을 찾을 수 없음")
                return False
        except Exception as e:
            logger.error(f"세션 삭제 실패: {str(e)}")
            return False
    
    async def add_message(self, user_id: str, user_message: str, assistant_response: str, session_id: str = None):
        """특정 세션에 메시지를 추가합니다."""
        import logging
        logger = logging.getLogger(__name__)
        
        # 세션 ID가 없으면 default 세션 찾기 또는 생성
        if not session_id:
            session_id = await self._get_or_create_default_session(user_id)
        
        logger.info(f"add_message 호출: user_id={user_id}, session_id={session_id}")
        
        # 새 메시지 객체
        new_message = {
            "user_message": user_message,
            "assistant_response": assistant_response,
            "timestamp": datetime.now()
        }
        
        try:
            # 세션 문서가 있는지 확인
            existing_doc = await self.conversations_collection.find_one(
                {"user_id": user_id, "session_id": session_id}
            )
            
            if existing_doc:
                # 기존 세션에 메시지 추가
                result = await self.conversations_collection.update_one(
                    {"user_id": user_id, "session_id": session_id},
                    {
                        "$push": {"messages": new_message},
                        "$set": {"updated_at": datetime.now()}
                    }
                )
                logger.info(f"세션에 메시지 추가: user_id={user_id}, session_id={session_id}")
                return str(existing_doc["_id"])
            else:
                # 세션이 없으면 새로 생성
                new_doc = {
                    "user_id": user_id,
                    "session_id": session_id,
                    "session_name": "기본 대화",
                    "messages": [new_message],
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }
                result = await self.conversations_collection.insert_one(new_doc)
                logger.info(f"새 세션 생성 및 메시지 추가: user_id={user_id}, session_id={session_id}")
                return str(result.inserted_id)
                
        except Exception as e:
            logger.error(f"메시지 저장 실패: {str(e)}")
            raise
    
    async def get_conversation_history(self, user_id: str, limit: int = 20, session_id: str = None) -> List[Dict[str, Any]]:
        """특정 세션의 대화 히스토리를 가져옵니다."""
        import logging
        logger = logging.getLogger(__name__)
        
        # 세션 ID가 없으면 default 세션 찾기
        if not session_id:
            session_id = await self._get_or_create_default_session(user_id)
        
        try:
            # 세션 문서 조회
            conversation_doc = await self.conversations_collection.find_one(
                {"user_id": user_id, "session_id": session_id}
            )
            
            if not conversation_doc or "messages" not in conversation_doc:
                logger.info(f"세션 대화 내역 없음: user_id={user_id}, session_id={session_id}")
                return []
            
            # messages 배열에서 최근 limit개 메시지 가져오기
            messages = conversation_doc["messages"]
            if limit:
                messages = messages[-limit:]
            
            # 응답 형식으로 변환
            formatted_messages = []
            for msg in messages:
                formatted_messages.append({
                    "user": msg["user_message"],
                    "assistant": msg["assistant_response"],
                    "timestamp": msg["timestamp"].isoformat() if isinstance(msg["timestamp"], datetime) else msg["timestamp"]
                })
            
            logger.info(f"세션 대화 히스토리 조회: user_id={user_id}, session_id={session_id}, 메시지 수={len(formatted_messages)}")
            return formatted_messages
            
        except Exception as e:
            logger.error(f"세션 대화 히스토리 조회 실패: {str(e)}")
            return []
    
    async def clear_session_history(self, user_id: str, session_id: str) -> int:
        """특정 세션의 대화 히스토리를 초기화합니다."""
        try:
            result = await self.conversations_collection.update_one(
                {"user_id": user_id, "session_id": session_id},
                {
                    "$set": {
                        "messages": [],
                        "updated_at": datetime.now()
                    }
                }
            )
            return result.modified_count
        except Exception as e:
            return 0
    
    async def get_session_summary(self, user_id: str, session_id: str = None) -> Dict[str, Any]:
        """특정 세션의 요약 정보를 반환합니다."""
        import logging
        logger = logging.getLogger(__name__)
        
        # 세션 ID가 없으면 default 세션 찾기
        if not session_id:
            session_id = await self._get_or_create_default_session(user_id)
        
        try:
            # 세션 문서 조회
            conversation_doc = await self.conversations_collection.find_one(
                {"user_id": user_id, "session_id": session_id}
            )
            
            if not conversation_doc:
                return {
                    "session_id": session_id,
                    "session_name": "기본 대화",
                    "total_messages": 0,
                    "has_history": False,
                    "last_activity": None
                }
            
            # 메시지 수 계산
            messages = conversation_doc.get("messages", [])
            total_count = len(messages)
            
            # 마지막 활동 시간
            last_activity = None
            if conversation_doc.get("updated_at"):
                last_activity = conversation_doc["updated_at"].isoformat()
            elif messages:
                last_message = messages[-1]
                if "timestamp" in last_message:
                    timestamp = last_message["timestamp"]
                    last_activity = timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp
            
            return {
                "session_id": session_id,
                "session_name": conversation_doc.get("session_name", "기본 대화"),
                "total_messages": total_count,
                "has_history": total_count > 0,
                "last_activity": last_activity
            }
            
        except Exception as e:
            logger.error(f"세션 요약 조회 실패: {str(e)}")
            return {
                "session_id": session_id,
                "session_name": "기본 대화",
                "total_messages": 0,
                "has_history": False,
                "last_activity": None
            }
    
    async def _get_or_create_default_session(self, user_id: str) -> str:
        """기본 세션을 찾거나 생성합니다."""
        # 먼저 기존 세션이 있는지 확인 (하위 호환성)
        existing_doc = await self.conversations_collection.find_one(
            {"user_id": user_id, "session_id": {"$exists": False}}
        )
        
        if existing_doc:
            # 기존 세션을 default로 변환
            default_session_id = "default"
            await self.conversations_collection.update_one(
                {"_id": existing_doc["_id"]},
                {
                    "$set": {
                        "session_id": default_session_id,
                        "session_name": "기본 대화"
                    }
                }
            )
            return default_session_id
        else:
            # default 세션 찾기
            default_doc = await self.conversations_collection.find_one(
                {"user_id": user_id, "session_id": "default"}
            )
            
            if default_doc:
                return "default"
            else:
                # default 세션 생성
                return await self.create_session(user_id, "기본 대화")

    # 하위 호환성을 위한 기존 메서드들
    async def clear_conversation_history(self, user_id: str):
        """기본 세션의 대화 히스토리를 삭제합니다 (하위 호환성)."""
        session_id = await self._get_or_create_default_session(user_id)
        return await self.clear_session_history(user_id, session_id)
    
    async def get_conversation_summary(self, user_id: str) -> Dict[str, Any]:
        """기본 세션의 대화 요약 정보를 반환합니다 (하위 호환성)."""
        session_id = await self._get_or_create_default_session(user_id)
        return await self.get_session_summary(user_id, session_id)

# 전역 인스턴스
conversation_manager = ConversationManager()