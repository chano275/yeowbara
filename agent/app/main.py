###########################################################################################
"""
>> AI AGENT 입력 텍스트 예시
curl -X POST http://localhost:8001/agent-query   -H "Content-Type: application/json"   --data @- <<EOF
{"text": "GitHub의 test-repo 저장소의 master 브랜치에 README.md 파일을 만들어줘. 내용은 '테스트 중입니다'로 해줘."}
EOF

curl -X POST http://localhost:8001/agent-query   -H "Content-Type: application/json"   --data @- <<EOF
{"text": "연결되어있는 내 notion 페이지 ( 페이지명 : mcp ) 에 '안녕하세요' 라는 문구 추가해줘. "}
EOF

>> 고려사항
- OUTPUT 으로 Internal Server Error 나왔을 경우 사용자에게 에러 어떤 식으로 전달? 챗봇 형식이라면 BE를 어떤 식으로 구성? 
- fastapi > ai agent 로 로그인할 때에 꺼져있는 컨테이너 키고 기존 유저의 문맥 메모리 / 환경변수 / 사용할 mcp 리스트 줘야 하는데, 어떤 식으로 주고받을지? 
- 모델 선택 가능한것도 만들면 좋을듯? 이건 기획때 BM 따라서 나뉘는데 구독형이면 그냥 박아놔도 괜찮고 / 사용자 API 토큰 쓰게할거면 선택 필수 

>> MCP 서버별 가능 기능
##### github ##### 
- 토큰 발급 : github.com/settings/tokens > Generate New Token > classic > 이름 / 기한 / 권한 설정 > 생성

- [O] repo 생성
- [X] 생성된 repo 에 파일 추가 ( init ) : github REST API 설계상 불가하다고...

##### notion #####
- [*] 토큰 발급 : 본인 노션 우측 상단 ``` > 연결 > 연결 관리 > API 연결 개발 또는 관리 > 새 API 통합 > 이름 / 사용할 워크스페이스 / 프라이빗 > 저장 > API 통합 설정 구성 > 기능 설정
- [*] 페이지 연동 : 연동하고 싶은 페이지 > ``` > 연결 > '연결 검색' 창에 본인이 설정한 API 이름 입력 > 선택 
- [O] 해당 페이지에 내용 입력하기 
- [X] 연동 페이지 이외의 페이지 


##### gitlab #####
- [*] 토큰 발급 : 본인 노션 우측 상단 ``` > 연결 > 연결 관리 > API 연결 개발 또는 관리 > 새 API 통합 > 이름 / 사용할 워크스페이스 / 프라이빗 > 저장 > API 통합 설정 구성 > 기능 설정
- [*] 개인 네임스페이스 ID 를 확인해야 함. curl --header "PRIVATE-TOKEN: @@@" https://lab.ssafy.com/api/v4/namespaces 을 이용해서 ID 알아오고 
- [O] 해당 페이지에 내용 입력하기 
- [X] 연동 페이지 이외의 페이지 
"""
###########################################################################################
import os
from fastapi import FastAPI, HTTPException
from agents import Agent, Runner, set_default_openai_client
from agents.mcp.server import MCPServerStdio
from openai import AsyncOpenAI
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

app = FastAPI()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

# 요청 모델 정의
class AgentRequest(BaseModel):
    text: str
    user_id: Optional[str] = None
    conversation_history: Optional[List[Dict[str, Any]]] = None
    use_conversation_context: Optional[bool] = False

# MCP 서버들 설정
MCP_SERVER_CONFIG = {
    "github": {
        "type": "stdio",
        "params": {"command": "mcp-server-github", "args": [], "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")}}
        # "params": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"], "env": {"GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", "")}}
    },
    "notion": {
        "type": "stdio",
        "params": {"command": "mcp-notion-server", "args": [], "env": {"NOTION_API_TOKEN": os.getenv("NOTION_API_TOKEN", "")}}
    },
    "gitlab": {
        "type": "stdio",
        "params": {"command": "mcp-gitlab", "args": [], "env": {"GITLAB_PERSONAL_ACCESS_TOKEN": os.getenv("GITLAB_PERSONAL_ACCESS_TOKEN", ""), "GITLAB_API_URL": os.getenv("GITLAB_API_URL", ""), "GITLAB_READ_ONLY_MODE": os.getenv("GITLAB_READ_ONLY_MODE", "true")}}
    },
    "duckduckgo-search": {
        "type": "stdio",
        "params": { "command": "duckduckgo-mcp-server", "args": [], "env": {}}
    },
    "korean-spell-checker": {
        "type": "stdio",
        "params": { "command": "mcp-korean-spell", "args": [], "env": {}}
    },
    "sequentialthinking": {
        "type": "stdio",
        "params": {"command": "mcp-server-sequentialthinking", "args": [], "env": {}}
    },
}

