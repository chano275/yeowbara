import subprocess,json
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime
from routers.nosql_auth import get_current_user
from models.mcp_nosql import ChatRequest, ChatResponse
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


logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["챗봇"],
    responses={404: {"description": "Not found"}}
)

@router.post("/pod")
async def create_pod(current_user: dict = Depends(get_current_user)):
    user_id = str(current_user["_id"])
    
    # Pod 생성 함수 호출
    from core.create_pod import create_pod as c_create_pod
    try:
        # user_id만 전달하여 Pod 생성 함수 호출
        pod_result = await c_create_pod(user_id)
        
        if pod_result.get("success", False):
            logger.info(f"Pod 생성 성공 - 사용자: {user_id}, Pod: {pod_result.get('pod_name')}")
        else:
            logger.warning(f"Pod 생성 실패 - 사용자: {user_id}, 오류: {pod_result.get('message')}")
        
        # 중요: 결과 반환
        # return pod_result
        return {
            "success": True,
            "message": pod_result["message"]
        }
    
    except Exception as e:
        # Pod 생성 오류가 로그인을 방해하지 않도록 예외 처리
        logger.error(f"Pod 생성 중 예외 발생 - 사용자: {user_id}, 오류: {str(e)}")
        return {
            "success": False,
            "message": f"Pod 생성 중 오류 발생: {str(e)}",
            "pod_name": None
        }


# @router.post("/chat", response_model=ChatResponse)
# async def process_chat(chat_request: ChatRequest, current_user: dict = Depends(get_current_user)):
#     """사용자의 채팅 메시지를 처리하고 응답합니다."""
    
#     user_id = str(current_user["_id"])
    
#     from crud.nosql import get_user_by_id  
    
#     user = await get_user_by_id(user_id)
#     pod_name = user["pod_name"]

#     # 메시지에 특수문자가 있으면 JSON 파싱에 문제가 될 수 있으므로 이스케이프 처리
#     import json
#     escaped_message = json.dumps(chat_request.message)[1:-1]  # 따옴표 제거
    
#     cmd = [
#         "kubectl", "exec", pod_name, "-n", "agent-env", "-c", "agent","--", 
#         "curl", "-X", "POST", settings.AGENT_URL, 
#         "-H", "Content-Type: application/json", 
#         "-d", f'{{"text": "{escaped_message}"}}'
#     ]
    
#     result = subprocess.run(cmd, capture_output=True, text=True)
    
#     # 응답 처리
#     if result.returncode != 0:
#         return {
#             "response": f"명령어 실행 실패 (코드: {result.returncode}): {result.stderr}",
#             "timestamp": datetime.utcnow()
#         }
    
#     if not result.stdout.strip():
#         # stderr에 내용이 있다면 표시
#         if result.stderr.strip():
#             return {
#                 "response": f"응답이 비어있습니다. 오류 내용: {result.stderr}",
#                 "timestamp": datetime.utcnow()
#             }
#         else:
#             return {
#                 "response": "응답이 비어있습니다. (stderr도 비어있음)",
#                 "timestamp": datetime.utcnow()
#             }
    
#     # 응답이 있는 경우 처리
#     try:
#         # 원본 응답 내용 출력
#         stripped_stdout = result.stdout.strip()
#         logger.info(f"처리할 응답 내용: '{stripped_stdout}'")
        
#         # JSON 형식인지 확인
#         if stripped_stdout.startswith('{') and stripped_stdout.endswith('}'):
#             try:
#                 data = json.loads(stripped_stdout)
#                 logger.info(f"JSON 파싱 성공: {data}")
                
#                 if "response" in data:
#                     response_str = data["response"]
#                     # response가 문자열이고 JSON 형식인지 확인
#                     if isinstance(response_str, str) and response_str.startswith('{') and response_str.endswith('}'):
#                         try:
#                             inner_data = json.loads(response_str)
#                             logger.info(f"중첩 JSON 파싱 성공: {inner_data}")
                            
