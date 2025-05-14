import subprocess,json
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from pydantic import BaseModel
from datetime import datetime
from routers.nosql_auth import get_current_user
from models.mcp_nosql import ChatRequest, ChatResponse
from core.config import settings
import logging

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


@router.post("/chat", response_model=ChatResponse)
async def process_chat(chat_request: ChatRequest, current_user: dict = Depends(get_current_user)):
    """사용자의 채팅 메시지를 처리하고 응답합니다."""
    
    user_id = str(current_user["_id"])
    
    from crud.nosql import get_user_by_id  
    
    user = await get_user_by_id(user_id)
    pod_name = user["pod_name"]

    # 메시지에 특수문자가 있으면 JSON 파싱에 문제가 될 수 있으므로 이스케이프 처리
    import json
    escaped_message = json.dumps(chat_request.message)[1:-1]  # 따옴표 제거
    
    cmd = [
        "kubectl", "exec", pod_name, "-n", "agent-env", "-c", "agent","--", 
        "curl", "-X", "POST", settings.AGENT_URL, 
        "-H", "Content-Type: application/json", 
        "-d", f'{{"text": "{escaped_message}"}}'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # 응답 처리
    if result.returncode != 0:
        return {
            "response": f"명령어 실행 실패 (코드: {result.returncode}): {result.stderr}",
            "timestamp": datetime.utcnow()
        }
    
    if not result.stdout.strip():
        # stderr에 내용이 있다면 표시
        if result.stderr.strip():
            return {
                "response": f"응답이 비어있습니다. 오류 내용: {result.stderr}",
                "timestamp": datetime.utcnow()
            }
        else:
            return {
                "response": "응답이 비어있습니다. (stderr도 비어있음)",
                "timestamp": datetime.utcnow()
            }
    
    # 응답이 있는 경우 처리
    try:
        # 원본 응답 내용 출력
        stripped_stdout = result.stdout.strip()
        logger.info(f"처리할 응답 내용: '{stripped_stdout}'")
        
        # JSON 형식인지 확인
        if stripped_stdout.startswith('{') and stripped_stdout.endswith('}'):
            try:
                data = json.loads(stripped_stdout)
                logger.info(f"JSON 파싱 성공: {data}")
                
                if "response" in data:
                    response_str = data["response"]
                    # response가 문자열이고 JSON 형식인지 확인
                    if isinstance(response_str, str) and response_str.startswith('{') and response_str.endswith('}'):
                        try:
                            inner_data = json.loads(response_str)
                            logger.info(f"중첩 JSON 파싱 성공: {inner_data}")
                            
                            if "response" in inner_data:
                                bot_response = inner_data["response"]
                            else:
                                bot_response = str(inner_data)
                        except json.JSONDecodeError as e:
                            logger.error(f"중첩 JSON 파싱 실패: {e}")
                            bot_response = response_str
                    else:
                        bot_response = response_str
                else:
                    bot_response = str(data)
            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 실패: {e}")
                bot_response = stripped_stdout
        else:
            bot_response = stripped_stdout
    except Exception as e:
        logger.exception("응답 처리 중 예외 발생")
        bot_response = f"응답 처리 중 예외 발생: {str(e)}"
    
    return {
        "response": bot_response,
        "timestamp": datetime.utcnow()
    }