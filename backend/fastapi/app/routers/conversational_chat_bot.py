import subprocess
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from routers.nosql_auth import get_current_user
from models.mcp_nosql import ChatRequest, ChatResponse
from core.config import settings
from core.smart_session_manager import smart_session_manager
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# 응답 모델 확장
class ConversationalChatResponse(BaseModel):
    response: str
    timestamp: datetime
    had_context: bool = False
    session_info: Optional[Dict[str, Any]] = None

class ChatHistoryResponse(BaseModel):
    history: List[Dict[str, Any]]
    session_active: bool
    conversation_summary: Dict[str, Any]

router = APIRouter(
    prefix="/conversational",
    tags=["대화형 챗봇"],
    responses={404: {"description": "Not found"}}
)

@router.post("/pod")
async def create_pod(current_user: dict = Depends(get_current_user)):
    """Pod를 생성합니다."""
    user_id = str(current_user["_id"])
    
    # Pod 생성 함수 호출
    from core.create_pod import create_pod as c_create_pod
    try:
        pod_result = await c_create_pod(user_id)
        
        if pod_result.get("success", False):
            logger.info(f"Pod 생성 성공 - 사용자: {user_id}, Pod: {pod_result.get('pod_name')}")
        else:
            logger.warning(f"Pod 생성 실패 - 사용자: {user_id}, 오류: {pod_result.get('message')}")
        
        return {
            "success": True,
            "message": pod_result["message"]
        }
    
    except Exception as e:
        logger.error(f"Pod 생성 중 예외 발생 - 사용자: {user_id}, 오류: {str(e)}")
        return {
            "success": False,
            "message": f"Pod 생성 중 오류 발생: {str(e)}",
            "pod_name": None
        }

@router.post("/chat", response_model=ConversationalChatResponse)
async def conversational_chat(
    chat_request: ChatRequest, 
    current_user: dict = Depends(get_current_user)
):
    """대화형 채팅을 처리합니다. 자동으로 컨텍스트 필요성을 판단하여 처리합니다."""
    
    user_id = str(current_user["_id"])
    
    try:
        # 사용자 정보 조회
        from crud.nosql import get_user_by_id
        user = await get_user_by_id(user_id)
        
        if not user.get("pod_name"):
            raise HTTPException(
                status_code=400, 
                detail="Pod가 생성되지 않았습니다. 먼저 /conversational/pod 엔드포인트를 호출해주세요."
            )
        
        pod_name = user["pod_name"]
        
        # 세션 가져오기 또는 생성
        await smart_session_manager.get_or_create_session(user_id, pod_name)
        
        # 스마트한 메시지 처리
        result = await smart_session_manager.send_message(user_id, chat_request.message)
        
        if result.get("error"):
            return ConversationalChatResponse(
                response=result["response"],
                timestamp=datetime.utcnow(),
                had_context=False,
                session_info={"error": True}
            )
        
        # 세션 정보 추가
        session_info = smart_session_manager.get_conversation_summary(user_id)
        
        return ConversationalChatResponse(
            response=result["response"],
            timestamp=datetime.utcnow(),
            had_context=result["had_context"],
            session_info=session_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"대화 처리 중 오류 발생 - 사용자: {user_id}")
        
        return ConversationalChatResponse(
            response=f"대화 처리 중 오류가 발생했습니다: {str(e)}",
            timestamp=datetime.utcnow(),
            had_context=False,
            session_info={"error": True}
        )

@router.get("/chat/history", response_model=ChatHistoryResponse)
async def get_conversation_history(current_user: dict = Depends(get_current_user)):
    """대화 히스토리를 조회합니다."""
    user_id = str(current_user["_id"])
    
    if user_id not in smart_session_manager.sessions:
        return ChatHistoryResponse(
            history=[],
            session_active=False,
            conversation_summary={"active": False}
        )
    
    session = smart_session_manager.sessions[user_id]
    summary = smart_session_manager.get_conversation_summary(user_id)
    
    return ChatHistoryResponse(
        history=session["history"],
        session_active=True,
        conversation_summary=summary
    )

