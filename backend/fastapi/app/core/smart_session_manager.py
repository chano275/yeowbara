import asyncio
import json
import logging
import re
import subprocess
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from core.config import settings

logger = logging.getLogger(__name__)

class SmartChatSessionManager:
    def __init__(self):
        self.sessions: Dict[str, dict] = {}
        
        # 컨텍스트가 필요한 패턴들
        self.context_patterns = [
            r'\b(그것|그거|이것|이거|저것|저거)\b',  # 지시대명사
            r'\b(그때|그런데|그래서|그럼)\b',        # 연결어
            r'\b(방금|아까|전에|위에서)\b',           # 시간 참조
            r'\b(이어서|계속|더|또)\b',              # 계속 지시어
            r'\?$',                                # 질문 (맥락 필요할 가능성)
        ]
        
        # 독립적인 메시지 패턴들
        self.independent_patterns = [
            r'^(안녕|hello|hi|hey)',                # 인사
            r'(뭐|무엇|what|how|why)',              # 새로운 질문
            r'(설명|explain|tell me)',              # 설명 요청
            r'(도움|help|assistant)',               # 도움말
        ]
    
    async def get_or_create_session(self, user_id: str, pod_name: str) -> dict:
        """사용자 세션을 가져오거나 새로 생성합니다."""
        if user_id not in self.sessions:
            self.sessions[user_id] = {
                "history": [],
                "pod_name": pod_name,
                "created_at": datetime.utcnow(),
                "last_activity": datetime.utcnow(),
                "conversation_context": ""  # 대화의 주제나 맥락
            }
            logger.info(f"새 세션 생성: {user_id}")
        
        # 마지막 활동 시간 업데이트
        self.sessions[user_id]["last_activity"] = datetime.utcnow()
        return self.sessions[user_id]
    
    def analyze_message_context(self, message: str, history: List[dict]) -> Tuple[bool, str]:
        """메시지가 컨텍스트를 필요로 하는지 분석하고 적절한 컨텍스트를 반환합니다."""
        message_lower = message.lower()
        
        # 1. 독립적인 메시지인지 확인
        for pattern in self.independent_patterns:
            if re.search(pattern, message_lower):
                return False, ""
        
        # 2. 컨텍스트가 필요한 패턴 확인
        needs_context = False
        for pattern in self.context_patterns:
            if re.search(pattern, message_lower):
                needs_context = True
                break
        
        # 3. 질문의 경우 이전 주제와 관련성 확인
        if '?' in message and history:
            last_messages = [item['bot'] for item in history[-2:]]
            for last_msg in last_messages:
                # 간단한 키워드 매칭으로 관련성 확인
                common_words = set(message_lower.split()) & set(last_msg.lower().split())
                if len(common_words) > 1:
                    needs_context = True
                    break
        
        # 4. 컨텍스트 구성
        if needs_context and history:
            context = self._build_smart_context(history, message)
            return True, context
        
        return False, ""
    
    def _build_smart_context(self, history: List[dict], current_message: str) -> str:
        """현재 메시지와 관련된 스마트한 컨텍스트를 구성합니다."""
        context_parts = []
        
        # 최근 2-3개 대화만 포함
        recent_history = history[-3:]
        
        for item in recent_history:
            # 대화 내용을 요약하여 포함
            user_msg = item['user'][:100] + "..." if len(item['user']) > 100 else item['user']
            bot_msg = item['bot'][:200] + "..." if len(item['bot']) > 200 else item['bot']
            
            context_parts.append(f"사용자: {user_msg}")
            context_parts.append(f"봇: {bot_msg}")
        
        return "\n".join(context_parts)
    
    async def send_message(self, user_id: str, message: str) -> dict:
        """메시지를 전송하고 스마트한 응답을 받습니다."""
        if user_id not in self.sessions:
            raise Exception("세션을 찾을 수 없습니다.")
        
        session = self.sessions[user_id]
        
        # 컨텍스트 필요성 분석
        needs_context, context = self.analyze_message_context(message, session["history"])
        
        # API 요청 구성
        api_data = {
            "text": message,
            "user_id": user_id,  # 사용자 식별
        }
        
        # 컨텍스트가 필요한 경우에만 포함
        if needs_context:
            api_data["context"] = context
            api_data["continue_conversation"] = True
            logger.info(f"컨텍스트 포함 전송 - 사용자: {user_id}")
        else:
            api_data["new_conversation"] = True
            logger.info(f"새 대화로 전송 - 사용자: {user_id}")
        
        # kubectl exec을 통한 API 호출
        pod_name = session["pod_name"]
        escaped_data = json.dumps(api_data).replace('"', '\\"')
        
        # kubectl 명령어 개선 - 외부에서 컨테이너 내 서비스 호출
        cmd = [
            "kubectl", "exec", pod_name, 
            "-n", "agent-env", 
            "-c", "agent", 
            "--", 
            "curl", "-s", "-X", "POST", 
            settings.AGENT_URL,
            "-H", "Content-Type: application/json",
            "-d", escaped_data
        ]
        
        logger.debug(f"실행할 kubectl 명령: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            logger.error(f"kubectl 명령 타임아웃 - 사용자: {user_id}")
            return {
                "response": "요청 처리 시간이 초과되었습니다. 다시 시도해주세요.",
                "error": True
            }
        
        if result.returncode != 0:
            logger.error(f"kubectl 명령 실패 - 반환 코드: {result.returncode}")
            logger.error(f"오류 내용: {result.stderr}")
            logger.error(f"표준 출력: {result.stdout}")
            
            # 연결 오류인 경우 더 자세한 정보 제공
            if "connection refused" in result.stderr.lower():
                return {
                    "response": "Agent 서비스에 연결할 수 없습니다. Pod가 준비되지 않았거나 서비스가 시작되지 않았을 수 있습니다.",
                    "error": True,
                    "debug_info": {
                        "stderr": result.stderr[:200],  # 오류의 처음 200자만
                        "pod_name": pod_name
                    }
                }
            
            return {
                "response": f"명령 실행 실패: {result.stderr[:100]}",
                "error": True
            }
        
        # 응답 처리
        try:
            if result.stdout.strip():
                response_data = json.loads(result.stdout)
                bot_response = response_data.get("response", result.stdout.strip())
            else:
                logger.warning(f"빈 응답 - 사용자: {user_id}")
                return {
                    "response": "서버에서 빈 응답을 받았습니다.",
                    "error": True
                }
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 오류: {e}")
            logger.error(f"원본 응답: {result.stdout}")
            bot_response = result.stdout.strip() if result.stdout.strip() else "응답 파싱 오류"
        
        # 대화 히스토리 업데이트
        session["history"].append({
            "user": message,
            "bot": bot_response,
            "timestamp": datetime.utcnow(),
            "had_context": needs_context
        })
        
        # 히스토리 길이 관리 (최근 20개 유지)
        if len(session["history"]) > 20:
            session["history"] = session["history"][-15:]  # 최근 15개만 유지
        
        return {
            "response": bot_response,
            "had_context": needs_context,
            "error": False
        }
    
    def get_conversation_summary(self, user_id: str) -> dict:
        """대화 요약 정보를 반환합니다."""
        if user_id not in self.sessions:
            return {"active": False}
        
        session = self.sessions[user_id]
        return {
            "active": True,
            "message_count": len(session["history"]),
            "created_at": session["created_at"],
            "last_activity": session["last_activity"],
            "recent_topics": self._extract_topics(session["history"])
        }
    
    def _extract_topics(self, history: List[dict]) -> List[str]:
        """최근 대화에서 주제를 추출합니다."""
        topics = []
        recent_messages = [item['user'] for item in history[-5:]]
        
        # 간단한 키워드 추출
        for msg in recent_messages:
            # 명사 또는 긴 단어 추출 (간단한 방법)
            words = [word for word in msg.split() if len(word) > 3]
            topics.extend(words)
        
        # 빈도수 기반 상위 3개 반환
        from collections import Counter
        topic_counts = Counter(topics)
        return [topic for topic, _ in topic_counts.most_common(3)]
    
    async def reset_session(self, user_id: str):
        """세션을 초기화합니다."""
        if user_id in self.sessions:
            pod_name = self.sessions[user_id]["pod_name"]
            self.sessions[user_id] = {
                "history": [],
                "pod_name": pod_name,
                "created_at": datetime.utcnow(),
                "last_activity": datetime.utcnow(),
                "conversation_context": ""
            }
            logger.info(f"세션 리셋: {user_id}")

# 전역 세션 매니저 인스턴스
smart_session_manager = SmartChatSessionManager()