# 환경변수 MCP_SERVICES 기반으로 사용할 서비스만 필터링
services_env = os.getenv("MCP_SERVICES", "")
if services_env:
    allowed = [s.strip() for s in services_env.split(",") if s.strip()]
    MCP_SERVER_CONFIG = {k: v for k, v in MCP_SERVER_CONFIG.items() if k in allowed}

agent: Agent | None = None
servers: list[MCPServerStdio] = []

def format_conversation_history(history: List[Dict[str, Any]]) -> str:
    """대화 히스토리를 컨텍스트 문자열로 포맷팅"""
    if not history:
        return ""
    
    formatted_parts = ["이전 대화 내역:"]
    for item in history[-5:]:  # 최근 5개 대화만 사용
        user_msg = item.get('user', '')
        assistant_msg = item.get('assistant', '')
        
        if user_msg and assistant_msg:
            formatted_parts.append(f"사용자: {user_msg}")
            formatted_parts.append(f"어시스턴트: {assistant_msg}")
    
    return "\n".join(formatted_parts)

# 앱 시작 시 필요한 서버만 연결하고 Agent 초기화
@app.on_event("startup")
async def startup_event():
    global agent, servers
    for name, cfg in MCP_SERVER_CONFIG.items():
        srv = MCPServerStdio(params=cfg["params"], cache_tools_list=True, name=name)
        await srv.connect()
        servers.append(srv)
    agent = Agent(
        name="Assistant",
        instructions="Use the tools to achieve the task. Consider the conversation history when provided. Today's date is 2025-05-12",
        model="gpt-4.1-mini",
        # model="gpt-4.1",
        mcp_servers=servers
    )

# 앱 종료 시 모든 서버 정리
@app.on_event("shutdown")
async def shutdown_event():
    for srv in servers:
        await srv.cleanup()

# 메시지 처리 핸들러: 단순히 global agent 사용
# @app.post("/agent-query")
# async def query_agent(payload: dict):
#     if agent is None: raise HTTPException(503, "Agent가 초기화되지 않았습니다.")
#     text = payload.get("text")
#     if not text: raise HTTPException(400, "'text' 필드가 필요합니다.")
#     result = await Runner.run(agent, text)
#     return {"response": result.final_output}

# 메시지 처리 핸들러: Backend에서 conversation_history를 전달받아 처리
@app.post("/agent-query")
async def query_agent(payload: AgentRequest):
    if agent is None: 
        raise HTTPException(503, "Agent가 초기화되지 않았습니다.")
    
    text = payload.text
    
    # 대화 히스토리가 있는 경우 컨텍스트로 추가
    enhanced_text = text
    if payload.conversation_history and payload.use_conversation_context:
        conversation_context = format_conversation_history(payload.conversation_history)
        if conversation_context:
            enhanced_text = f"{conversation_context}\n\n현재 질문: {text}"
    
    try:
        # Agent 실행
        result = await Runner.run(agent, enhanced_text)
        response = result.final_output
        
        return {"response": response}
    
    except Exception as e:
        raise HTTPException(500, f"Agent 처리 중 오류 발생: {str(e)}")

# 기존 호환성을 위한 단순 엔드포인트
@app.post("/agent-query-simple")
async def query_agent_simple(payload: dict):
    """기존 호환성을 위한 단순 텍스트 처리"""
    if agent is None: 
        raise HTTPException(503, "Agent가 초기화되지 않았습니다.")
    
    text = payload.get("text")
    if not text: 
        raise HTTPException(400, "'text' 필드가 필요합니다.")
    
    result = await Runner.run(agent, text)
    return {"response": result.final_output}