@router.post("/chat/reset")
async def reset_conversation(current_user: dict = Depends(get_current_user)):
    """대화를 초기화합니다."""
    user_id = str(current_user["_id"])
    
    try:
        await smart_session_manager.reset_session(user_id)
        return {
            "success": True,
            "message": "대화가 초기화되었습니다."
        }
    except Exception as e:
        logger.error(f"대화 초기화 오류: {e}")
        return {
            "success": False,
            "message": f"대화 초기화 중 오류 발생: {str(e)}"
        }

@router.get("/chat/status")
async def get_conversation_status(current_user: dict = Depends(get_current_user)):
    """현재 대화 상태를 조회합니다."""
    user_id = str(current_user["_id"])
    summary = smart_session_manager.get_conversation_summary(user_id)
    
    return {
        "user_id": user_id,
        "conversation_summary": summary,
        "timestamp": datetime.utcnow()
    }

@router.get("/debug/pod-status")
async def check_pod_status(current_user: dict = Depends(get_current_user)):
    """사용자의 Pod 상태를 확인합니다."""
    user_id = str(current_user["_id"])
    
    try:
        from crud.nosql import get_user_by_id
        user = await get_user_by_id(user_id)
        
        if not user.get("pod_name"):
            return {
                "success": False,
                "message": "Pod가 생성되지 않았습니다.",
                "pod_name": None
            }
        
        pod_name = user["pod_name"]
        
        # Pod 상태 확인
        cmd_status = ["kubectl", "get", "pod", pod_name, "-n", "agent-env", "-o", "json"]
        result_status = subprocess.run(cmd_status, capture_output=True, text=True)
        
        if result_status.returncode != 0:
            return {
                "success": False,
                "message": f"Pod 상태 확인 실패: {result_status.stderr}",
                "pod_name": pod_name
            }
        
        # Pod 로그 상태 확인
        cmd_logs = ["kubectl", "logs", pod_name, "-n", "agent-env", "-c", "agent", "--tail=10"]
        result_logs = subprocess.run(cmd_logs, capture_output=True, text=True)
        
        # Pod 내부 서비스 확인
        cmd_test = [
            "kubectl", "exec", pod_name, "-n", "agent-env", "-c", "agent", "--",
            "curl", "-s", settings.AGENT_URL
        ]
        result_test = subprocess.run(cmd_test, capture_output=True, text=True)
        
        try:
            pod_status = json.loads(result_status.stdout)
            status_info = {
                "phase": pod_status.get("status", {}).get("phase"),
                "ready": False,
                "conditions": []
            }
            
            conditions = pod_status.get("status", {}).get("conditions", [])
            for condition in conditions:
                if condition.get("type") == "Ready":
                    status_info["ready"] = condition.get("status") == "True"
                status_info["conditions"].append({
                    "type": condition.get("type"),
                    "status": condition.get("status")
                })
        except json.JSONDecodeError:
            status_info = {"error": "Pod 상태 파싱 실패"}
        
        return {
            "success": True,
            "pod_name": pod_name,
            "status": status_info,
            "logs": result_logs.stdout[-500:] if result_logs.returncode == 0 else result_logs.stderr,
            "service_test": {
                "success": result_test.returncode == 0,
                "response": result_test.stdout if result_test.returncode == 0 else result_test.stderr
            }
        }
        
    except Exception as e:
        logger.exception(f"Pod 상태 확인 중 오류: {e}")
        return {
            "success": False,
            "message": f"오류 발생: {str(e)}"
        }

@router.post("/chat/analyze")
async def analyze_message_context(
    message: dict,  # {"text": "메시지 내용"}
    current_user: dict = Depends(get_current_user)
):
    """메시지의 컨텍스트 필요성을 미리 분석합니다 (디버깅용)."""
    user_id = str(current_user["_id"])
    text = message.get("text", "")
    
    if user_id not in smart_session_manager.sessions:
        return {
            "needs_context": False,
            "reason": "세션이 없음",
            "analysis": {}
        }
    
    session = smart_session_manager.sessions[user_id]
    needs_context, context = smart_session_manager.analyze_message_context(text, session["history"])
    
    return {
        "needs_context": needs_context,
        "context_preview": context[:200] + "..." if len(context) > 200 else context,
        "analysis": {
            "message_length": len(text),
            "history_length": len(session["history"]),
            "patterns_detected": "검출된 패턴 분석 결과"
        }
    }
