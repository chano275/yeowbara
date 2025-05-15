import subprocess,json
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime
from routers.nosql_auth import get_current_user
from models.mcp_nosql import (
    ChatRequest, ChatResponse, ConversationalChatResponse,
    MessageRequest, SessionCreateRequest, SessionUpdateRequest, 
    SessionInfo, SessionListResponse
)
from core.config import settings
from crud.conversation import conversation_manager
import logging

# 커스텀 JSON 인코더
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

logger = logging.getLogger(__name__)

class ChatHistoryResponse(BaseModel):
    history: List[Dict[str, Any]]
    session_active: bool
    conversation_summary: Dict[str, Any]

router = APIRouter(
    tags=["챗봇"],
    responses={404: {"description": "Not found"}}
)

# 세션 관리 엔드포인트들
@router.post("/sessions", response_model=Dict[str, str])
async def create_session(
    session_request: SessionCreateRequest,
    current_user: dict = Depends(get_current_user)
):
    """새로운 대화 세션을 생성합니다."""
    user_id = str(current_user["_id"])
    
    try:
        session_id = await conversation_manager.create_session(
            user_id=user_id,
            session_name=session_request.session_name
        )
        
        return {
            "session_id": session_id,
            "session_name": session_request.session_name,
            "message": "새 세션이 생성되었습니다."
        }
    except Exception as e:
        logger.error(f"세션 생성 오류: {e}")
        raise HTTPException(status_code=500, detail=f"세션 생성 실패: {str(e)}")

@router.get("/sessions", response_model=SessionListResponse)
async def get_sessions(current_user: dict = Depends(get_current_user)):
    """사용자의 모든 세션 목록을 조회합니다."""
    user_id = str(current_user["_id"])
    
    try:
        sessions = await conversation_manager.get_user_sessions(user_id)
        return SessionListResponse(sessions=sessions)
    except Exception as e:
        logger.error(f"세션 목록 조회 오류: {e}")
        raise HTTPException(status_code=500, detail=f"세션 목록 조회 실패: {str(e)}")

@router.put("/sessions/{session_id}")
async def update_session(
    session_id: str,
    session_request: SessionUpdateRequest,
    current_user: dict = Depends(get_current_user)
):
    """세션 이름을 변경합니다."""
    user_id = str(current_user["_id"])
    
    try:
        success = await conversation_manager.update_session_name(
            user_id=user_id,
            session_id=session_id,
            new_name=session_request.session_name
        )
        
        if success:
            return {
                "message": "세션 이름이 변경되었습니다.",
                "session_id": session_id,
                "session_name": session_request.session_name
            }
        else:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"세션 이름 변경 오류: {e}")
        raise HTTPException(status_code=500, detail=f"세션 이름 변경 실패: {str(e)}")

@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """세션을 삭제합니다."""
    user_id = str(current_user["_id"])
    
    try:
        success = await conversation_manager.delete_session(
            user_id=user_id,
            session_id=session_id
        )
        
        if success:
            return {"message": "세션이 삭제되었습니다.", "session_id": session_id}
        else:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"세션 삭제 오류: {e}")
        raise HTTPException(status_code=500, detail=f"세션 삭제 실패: {str(e)}")

@router.post("/sessions/{session_id}/reset")
async def reset_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """특정 세션의 대화를 초기화합니다."""
    user_id = str(current_user["_id"])
    
    try:
        deleted_count = await conversation_manager.clear_session_history(user_id, session_id)
        logger.info(f"세션 초기화 완료 - 사용자: {user_id}, 세션: {session_id}")
        
        return {
            "success": True,
            "message": f"세션이 초기화되었습니다.",
            "session_id": session_id,
            "deleted_count": deleted_count
        }
    except Exception as e:
        logger.error(f"세션 초기화 오류: {e}")
        return {
            "success": False,
            "message": f"세션 초기화 중 오류 발생: {str(e)}"
        }

