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
                "conversation_context": "",  # 대화의 주제나 맥락
                "current_entities": {  # 현재 논의 중인 엔터티
                    "project": None,  # 현재 논의 중인 프로젝트
                    "file": None,     # 현재 논의 중인 파일
                    "branch": None    # 현재 논의 중인 브랜치
                }
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
        entities = {}  # 중요한 엔티티 추출
        
        # 대화형 처리를 위한 엔티티 수집 (더 많은 히스토리 확인)
        for item in history[-5:]:  # 최근 5개 확인
            user_msg = item['user']
            bot_msg = item['bot']
            
            # 프로젝트명 추출 - 다양한 패턴 고려
            import re
            
            # 1. "yeobara_test프로젝트" 형태에서 추출
            project_pattern = r'([\w\-_]+)(?:프로젝트|저장소)'
            match = re.search(project_pattern, user_msg)
            if match:
                entities['current_project'] = match.group(1)
            
            # 2. "\"프로젝트명\"" 형태에서 추출
            quoted_pattern = r'\"([^\"]+)\".*프로젝트'
            quoted_match = re.search(quoted_pattern, bot_msg)
            if quoted_match:
                entities['current_project'] = quoted_match.group(1)
            
            # 3. GitLab URL이나 프로젝트 정보에서 추출
            if 'lab.ssafy.com' in bot_msg:
                # "dmlcks1998/yeobara_test" 형태의 경로 추출
                path_pattern = r'dmlcks1998/([\w\-_]+)'
                match = re.search(path_pattern, bot_msg)
                if match:
                    entities['current_project'] = match.group(1)
            
            # 4. 프로젝트 정보 라인에서 추출
            if '프로젝트' in bot_msg and '소유자' in bot_msg:
                # 여러 프로젝트가 나열된 경우 가장 최근 언급된 것
                project_lines = bot_msg.split('\n')
                for line in project_lines:
                    if 'yeobara_test' in line:
                        entities['current_project'] = 'yeobara_test'
                        break
        
        # 사용자의 현재 메시지에서 지시대명사 확인
        current_message_lower = current_message.lower()
        pronoun_patterns = ['그 프로젝트', '그거', '그건', '이것', '이거', '그거엔', '그거에', '그것에', '그것엔']
        has_pronoun = any(pattern in current_message_lower for pattern in pronoun_patterns)
        
        # 지시대명사가 사용된 경우 중요 정보 추가
        if has_pronoun and 'current_project' in entities:
            context_parts.append(f"[IMPORTANT] 현재 논의 중인 프로젝트: {entities['current_project']}")
            context_parts.append(f"[NOTICE] 사용자가 '{entities['current_project']}' 프로젝트를 참조하고 있습니다.")
            
            # 요청 타입 파악
            if '파일' in current_message:
                context_parts.append(f"[REQUEST] 사용자가 {entities['current_project']} 프로젝트의 파일 목록을 요청하고 있습니다.")
        
        # 기존 컨텍스트 추가 (중요한 정보 유지)
        recent_history = history[-2:]  # 최근 2개만
        
        for item in recent_history:
            user_msg = item['user']
            bot_msg = item['bot']
            
            # 사용자 메시지
            if len(user_msg) > 50:
                user_msg = user_msg[:50] + "..."
            context_parts.append(f"사용자: {user_msg}")
            
            # 봇 메시지 (중요 정보 우선 유지)
            if len(bot_msg) > 600:  # 제한 더 증가
                # GitLab 프로젝트 정보 우선
                if '프로젝트' in bot_msg:
                    # 프로젝트 관련 중요 정보 추출
                    lines = bot_msg.split('\n')
                    important_lines = []
                    for line in lines:
                        # yeobara_test 관련 정보 우선
                        if any(keyword in line for keyword in ['yeobara_test', 'URL:', '경로:', '소유자:', 'https://', '프로젝트 설명']):
                            important_lines.append(line)
                    if important_lines:
                        bot_msg = '\n'.join(important_lines[:6]) + '...'  # 최대 6줄
                    else:
                        bot_msg = bot_msg[:600] + "..."
                else:
                    bot_msg = bot_msg[:600] + "..."
            context_parts.append(f"봇: {bot_msg}")
        
        # 사용자가 무엇을 요청하는지 추가 힌트 제공
        if '파일' in current_message and '목록' in current_message:
            context_parts.append("[CONTEXT] 사용자가 파일 목록을 요청하고 있습니다.")
        
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
        
        # kubectl 명령어 개선 - JSON 전달 방식 변경
        pod_name = session["pod_name"]
        
        # API 요청을 위한 JSON 구조 생성 (chat_bot.py 방식 활용)
        if needs_context:
            # context가 있는 경우
            json_data = {
                "text": message,
                "user_id": user_id,
                "context": context,
                "continue_conversation": True
            }
        else:
            # 새 대화인 경우
            json_data = {
                "text": message,
                "user_id": user_id,
                "new_conversation": True
            }
        
        # 각 필드를 안전하게 이스케이프
        escaped_text = json.dumps(message)[1:-1]  # 따옴표 제거
        escaped_user_id = json.dumps(user_id)[1:-1]
        
        # JSON 문자열 구성 (chat_bot.py 방식)
        if needs_context:
            escaped_context = json.dumps(context)[1:-1]
            # 시스템 지시문 추가
            system_instruction = "이전 대화의 컨텍스트를 MUST USE해야 합니다. [IMPORTANT], [NOTICE], [REQUEST] 태그에 나온 정보를 반드시 참고하세요. 지시대명사('그 프로젝트', '그거')MUST 참조합니다."
            json_str = f'{{"text": "{escaped_text}", "user_id": "{escaped_user_id}", "context": "{escaped_context}", "system_instruction": "{system_instruction}", "continue_conversation": true}}'
        else:
            json_str = f'{{"text": "{escaped_text}", "user_id": "{escaped_user_id}", "new_conversation": true}}'
        
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
                    "error": True,
                    "details": {
                        "error_type": "empty_response",
                        "pod_name": pod_name
                    }
                }
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 오류: {e}")
            logger.error(f"원본 응답: {result.stdout}")
            
            # JSON 파싱 에러 상세 정보 반환
            return {
                "response": f"에이전트 응답 파싱 오류: 올바르지 않은 JSON 형식입니다.",
                "error": True,
                "details": {
                    "error_type": "json_decode_error",
                    "raw_response": result.stdout[:200] + "..." if len(result.stdout) > 200 else result.stdout,
                    "json_error": str(e),
                    "pod_name": pod_name
                }
            }
        
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
