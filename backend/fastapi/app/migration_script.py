"""
기존 개별 메시지 문서들을 유저별 통합 문서로 마이그레이션하는 스크립트
"""
import asyncio
from datetime import datetime
from core.database import async_conversations_collection
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_to_user_documents():
    """개별 메시지 문서들을 유저별 통합 문서로 마이그레이션"""
    
    # 1. 모든 기존 메시지에서 user_id 목록 추출
    pipeline = [
        {"$match": {"messages": {"$exists": False}}},  # 기존 형식만 (새 형식 제외)
        {"$group": {"_id": "$user_id"}}
    ]
    
    user_ids = []
    async for doc in async_conversations_collection.aggregate(pipeline):
        user_ids.append(doc["_id"])
    
    logger.info(f"마이그레이션 대상 사용자: {len(user_ids)}명")
    
    migrated_users = 0
    
    for user_id in user_ids:
        logger.info(f"사용자 {user_id} 마이그레이션 시작...")
        
        # 2. 해당 사용자의 모든 기존 메시지 조회 (시간순)
        cursor = async_conversations_collection.find({
            "user_id": user_id,
            "messages": {"$exists": False}  # 기존 형식만
        }).sort("timestamp", 1)
        
        messages = []
        old_message_ids = []
        
        async for msg_doc in cursor:
            # 기존 형식에서 메시지 정보 추출
            if "user_message" in msg_doc and "assistant_response" in msg_doc:
                messages.append({
                    "user_message": msg_doc["user_message"],
                    "assistant_response": msg_doc["assistant_response"],
                    "timestamp": msg_doc.get("timestamp", datetime.now())
                })
                old_message_ids.append(msg_doc["_id"])
        
        if not messages:
            logger.info(f"사용자 {user_id}: 마이그레이션할 메시지 없음")
            continue
        
        # 3. 이미 통합 문서가 있는지 확인
        existing_doc = await async_conversations_collection.find_one({
            "user_id": user_id,
            "messages": {"$exists": True}
        })
        
        if existing_doc:
            logger.info(f"사용자 {user_id}: 이미 통합 문서 존재, 기존 메시지만 삭제")
            # 기존 개별 메시지만 삭제
            delete_result = await async_conversations_collection.delete_many({
                "_id": {"$in": old_message_ids}
            })
            logger.info(f"사용자 {user_id}: {delete_result.deleted_count}개 기존 메시지 삭제")
            continue
        
        # 4. 새로운 통합 문서 생성
        conversation_doc = {
            "user_id": user_id,
            "messages": messages,
            "created_at": messages[0]["timestamp"],
            "updated_at": messages[-1]["timestamp"]
        }
        
        try:
            # 새 통합 문서 삽입
            insert_result = await async_conversations_collection.insert_one(conversation_doc)
            logger.info(f"사용자 {user_id}: 통합 문서 생성 완료 ({len(messages)}개 메시지)")
            
            # 기존 개별 메시지 문서들 삭제
            delete_result = await async_conversations_collection.delete_many({
                "_id": {"$in": old_message_ids}
            })
            logger.info(f"사용자 {user_id}: {delete_result.deleted_count}개 기존 메시지 삭제")
            
            migrated_users += 1
            
        except Exception as e:
            logger.error(f"사용자 {user_id} 마이그레이션 실패: {str(e)}")
    
    logger.info(f"마이그레이션 완료: {migrated_users}명 처리")

async def verify_migration():
    """마이그레이션 결과 검증"""
    
    # 기존 형식 문서 수 확인
    old_format_count = await async_conversations_collection.count_documents({
        "messages": {"$exists": False}
    })
    
    # 새 형식 문서 수 확인
    new_format_count = await async_conversations_collection.count_documents({
        "messages": {"$exists": True}
    })
    
    logger.info(f"검증 결과:")
    logger.info(f"- 기존 형식 문서 수: {old_format_count}")
    logger.info(f"- 새 형식 문서 수: {new_format_count}")
    
    # 새 형식 문서의 메시지 수 확인
    pipeline = [
        {"$match": {"messages": {"$exists": True}}},
        {"$project": {
            "user_id": 1,
            "message_count": {"$size": "$messages"}
        }}
    ]
    
    total_messages = 0
    async for doc in async_conversations_collection.aggregate(pipeline):
        total_messages += doc["message_count"]
        logger.info(f"사용자 {doc['user_id']}: {doc['message_count']}개 메시지")
    
    logger.info(f"총 통합된 메시지 수: {total_messages}")

async def rollback_migration():
    """마이그레이션 롤백 (필요시)"""
    logger.warning("롤백 시작... 통합 문서를 개별 메시지로 분리합니다.")
    
    # 새 형식 문서들 조회
    cursor = async_conversations_collection.find({
        "messages": {"$exists": True}
    })
    
    rollback_count = 0
    
    async for doc in cursor:
        user_id = doc["user_id"]
        messages = doc.get("messages", [])
        
        logger.info(f"사용자 {user_id} 롤백 시작... ({len(messages)}개 메시지)")
        
        # 각 메시지를 개별 문서로 생성
        individual_docs = []
        for msg in messages:
            individual_docs.append({
                "user_id": user_id,
                "user_message": msg["user_message"],
                "assistant_response": msg["assistant_response"],
                "timestamp": msg["timestamp"]
            })
        
        try:
            if individual_docs:
                # 개별 문서들 삽입
                await async_conversations_collection.insert_many(individual_docs)
                logger.info(f"사용자 {user_id}: {len(individual_docs)}개 개별 문서 생성")
            
            # 통합 문서 삭제
            await async_conversations_collection.delete_one({"_id": doc["_id"]})
            logger.info(f"사용자 {user_id}: 통합 문서 삭제")
            
            rollback_count += 1
            
        except Exception as e:
            logger.error(f"사용자 {user_id} 롤백 실패: {str(e)}")
    
    logger.info(f"롤백 완료: {rollback_count}명 처리")

# 실행 함수들
async def main():
    """메인 실행 함수"""
    import sys
    
    if len(sys.argv) < 2:
        print("사용법: python migration_script.py [migrate|verify|rollback]")
        return
    
    command = sys.argv[1]
    
    if command == "migrate":
        await migrate_to_user_documents()
    elif command == "verify":
        await verify_migration()
    elif command == "rollback":
        await rollback_migration()
    else:
        print("사용 가능한 명령: migrate, verify, rollback")

if __name__ == "__main__":
    asyncio.run(main())