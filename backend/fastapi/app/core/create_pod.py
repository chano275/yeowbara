import subprocess, json, os, asyncio, logging
from typing import Dict, Any
from crud.nosql import get_user_by_id, update_pod_name, get_env_vars, get_user_selected_mcps
from core.config import settings

# 로깅 설정
logger = logging.getLogger(__name__)

# Pod 배포 서버 주소 설정
DEPLOY_SERVER_URL = f"{settings.DEPLOY_SERVER_URL}/deploy"

async def create_pod(user_id: str) -> Dict[str, Any]:
    """
    사용자 ID를 기반으로 Pod를 생성하고, 생성된 Pod 이름을 DB에 저장합니다.
    
    Args:
        user_id: 사용자의 ID (UUID 문자열)
        
    Returns:
        Dict[str, Any]: 생성 결과 정보 (pod_name 포함)
    """
    try:
        # 사용자 정보 조회 - 존재 여부만 확인
        user = await get_user_by_id(user_id)
        if not user:
            return {
                "success": False,
                "message": f"사용자 ID({user_id})에 해당하는 사용자를 찾을 수 없습니다.",
                "pod_name": None
            }
        
        # 환경 변수 목록 구성
        env_vars_list = []
        
        # 기본 환경 변수 추가
        # env_vars_list.append({"name":"GMS_KEY","value":settings.GMS_KEY})
        # env_vars_list.append({"name":"GMS_API_BASE","value":settings.GMS_API_BASE})
        env_vars_list.append({"name":"OPENAI_API_KEY","value":settings.OPENAI_API_KEY})
        
        # 사용자가 선택한 MCP 서비스 목록 가져오기
        selected_mcps = await get_user_selected_mcps(user_id)
        if selected_mcps:
            # 선택한 MCP 타입들을 콤마로 구분된 문자열로 저장
            mcp_types = []
            for mcp in selected_mcps:
                mcp_type = mcp.get("mcp_type")
                if mcp_type and mcp_type not in mcp_types:
                    mcp_types.append(mcp_type)
            
            # MCP_SERVICES 환경 변수로 추가
            if mcp_types:
                mcp_services_value = ",".join(mcp_types)
                env_vars_list.append({"name": "MCP_SERVICES", "value": mcp_services_value})
                logger.info(f"사용자 {user_id}의 MCP 서비스: {mcp_services_value}")
        else:
            # MCP가 없는 경우에도 빈 값을 설정하거나 기본값 설정
            env_vars_list.append({"name": "MCP_SERVICES", "value": " "})
            logger.info(f"사용자 {user_id}에게 선택된 MCP가 없습니다. 빈 MCP_SERVICES로 진행합니다.")
        
        # 사용자가 설정한 환경 변수 조회 및 추가
        user_env_settings = await get_env_vars(user_id)
        if user_env_settings:
            for mcp_id, mcp_env_vars in user_env_settings.items():
                for key, value in mcp_env_vars.items():
                    # 키에 공백 제거 및 대문자로 변환 (Kubernetes 환경변수 네이밍 규칙)
                    env_key = key.strip().upper().replace(' ', '_')
                    # 중복 방지
                    if not any(env["name"] == env_key for env in env_vars_list):
                        env_vars_list.append({"name": env_key, "value": value})
        
        # Pod 생성 요청 데이터 구성
        deploy_data = {
            "user_id": user_id,  # UUID 기반 사용자 ID 사용
            "env": env_vars_list
        }
        
        # JSON 데이터로 변환
        json_data = json.dumps(deploy_data)
        
        logger.info(f"Pod 생성 요청 - 사용자: {user_id}")
        
        # curl 명령어 구성 및 실행
        cmd = [
            "curl", "-X", "POST", DEPLOY_SERVER_URL,
            "-H", "Content-Type: application/json",
            "-d", json_data
        ]
        
        # 명령어 실행
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # 결과 처리
        if result.returncode != 0:
            logger.error(f"Pod 생성 중 오류 발생 - 사용자: {user_id}, 오류: {result.stderr}")
            return {
                "success": False, 
                "message": f"Pod 생성 중 오류 발생: {result.stderr}",
                "pod_name": None
            }
        
        # 응답에서 pod_name 추출
        try:            
            response_data = json.loads(result.stdout)
            pod_name = response_data.get("pod_name")
            
            if pod_name:
                # DB에 pod_name 업데이트
                update_success = await update_pod_name(user_id, pod_name)
                logger.info(f"pod_name: {pod_name}")
                if not update_success:
                    logger.warning(f"pod_name 업데이트 실패 - 사용자: {user_id}, Pod: {pod_name}")
                else:
                    logger.info(f"pod_name 업데이트 성공 - 사용자: {user_id}, Pod: {pod_name}")
            else:
                logger.warning(f"Pod 생성 응답에 pod_name이 없음 - 사용자: {user_id}, 응답: {result.stdout}")
            
            return {
                "success": True,
                "pod_name": pod_name,
                "message": "Pod가 성공적으로 생성되었습니다."
            }
        except json.JSONDecodeError:
            logger.error(f"Pod 생성 응답 파싱 오류 - 사용자: {user_id}, 응답: {result.stdout}")
            return {
                "success": False, 
                "message": f"Pod 생성 응답을 파싱할 수 없습니다: {result.stdout}",
                "pod_name": None
            }
    
    except Exception as e:
        logger.error(f"Pod 생성 중 예외 발생 - 사용자: {user_id}, 오류: {str(e)}")
        return {
            "success": False, 
            "message": f"Pod 생성 중 예외 발생: {str(e)}",
            "pod_name": None
        }

