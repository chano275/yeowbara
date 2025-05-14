import subprocess
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from typing import List, Dict, Any, Optional

from routers.nosql_auth import get_current_user
from models.mcp_nosql import ChatRequest, ConversationalChatResponse
from crud.nosql import (
    get_recent_conversations,
    save_conversation_message,
    get_conversation_stats,
    clear_user_conversation,
    get_user_by_id
)
from core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/conversation",
    tags=["대화형 챗봇 (DB 기반)"],
    responses={404: {"description": "Not found"}}
)

@router.post("/chat", response_model=ConversationalChatResponse)
async def chat_with_history(
    chat_request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """DB 기반 대화 처리 - 최신 3쌍의 대화를 Agent에 전달"""
    
    user_id = str(current_user["_id"])
    
    try:
        # 1. 사용자 Pod 정보 확인
        user = await get_user_by_id(user_id)
        if not user.get("pod_name"):
            raise HTTPException(
                status_code=400,
                detail="Pod가 생성되지 않았습니다. 먼저 Pod를 생성해주세요."
            )
        
        pod_name = user["pod_name"]
        
        # 2. 최신 대화 히스토리 조회 (3쌍 = 6개 메시지)
        recent_conversations = await get_recent_conversations(user_id, limit=6)
        
        # 3. Agent에 전송할 데이터 구성
        agent_data = {
            "text": chat_request.message,
            "user_id": user_id,
        }
        
        # 대화 히스토리가 있으면 포함
        if recent_conversations:
            agent_data["conversation_history"] = recent_conversations
            agent_data["use_conversation_context"] = True
            logger.info(f"대화 히스토리 포함 - 사용자: {user_id}, 히스토리 수: {len(recent_conversations)}")
        else:
            agent_data["new_conversation"] = True
            logger.info(f"새 대화 시작 - 사용자: {user_id}")
        
        # 4. kubectl + curl로 Agent 호출
        json_str = json.dumps(agent_data)
        cmd = [
            "kubectl", "exec", pod_name,
            "-n", "agent-env",
            "-c", "agent",
            "--",
            "curl", "-s", "-X", "POST",
            settings.AGENT_URL,
            "-H", "Content-Type: application/json",
            "-d", json_str
        ]
        
        logger.debug(f"kubectl 명령 실행: {' '.join(cmd[:6])}...")
        
        # Agent 호출
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            logger.error(f"kubectl 명령 실패 - 반환 코드: {result.returncode}")
            logger.error(f"오류: {result.stderr}")
            raise HTTPException(
                status_code=500,
                detail=f"Agent 호출 실패: {result.stderr[:100]}"
            )
        
        # 5. Agent 응답 처리
        try:
            if result.stdout.strip():
                logger.info(f"Agent 원본 응답: {result.stdout[:500]}...")
                response_data = json.loads(result.stdout)
                agent_response = response_data.get("response", result.stdout.strip())
            else:
                logger.error("Agent에서 빈 응답을 받았습니다.")
                raise HTTPException(
                    status_code=500,
                    detail="Agent에서 빈 응답을 받았습니다."
                )
        except json.JSONDecodeError as e:
            logger.error(f"Agent 응답 파싱 오류: {e}")
            logger.error(f"원본 응답: {result.stdout}")
            # JSON 파싱 실패시 일반 텍스트로 처리
            agent_response = result.stdout.strip() if result.stdout.strip() else "Agent 응답을 받을 수 없습니다."
        
        # 6. DB에 대화 저장
        saved = await save_conversation_message(
            user_id, 
            chat_request.message, 
            agent_response
        )
        
        if not saved:
            logger.warning(f"대화 저장 실패 - 사용자: {user_id}")
        
        # 7. 응답 구성
        stats = await get_conversation_stats(user_id)
        
        return ConversationalChatResponse(
            response=agent_response,
            timestamp=datetime.utcnow(),
            conversation_count=stats.get("total_messages", 0),
            used_history=bool(recent_conversations)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"대화 처리 중 오류 - 사용자: {user_id}")
        raise HTTPException(
            status_code=500,
            detail=f"내부 서버 오류: {str(e)}"
        )

@router.get("/history")
async def get_conversation_history(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """사용자 대화 히스토리 조회"""
    user_id = str(current_user["_id"])
    
    try:
        # 더 많은 대화 조회 (최대 limit개)
        history = await get_recent_conversations(user_id, limit=limit*2)  # limit*2로 쌍을 맞춤
        stats = await get_conversation_stats(user_id)
        
        return {
            "history": history,
            "stats": stats,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.exception(f"대화 히스토리 조회 오류 - 사용자: {user_id}")
        raise HTTPException(
            status_code=500,
            detail=f"히스토리 조회 오류: {str(e)}"
        )

@router.post("/reset")
async def reset_conversation_history(
    current_user: dict = Depends(get_current_user)
):
    """대화 히스토리 초기화"""
    user_id = str(current_user["_id"])
    
    try:
        cleared = await clear_user_conversation(user_id)
        
        if cleared:
            return {
                "success": True,
                "message": "대화 히스토리가 초기화되었습니다.",
                "timestamp": datetime.utcnow()
            }
        else:
            return {
                "success": False,
                "message": "초기화할 대화가 없습니다.",
                "timestamp": datetime.utcnow()
            }
    except Exception as e:
        logger.exception(f"대화 히스토리 초기화 오류 - 사용자: {user_id}")
        raise HTTPException(
            status_code=500,
            detail=f"초기화 오류: {str(e)}"
        )

@router.get("/stats")
async def get_conversation_statistics(
    current_user: dict = Depends(get_current_user)
):
    """대화 통계 조회"""
    user_id = str(current_user["_id"])
    
    try:
        stats = await get_conversation_stats(user_id)
        return {
            "stats": stats,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.exception(f"대화 통계 조회 오류 - 사용자: {user_id}")
        raise HTTPException(
            status_code=500,
            detail=f"통계 조회 오류: {str(e)}"
        )

@router.post("/debug/agent-test")
async def debug_agent_test(
    chat_request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """디버그용 Agent 테스트 엔드포인트"""
    user_id = str(current_user["_id"])
    
    try:
        # 사용자 Pod 정보 확인
        user = await get_user_by_id(user_id)
        if not user.get("pod_name"):
            return {
                "error": "Pod가 생성되지 않았습니다.",
                "user_id": user_id
            }
        
        pod_name = user["pod_name"]
        
        # 최신 대화 히스토리 조회
        recent_conversations = await get_recent_conversations(user_id, limit=6)
        
        # Agent에 전송할 데이터 구성
        agent_data = {
            "text": chat_request.message,
            "user_id": user_id,
        }
        
        if recent_conversations:
            agent_data["conversation_history"] = recent_conversations
            agent_data["use_conversation_context"] = True
        else:
            agent_data["new_conversation"] = True
        
        # kubectl + curl로 Agent 호출
        json_str = json.dumps(agent_data)
        cmd = [
            "kubectl", "exec", pod_name,
            "-n", "agent-env",
            "-c", "agent",
            "--",
            "curl", "-s", "-X", "POST",
            settings.AGENT_URL,
            "-H", "Content-Type: application/json",
            "-d", json_str
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        return {
            "request_data": agent_data,
            "pod_name": pod_name,
            "cmd_executed": ' '.join(cmd[:6]) + ' ... [JSON_DATA]',
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "has_history": bool(recent_conversations),
            "history_count": len(recent_conversations)
        }
        
    except Exception as e:
        logger.exception(f"Agent 테스트 오류 - 사용자: {user_id}")
        return {
            "error": str(e),
            "user_id": user_id
        }
