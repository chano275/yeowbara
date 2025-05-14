from fastapi import FastAPI, Request, HTTPException
from app.deploy import deploy_agent
from app.config import NAMESPACE
from kubernetes import config
from kubernetes.client import CoreV1Api

app = FastAPI()

# 쿠버네티스 클러스터 인증 세팅
config.load_incluster_config()

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/deploy")
async def deploy_user_server(request: Request):
    try:
        data = await request.json()

        user_id = data["user_id"]
        env_vars = data.get("env", [])

        # 비동기 함수 호출
        await deploy_agent(user_id, env_vars)
        
        # 생성된 pod 이름 조회
        core_v1 = CoreV1Api()
        pods = core_v1.list_namespaced_pod(
            namespace=NAMESPACE,
            label_selector=f"app=agent-{user_id}"
        )
        pod_name = pods.items[0].metadata.name if pods.items else None
        return {"pod_name": pod_name}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))