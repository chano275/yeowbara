import subprocess
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
from routers.nosql_auth import get_current_user
from models.mcp_nosql import ChatRequest, ChatResponse
from core.config import settings
from crud.conversation import conversation_manager
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
    """대화형 채팅을 처리합니다. DB에서 대화 히스토리를 관리합니다."""
    
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
        
        # DB에서 최대 6개의 대화 히스토리 가져오기
        conversation_history = await conversation_manager.get_conversation_history(user_id, limit=6)
        
        # 무조건 대화 히스토리 포함하여 전송
        agent_request = {
            "text": chat_request.message,
            "user_id": user_id,
            "conversation_history": conversation_history,
            "use_conversation_context": True  # 항상 True
        }
        
        # Agent에 요청
        logger.info(f"메시지 처리 시작 - 사용자: {user_id}, 대화 히스토리: {len(conversation_history)}개")
        
        cmd = [
            "kubectl", "exec", pod_name, 
            "-n", "agent-env", 
            "-c", "agent", 
            "--", 
            "curl", "-s", "-X", "POST", 
            f'{settings.AGENT_URL}-test',
            "-H", "Content-Type: application/json",
            "-d", json.dumps(agent_request)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            logger.error(f"kubectl 명령 타임아웃 - 사용자: {user_id}")
            return ConversationalChatResponse(
                response="요청 처리 시간이 초과되었습니다. 다시 시도해주세요.",
                timestamp=datetime.utcnow(),
                had_context=True,  # 항상 컨텍스트 포함
                session_info={"error": True, "error_type": "timeout"}
            )
        
        if result.returncode != 0:
            logger.error(f"kubectl 명령 실패 - 반환 코드: {result.returncode}")
            logger.error(f"오류 내용: {result.stderr}")
            return ConversationalChatResponse(
                response=f"명령 실행 실패: Agent와 통신할 수 없습니다.",
                timestamp=datetime.utcnow(),
                had_context=True,  # 항상 컨텍스트 포함
                session_info={"error": True, "error_type": "agent_communication"}
            )
        
        # 응답 처리
        try:
            if result.stdout.strip():
                response_data = json.loads(result.stdout)
                bot_response = response_data.get("response", result.stdout.strip())
            else:
                logger.warning(f"빈 응답 - 사용자: {user_id}")
                return ConversationalChatResponse(
                    response="Agent에서 빈 응답을 받았습니다.",
                    timestamp=datetime.utcnow(),
                    had_context=True,  # 항상 컨텍스트 포함
                    session_info={"error": True, "error_type": "empty_response"}
                )
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 오류: {e}")
            logger.error(f"원본 응답: {result.stdout}")
            return ConversationalChatResponse(
                response="Agent 응답을 파싱할 수 없습니다.",
                timestamp=datetime.utcnow(),
                had_context=True,  # 항상 컨텍스트 포함
                session_info={
                    "error": True,
                    "error_type": "json_decode_error",
                    "raw_response": result.stdout[:200] + "..." if len(result.stdout) > 200 else result.stdout
                }
            )
        
        # DB에 대화 저장
        await conversation_manager.add_message(
            user_id=user_id,
            user_message=chat_request.message,
            assistant_response=bot_response
        )
        
        # 대화 요약 정보 가져오기
        summary = await conversation_manager.get_conversation_summary(user_id)
        
        return ConversationalChatResponse(
            response=bot_response,
            timestamp=datetime.utcnow(),
            had_context=True,  # 항상 컨텍스트 포함
            session_info={
                "db_managed": True,
                "conversation_summary": summary,
                "history_sent": len(conversation_history)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"대화 처리 중 오류 발생 - 사용자: {user_id}")
        
        return ConversationalChatResponse(
            response=f"대화 처리 중 오류가 발생했습니다: {str(e)}",
            timestamp=datetime.utcnow(),
            had_context=False,
            session_info={"error": True, "error_type": "internal_error"}
        )

@router.get("/chat/history", response_model=ChatHistoryResponse)
async def get_conversation_history(current_user: dict = Depends(get_current_user)):
    """대화 히스토리를 조회합니다. (DB에서 관리)"""
    user_id = str(current_user["_id"])
    
    try:
        # DB에서 대화 히스토리 가져오기
        history = await conversation_manager.get_conversation_history(user_id, limit=50)
        summary = await conversation_manager.get_conversation_summary(user_id)
        
        return ChatHistoryResponse(
            history=history,
            session_active=summary["has_history"],
            conversation_summary=summary
        )
    except Exception as e:
        logger.error(f"대화 히스토리 조회 오류: {e}")
        return ChatHistoryResponse(
            history=[],
            session_active=False,
            conversation_summary={"error": str(e), "has_history": False}
        )

@router.post("/chat/reset")
async def reset_conversation(current_user: dict = Depends(get_current_user)):
    """대화를 초기화합니다. (DB에서 삭제)"""
    user_id = str(current_user["_id"])
    
    try:
        deleted_count = await conversation_manager.clear_conversation_history(user_id)
        logger.info(f"대화 초기화 완료 - 사용자: {user_id}, 삭제된 메시지: {deleted_count}")
        
        return {
            "success": True,
            "message": f"대화가 초기화되었습니다. ({deleted_count}개 메시지 삭제)",
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.error(f"대화 초기화 오류: {e}")
        return {
            "success": False,
            "message": f"대화 초기화 중 오류 발생: {str(e)}"
        }

@router.get("/chat/status")
async def get_conversation_status(current_user: dict = Depends(get_current_user)):
    """현재 대화 상태를 조회합니다. (DB 기반)"""
    user_id = str(current_user["_id"])
    
    try:
        summary = await conversation_manager.get_conversation_summary(user_id)
        
        return {
            "user_id": user_id,
            "conversation_summary": {
                **summary,
                "managed_by": "database"
            },
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"대화 상태 조회 오류: {e}")
        return {
            "user_id": user_id,
            "conversation_summary": {"error": str(e), "managed_by": "database"},
            "timestamp": datetime.utcnow()
        }

# 개발/디버깅 엔드포인트들은 그대로 유지
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
    """메시지와 대화 히스토리 정보를 분석합니다 (디버깅용)."""
    user_id = str(current_user["_id"])
    text = message.get("text", "")
    
    # DB에서 최근 6개 대화 가져오기
    history = await conversation_manager.get_conversation_history(user_id, limit=6)
    
    return {
        "message": text,
        "always_send_context": True,  # 항상 전송
        "history_count": len(history),
        "analysis": {
            "contains_pronouns": any(pronoun in text.lower() for pronoun in ['그것', '그거', '이것', '이거', '그 프로젝트']),
            "is_question": '?' in text,
            "has_temporal_reference": any(ref in text.lower() for ref in ['방금', '아까', '전에']),
            "note": "컨텍스트 자동 판단을 제거했으므로 항상 대화 히스토리를 전송합니다."
        }
    }

@router.post("/debug/context-test")
async def debug_context_test(
    chat_request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """컨텍스트 구성과 전달을 디버깅합니다."""
    user_id = str(current_user["_id"])
    
    # DB에서 최대 6개 대화 히스토리 가져오기
    history = await conversation_manager.get_conversation_history(user_id, limit=6)
    
    # Agent로 전달될 데이터 구성 (항상 컨텍스트 포함)
    agent_request = {
        "text": chat_request.message,
        "user_id": user_id,
        "conversation_history": history,
        "use_conversation_context": True  # 항상 True
    }
    
    return {
        "message": chat_request.message,
        "always_sends_context": True,  # 항상 전송
        "history_count": len(history),
        "agent_request": agent_request,
        "recent_conversations": [
            {
                "user": item["user"][:50] + "..." if len(item["user"]) > 50 else item["user"],
                "assistant": item["assistant"][:50] + "..." if len(item["assistant"]) > 50 else item["assistant"]
            }
            for item in history[-3:]
        ],
        "note": "컨텍스트 필요성 판단을 제거하여 항상 최대 6개의 대화 히스토리를 전송합니다."
    }
