from datetime import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId
from core.database import async_conversations_collection

class ConversationManager:
    def __init__(self):
        self.conversations_collection = async_conversations_collection
    
    async def add_message(self, user_id: str, user_message: str, assistant_response: str):
        """대화에 메시지를 추가합니다. 유저별로 한 문서에 모든 대화를 저장합니다."""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"add_message 호출: user_id={user_id}")
        
        # 새 메시지 객체
        new_message = {
            "user_message": user_message,
            "assistant_response": assistant_response,
            "timestamp": datetime.now()
        }
        
        try:
            # 먼저 사용자 문서가 있는지 확인
            existing_doc = await self.conversations_collection.find_one({"user_id": user_id})
            
            if existing_doc:
                # 기존 문서가 있으면 메시지 추가
                result = await self.conversations_collection.update_one(
                    {"user_id": user_id},
                    {
                        "$push": {"messages": new_message},
                        "$set": {"updated_at": datetime.now()}
                    }
                )
                logger.info(f"기존 문서에 메시지 추가: user_id={user_id}, modified_count={result.modified_count}")
                return str(existing_doc["_id"])
            else:
                # 새 문서 생성
                new_doc = {
                    "user_id": user_id,
                    "messages": [new_message],
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }
                result = await self.conversations_collection.insert_one(new_doc)
                logger.info(f"새 문서 생성: user_id={user_id}, doc_id={result.inserted_id}")
                return str(result.inserted_id)
                
        except Exception as e:
            logger.error(f"메시지 저장 실패: {str(e)}")
            raise
    
    async def get_conversation_history(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """사용자의 대화 히스토리를 가져옵니다. 한 문서에서 messages 배열을 조회합니다."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # 사용자 문서 조회
            conversation_doc = await self.conversations_collection.find_one(
                {"user_id": user_id}
            )
            
            if not conversation_doc or "messages" not in conversation_doc:
                logger.info(f"사용자 대화 내역 없음: user_id={user_id}")
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
            
            logger.info(f"대화 히스토리 조회 성공: user_id={user_id}, 메시지 수={len(formatted_messages)}")
            return formatted_messages
            
        except Exception as e:
            logger.error(f"대화 히스토리 조회 실패: {str(e)}")
            return []
    
    async def clear_conversation_history(self, user_id: str):
        """사용자의 대화 히스토리를 삭제합니다. 전체 문서를 삭제합니다."""
        try:
            result = await self.conversations_collection.delete_one({"user_id": user_id})
            return result.deleted_count
        except Exception as e:
            return 0
    
    async def get_conversation_summary(self, user_id: str) -> Dict[str, Any]:
        """대화 요약 정보를 반환합니다."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # 사용자 문서 조회
            conversation_doc = await self.conversations_collection.find_one(
                {"user_id": user_id}
            )
            
            if not conversation_doc:
                return {
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
                "total_messages": total_count,
                "has_history": total_count > 0,
                "last_activity": last_activity
            }
            
        except Exception as e:
            logger.error(f"대화 요약 조회 실패: {str(e)}")
            return {
                "total_messages": 0,
                "has_history": False,
                "last_activity": None
            }

# 전역 인스턴스
conversation_manager = ConversationManager()