#                             if "response" in inner_data:
#                                 bot_response = inner_data["response"]
#                             else:
#                                 bot_response = str(inner_data)
#                         except json.JSONDecodeError as e:
#                             logger.error(f"중첩 JSON 파싱 실패: {e}")
#                             bot_response = response_str
#                     else:
#                         bot_response = response_str
#                 else:
#                     bot_response = str(data)
#             except json.JSONDecodeError as e:
#                 logger.error(f"JSON 파싱 실패: {e}")
#                 bot_response = stripped_stdout
#         else:
#             bot_response = stripped_stdout
#     except Exception as e:
#         logger.exception("응답 처리 중 예외 발생")
#         bot_response = f"응답 처리 중 예외 발생: {str(e)}"
    
#     return {
#         "response": bot_response,
#         "timestamp": datetime.utcnow()
#     }




@router.post("/chat", response_model=ConversationalChatResponse)
async def conversational_chat(
    chat_request: ChatRequest, 
    current_user: dict = Depends(get_current_user)
):
    """대화형 채팅을 처리합니다. DB에서 대화 히스토리를 관리합니다."""
    
    user_id = str(current_user["_id"])
    bot_response = None  # 초기값 설정
    
    try:
        logger.info(f"대화 요청 시작 - 사용자: {user_id}, 메시지: {chat_request.message}")
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
            f"{settings.AGENT_URL}-test",
            "-H", "Content-Type: application/json",
            "-d", json.dumps(agent_request, cls=DateTimeEncoder)
        ]
        logger.info(f"cmd 메시지 확인용 {cmd}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            logger.error(f"kubectl 명령 타임아웃 - 사용자: {user_id}")
            return ConversationalChatResponse(
            response="요청 처리 시간이 초과되었습니다. 다시 시도해주세요.",
            timestamp=datetime.now(),
            had_context=True,  # 항상 컨텍스트 포함
            session_info={"error": True, "error_type": "timeout"}
            )
        
        if result.returncode != 0:
            logger.error(f"kubectl 명령 실패 - 반환 코드: {result.returncode}")
            logger.error(f"오류 내용: {result.stderr}")
            return ConversationalChatResponse(
                response=f"명령 실행 실패: Agent와 통신할 수 없습니다.",
                timestamp=datetime.now(),
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
                bot_response = "Agent에서 빈 응답을 받았습니다."
                return ConversationalChatResponse(
                    response=bot_response,
                    timestamp=datetime.now(),
                    had_context=True,  # 항상 컨텍스트 포함
                    session_info={"error": True, "error_type": "empty_response"}
                )
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 오류: {e}")
            logger.error(f"원본 응답: {result.stdout}")
            bot_response = "Agent 응답을 파싱할 수 없습니다."
            return ConversationalChatResponse(
                response=bot_response,
                timestamp=datetime.now(),
                had_context=True,  # 항상 컨텍스트 포함
                session_info={
                    "error": True,
                    "error_type": "json_decode_error",
                    "raw_response": result.stdout[:200] + "..." if len(result.stdout) > 200 else result.stdout
                }
            )
        
        # DB에 대화 저장 (반드시 bot_response가 존재할 때만)
        if bot_response is not None:
            try:
                logger.info(f"대화 저장 시가 - 사용자: {user_id}, 메시지: {chat_request.message[:50]}..., 응답: {bot_response[:50]}...")
                
                await conversation_manager.add_message(
                    user_id=user_id,
                    user_message=chat_request.message,
                    assistant_response=bot_response
                )
                
                logger.info(f"대화 저장 성공 - 사용자: {user_id}")
            except Exception as save_error:
                logger.error(f"대화 저장 오류 - 사용자: {user_id}, 오류: {str(save_error)}")
                # 저장 오류가 발생해도 응답은 반환하도록 수정
        else:
            logger.warning(f"bot_response가 None이므로 대화를 저장하지 않음 - 사용자: {user_id}")
        
        # 대화 요약 정보 가져오기
        try:
            summary = await conversation_manager.get_conversation_summary(user_id)
        except Exception as summary_error:
            logger.error(f"대화 요약 조회 오류 - 사용자: {user_id}, 오류: {str(summary_error)}")
            summary = {"total_messages": 0, "has_history": False}
        
        return ConversationalChatResponse(
            response=bot_response if bot_response is not None else "알 수 없는 오류가 발생했습니다.",
            timestamp=datetime.now(),
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
            timestamp=datetime.now(),
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