from datetime import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId
from core.database import async_conversations_collection

class ConversationManager:
    def __init__(self):
        self.conversations_collection = async_conversations_collection
    
    async def add_message(self, user_id: str, user_message: str, assistant_response: str):
        """대화에 메시지를 추가합니다."""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"add_message 호출: user_id={user_id}, user_message={user_message[:50]}..., assistant_response={assistant_response[:50]}...")
        
        message_doc = {
            "user_id": user_id,
            "user_message": user_message,
            "assistant_response": assistant_response,
            "timestamp": datetime.now()
        }
        
        logger.info(f"DB에 저장할 문서: {message_doc}")
        
        try:
            result = await self.conversations_collection.insert_one(message_doc)
            logger.info(f"저장 성공: inserted_id={result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"DB 저장 실패: {str(e)}")
            raise
    
    async def get_conversation_history(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """사용자의 대화 히스토리를 가져옵니다."""
        import logging
        logger = logging.getLogger(__name__)
        
        cursor = self.conversations_collection.find(
            {"user_id": user_id}
        ).sort("timestamp", -1).limit(limit)
        
        messages = []
        async for doc in cursor:
            logger.info(f"DB에서 가져온 문서: {doc}")
            
            # 다양한 형태의 데이터 구조를 처리
            try:
                # 방법 1: user_message, assistant_response 사용
                if "user_message" in doc and "assistant_response" in doc:
                    messages.append({
                    "user": doc["user_message"],
                    "assistant": doc["assistant_response"],
                    "timestamp": doc.get("timestamp", datetime.now()).isoformat() if isinstance(doc.get("timestamp", datetime.now()), datetime) else doc.get("timestamp", datetime.now().isoformat())
                    })
                # 방법 2: user_message, assistant_message 사용
                elif "user_message" in doc and "assistant_message" in doc:
                    messages.append({
                        "user": doc["user_message"],
                        "assistant": doc["assistant_message"],
                        "timestamp": doc.get("timestamp", datetime.now()).isoformat() if isinstance(doc.get("timestamp", datetime.now()), datetime) else doc.get("timestamp", datetime.now().isoformat())
                    })
                # 방법 3: user, assistant 사용
                elif "user" in doc and "assistant" in doc:
                    messages.append({
                        "user": doc["user"],
                        "assistant": doc["assistant"],
                        "timestamp": doc.get("timestamp", datetime.now()).isoformat() if isinstance(doc.get("timestamp", datetime.now()), datetime) else doc.get("timestamp", datetime.now().isoformat())
                    })
                else:
                    logger.warning(f"알 수 없는 문서 형태: {doc}")
            except KeyError as e:
                logger.error(f"키 오류: {e}, 문서: {doc}")
                continue
        
        # 시간순으로 정렬 (최신 순에서 역순으로)
        return list(reversed(messages))
    
    async def clear_conversation_history(self, user_id: str):
        """사용자의 대화 히스토리를 삭제합니다."""
        result = await self.conversations_collection.delete_many({"user_id": user_id})
        return result.deleted_count
    
    async def get_conversation_summary(self, user_id: str) -> Dict[str, Any]:
        """대화 요약 정보를 반환합니다."""
        import logging
        logger = logging.getLogger(__name__)
        
        # 총 메시지 수
        total_count = await self.conversations_collection.count_documents({"user_id": user_id})
        
        # 최근 메시지
        last_message = await self.conversations_collection.find_one(
            {"user_id": user_id},
            sort=[("timestamp", -1)]
        )
        
        summary = {
            "total_messages": total_count,
            "has_history": total_count > 0,
            "last_activity": None
        }
        
        if last_message:
            try:
                # timestamp 필드 처리
                if "timestamp" in last_message:
                    timestamp = last_message["timestamp"]
                    summary["last_activity"] = timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp
                else:
                    logger.warning(f"timestamp 필드가 없는 문서: {last_message}")
                    summary["last_activity"] = datetime.now().isoformat()
            except Exception as e:
                logger.error(f"last_activity 처리 오류: {e}")
                summary["last_activity"] = datetime.now().isoformat()
        
        return summary

# 전역 인스턴스
conversation_manager = ConversationManager()
