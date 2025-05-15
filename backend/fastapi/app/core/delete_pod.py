import subprocess, json, logging
from typing import Dict, Any
from crud.nosql import get_user_by_id, update_pod_name
from core.config import settings

# 로깅 설정
logger = logging.getLogger(__name__)

async def delete_pod(user_id: str) -> Dict[str, Any]:
    """
    사용자 ID를 기반으로 Pod를 삭제하고, DB에서 pod_name을 제거합니다.
    
    Args:
        user_id: 사용자의 ID (UUID 문자열)
        
    Returns:
        Dict[str, Any]: 삭제 결과 정보
    """
    try:
        # 사용자 정보 조회
        user = await get_user_by_id(user_id)
        if not user:
            return {
                "success": False,
                "message": f"사용자 ID({user_id})에 해당하는 사용자를 찾을 수 없습니다."
            }
        
        # 현재 사용자에게 Pod가 있는지 확인
        pod_name = user.get("pod_name")
        if not pod_name:
            logger.info(f"사용자 {user_id}에게 삭제할 Pod가 없습니다.")
            return {
                "success": True,
                "message": "삭제할 Pod가 없습니다."
            }
        
        logger.info(f"Pod 삭제 요청 - 사용자: {user_id}, Pod: {pod_name}")
        
        # kubectl 명령어로 Pod 삭제
        cmd = [
            "kubectl", "delete", "pod", f'agent-{user_id}',
            "-n", "agent-env",
            "--ignore-not-found"
        ]
        
        # 명령어 실행
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # 결과 처리
        if result.returncode != 0:
            logger.error(f"Pod 삭제 중 오류 발생 - 사용자: {user_id}, Pod: {pod_name}, 오류: {result.stderr}")
            return {
                "success": False,
                "message": f"Pod 삭제 중 오류 발생: {result.stderr}"
            }
        
        # Pod 삭제 성공 시 DB에서 pod_name 제거
        # kubectl delete는 성공 시 "pod/[pod_name] deleted" 또는 "No resources found" 메시지를 출력
        logger.info(f"kubectl 출력: {result.stdout.strip()}")
        
        # DB에서 pod_name을 None으로 업데이트
        update_success = await update_pod_name(user_id, None)
        
        if update_success:
            logger.info(f"Pod 삭제 및 DB 업데이트 성공 - 사용자: {user_id}, Pod: {pod_name}")
            return {
                "success": True,
                "message": f"Pod({pod_name})가 성공적으로 삭제되었습니다."
            }
        else:
            logger.warning(f"Pod 삭제는 성공했으나 DB 업데이트 실패 - 사용자: {user_id}, Pod: {pod_name}")
            return {
                "success": True,  # Pod 삭제는 성공
                "message": f"Pod({pod_name})는 삭제되었으나 DB 업데이트에 실패했습니다."
            }
    
    except Exception as e:
        logger.error(f"Pod 삭제 중 예외 발생 - 사용자: {user_id}, 오류: {str(e)}")
        return {
            "success": False,
            "message": f"Pod 삭제 중 예외 발생: {str(e)}"
        }
