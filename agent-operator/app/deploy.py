import asyncio
from kubernetes import client
from app.config import NAMESPACE, AGENT_IMAGE

async def deploy_agent(user_id: str, env_vars: list) -> str:
    name = f"agent-{user_id}"

    # 쿠버네티스 API 호출은 비동기가 아니므로 스레드풀에서 실행
    apps_v1 = client.AppsV1Api()
    core_v1 = client.CoreV1Api()

    # 디플로이먼트 생성 로직을 비동기로 실행
    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name=name, labels={"app": name}),
        spec=client.V1DeploymentSpec(
            replicas=1,
            strategy=client.V1DeploymentStrategy(
                type="RollingUpdate",
                rolling_update=client.V1RollingUpdateDeployment(
                    max_surge=1,
                    max_unavailable=0
                )
            ),
            selector={"matchLabels": {"app": name}},
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": name}),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name="agent",
                            image=AGENT_IMAGE,
                            ports=[client.V1ContainerPort(container_port=8002)],
                            env=[client.V1EnvVar(name=e["name"], value=e["value"]) for e in env_vars],
                        )
                    ]
                )
            )
        )
    )
    
    # 쿠버네티스 API 호출을 비동기로 처리
    try:
        await asyncio.to_thread(
            apps_v1.replace_namespaced_deployment, 
            name=name, 
            namespace=NAMESPACE, 
            body=deployment
        )
        first_create = False
    except client.exceptions.ApiException as e:
        if e.status == 404:
            await asyncio.to_thread(
                apps_v1.create_namespaced_deployment, 
                namespace=NAMESPACE, 
                body=deployment
            )
            first_create = True
        else:
            raise

    # 첫 생성 시에만 Service 생성
    if first_create:
        service = client.V1Service(
            metadata=client.V1ObjectMeta(name=name),
            spec=client.V1ServiceSpec(
                selector={"app": name},
                ports=[client.V1ServicePort(port=80, target_port=8002)],
                type="ClusterIP"
            )
        )
        try:
            await asyncio.to_thread(
                core_v1.create_namespaced_service, 
                namespace=NAMESPACE, 
                body=service
            )
        except client.exceptions.ApiException as e:
            if e.status != 409:  # 409(이미 존재) 에러는 무시하고 진행
                raise
        
    # # Pod 생성 확인을 위한 대기
    await asyncio.sleep(4)  # 적절한 대기 시간 설정    
    # # Pod 이름 조회
    # pods = await asyncio.to_thread(
    #     core_v1.list_namespaced_pod,
    #     namespace=NAMESPACE,
    #     label_selector=f"app={name}"
    # )
    # pod_name = pods.items[0].metadata.name if pods.items else None
    
    # 서비스 URL + Pod 이름 반환
    # return {"service_url": f"http://{name}.{NAMESPACE}.svc.cluster.local", "pod_name": pod_name}