@router.get("/sessions/{session_id}/history", response_model=ChatHistoryResponse)
async def get_session_history(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """특정 세션의 대화 히스토리를 조회합니다."""
    user_id = str(current_user["_id"])
    
    try:
        # 세션 대화 히스토리 가져오기
        history = await conversation_manager.get_conversation_history(
            user_id, limit=50, session_id=session_id
        )
        summary = await conversation_manager.get_session_summary(user_id, session_id)
        
        return ChatHistoryResponse(
            history=history,
            session_active=summary["has_history"],
            conversation_summary=summary
        )
    except Exception as e:
        logger.error(f"세션 히스토리 조회 오류: {e}")
        return ChatHistoryResponse(
            history=[],
            session_active=False,
            conversation_summary={"error": str(e), "has_history": False}
        )

@router.post("/sessions/{session_id}/chat", response_model=ConversationalChatResponse)
async def session_chat(
    session_id: str,
    message_request: MessageRequest,  # MessageRequest 사용 (session_id 없음)
    current_user: dict = Depends(get_current_user)
):
    """특정 세션에서 대화를 진행합니다."""
    user_id = str(current_user["_id"])
    bot_response = None
    
    try:
        logger.info(f"세션 대화 요청 - 사용자: {user_id}, 세션: {session_id}, 메시지: {message_request.message}")
        
        # 사용자 정보 조회
        from crud.nosql import get_user_by_id
        user = await get_user_by_id(user_id)
        
        if not user.get("pod_name"):
            raise HTTPException(
                status_code=400, 
                detail="Pod가 생성되지 않았습니다. 먼저 /pod 엔드포인트를 호출해주세요."
            )
        
        pod_name = user["pod_name"]
        
        # 특정 세션의 대화 히스토리 가져오기
        conversation_history = await conversation_manager.get_conversation_history(
            user_id, limit=6, session_id=session_id
        )
        
        # 세션 정보 가져오기
        session_summary = await conversation_manager.get_session_summary(user_id, session_id)
        
        # Agent에 요청
        agent_request = {
            "text": message_request.message,
            "user_id": user_id,
            "conversation_history": conversation_history,
            "use_conversation_context": True,
            "session_id": session_id
        }
        
        logger.info(f"세션 메시지 처리 - 사용자: {user_id}, 세션: {session_id}, 히스토리: {len(conversation_history)}개")
        
        cmd = [
            "kubectl", "exec", pod_name, 
            "-n", "agent-env", 
            "-c", "agent", 
            "--", 
            "curl", "-s", "-X", "POST", 
            settings.AGENT_URL,
            "-H", "Content-Type: application/json",
            "-d", json.dumps(agent_request, cls=DateTimeEncoder)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            logger.error(f"kubectl 명령 타임아웃 - 사용자: {user_id}, 세션: {session_id}")
            return ConversationalChatResponse(
                response="요청 처리 시간이 초과되었습니다. 다시 시도해주세요.",
                timestamp=datetime.now(),
                session_id=session_id,
                session_name=session_summary.get("session_name", "알 수 없음"),
                had_context=True
            )
        
        if result.returncode != 0:
            logger.error(f"kubectl 명령 실패 - 반환 코드: {result.returncode}")
            logger.error(f"오류 내용: {result.stderr}")
            return ConversationalChatResponse(
                response=f"명령 실행 실패: Agent와 통신할 수 없습니다.",
                timestamp=datetime.now(),
                session_id=session_id,
                session_name=session_summary.get("session_name", "알 수 없음"),
                had_context=True
            )
        
        # 응답 처리
        try:
            if result.stdout.strip():
                response_data = json.loads(result.stdout)
                bot_response = response_data.get("response", result.stdout.strip())
                
                # 응답에 에러가 포함되어 있는지 확인
                if "error" in response_data.get("error", "").lower() or "Error" in bot_response:
                    # 에러 메시지를 요약하기 위해 다시 Agent에 요청
                    error_summary_request = {
                        "text": f"다음 에러 메시지를 사용자가 이해하기 쉽게 간단히 설명해주세요. 기술적인 용어는 피하고 문제 상황과 해결 방법을 제시해주세요: {bot_response}",
                        "user_id": user_id,
                        "conversation_history": [],
                        "use_conversation_context": False,
                        "is_error_summary": True
                    }
                    
                    # 에러 요약 요청
                    error_cmd = [
                        "kubectl", "exec", pod_name, 
                        "-n", "agent-env", 
                        "-c", "agent", 
                        "--", 
                        "curl", "-s", "-X", "POST", 
                        settings.AGENT_URL,
                        "-H", "Content-Type: application/json",
                        "-d", json.dumps(error_summary_request, cls=DateTimeEncoder)
                    ]
                    
                    try:
                        error_result = subprocess.run(error_cmd, capture_output=True, text=True, timeout=30)
                        if error_result.returncode == 0 and error_result.stdout.strip():
                            error_response_data = json.loads(error_result.stdout)
                            summarized_error = error_response_data.get("response", bot_response)
                            logger.info(f"에러 메시지 요약 완료: user_id={user_id}")
                            bot_response = summarized_error
                        else:
                            logger.warning(f"에러 요약 실패, 원본 메시지 사용: user_id={user_id}")
                    except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
                        logger.warning(f"에러 요약 중 오류, 원본 메시지 사용: {str(e)}")
                        
            else:
                logger.warning(f"빈 응답 - 사용자: {user_id}, 세션: {session_id}")
                bot_response = "죄송합니다. 응답을 생성할 수 없었습니다. 다시 시도해 주세요."
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 오류: {e}")
            logger.error(f"원본 응답: {result.stdout}")
            bot_response = "Agent 응답을 파싱할 수 없습니다."
        
        # 세션에 대화 저장
        if bot_response is not None:
            try:
                logger.info(f"세션 대화 저장 - 사용자: {user_id}, 세션: {session_id}")
                
                await conversation_manager.add_message(
                    user_id=user_id,
                    user_message=message_request.message,
                    assistant_response=bot_response,
                    session_id=session_id
                )
                
                logger.info(f"세션 대화 저장 성공 - 사용자: {user_id}, 세션: {session_id}")
            except Exception as save_error:
                logger.error(f"세션 대화 저장 오류 - 사용자: {user_id}, 세션: {session_id}, 오류: {str(save_error)}")
        
        # 업데이트된 세션 요약 정보 가져오기
        try:
            updated_summary = await conversation_manager.get_session_summary(user_id, session_id)
        except Exception as summary_error:
            logger.error(f"세션 요약 조회 오류: {summary_error}")
            updated_summary = session_summary
        
        return ConversationalChatResponse(
            response=bot_response if bot_response is not None else "알 수 없는 오류가 발생했습니다.",
            timestamp=datetime.now(),
            session_id=session_id,
            session_name=updated_summary.get("session_name", "알 수 없음"),
            conversation_count=updated_summary.get("total_messages", 0),
            had_context=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"세션 대화 처리 중 오류 발생 - 사용자: {user_id}, 세션: {session_id}")
        
        # 세션 정보 가져오기 시도
        try:
            session_summary = await conversation_manager.get_session_summary(user_id, session_id)
            session_name = session_summary.get("session_name", "알 수 없음")
        except:
            session_name = "알 수 없음"
        
        return ConversationalChatResponse(
            response=f"대화 처리 중 오류가 발생했습니다: {str(e)}",
            timestamp=datetime.now(),
            session_id=session_id,
            session_name=session_name,
            had_context=False
        )

# 기존 엔드포인트들
@router.post("/pod")
async def create_pod(current_user: dict = Depends(get_current_user)):
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
    chat_request: ChatRequest,  # ChatRequest 사용 (session_id 포함 가능)
    current_user: dict = Depends(get_current_user)
):
    """기본 세션에서 대화를 진행합니다. ChatRequest에 session_id가 있으면 해당 세션 사용."""
    user_id = str(current_user["_id"])
    
    # session_id가 제공되면 특정 세션 사용, 아니면 default 세션 사용
    session_id = chat_request.session_id
    if not session_id:
        # default 세션 찾기 또는 생성
        default_session = await conversation_manager._get_or_create_default_session(user_id)
        session_id = default_session
    
    # MessageRequest로 변환하여 세션 기반 대화 엔드포인트로 위임
    message_request = MessageRequest(message=chat_request.message)
    return await session_chat(session_id, message_request, current_user)

@router.get("/chat/history", response_model=ChatHistoryResponse)
async def get_conversation_history(current_user: dict = Depends(get_current_user)):
    """기본 세션의 대화 히스토리를 조회합니다."""
    user_id = str(current_user["_id"])
    
    try:
        # default 세션 찾기 또는 생성
        default_session = await conversation_manager._get_or_create_default_session(user_id)
        
        # 기본 세션 히스토리 조회
        history = await conversation_manager.get_conversation_history(
            user_id, limit=50, session_id=default_session
        )
        summary = await conversation_manager.get_session_summary(user_id, default_session)
        
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
    """기본 세션의 대화를 초기화합니다."""
    user_id = str(current_user["_id"])
    
    try:
        # default 세션 찾기 또는 생성
        default_session = await conversation_manager._get_or_create_default_session(user_id)
        
        deleted_count = await conversation_manager.clear_session_history(user_id, default_session)
        logger.info(f"기본 세션 초기화 완료 - 사용자: {user_id}")
        
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