from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from routers import nosql_auth, nosql_user, nosql_mcp, nosql_select, nosql_env, conversational_chat_bot,chat_bot
from core.config import settings
from crud.nosql import create_nosql_indexes

import logging

# root 로거 설정
logging.basicConfig(
    level=logging.INFO,  # 이 부분이 중요합니다. INFO 이상 레벨의 메시지를 처리합니다.
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # 콘솔 출력
    ]
)

app = FastAPI(title="MCP API")

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 포함
app.include_router(nosql_user.router)
app.include_router(nosql_mcp.router)
app.include_router(nosql_select.router)
app.include_router(nosql_env.router)
app.include_router(chat_bot.router)
# app.include_router(conversational_chat_bot.router)

# 시작 시 인덱스 생성
@app.on_event("startup")
async def startup_event():
    await create_nosql_indexes()

@app.get("/")
def read_root():
    """API 루트 엔드포인트"""
    return {"message": "MCP API에 오신 것을 환영합니다"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
