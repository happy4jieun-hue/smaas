"""
app/api/routes/workflows.py — /api/workflows 엔드포인트
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[역할]
  task_id로 워크플로우 결과를 조회하는 단일 엔드포인트를 제공한다.
  응답에는 AgentContext 전체(steps, errors 포함)가 담겨 있어
  프론트엔드가 각 에이전트의 결과를 시각화할 수 있다.

[등록 위치]
  main.py: app.include_router(workflows.router, prefix="/api/workflows")
  → 이 파일의 "/{task_id}" → GET /api/workflows/{task_id}

[응답 구조]
  WorkflowRecord
  ├── id, taskId, status, createdAt, updatedAt
  └── context (AgentContext)
        ├── steps
        │   ├── analyzed  : AnalysisResult  (카테고리, 난이도, 스킬)
        │   ├── planned   : PlanResult      (서브태스크 목록)
        │   ├── matched   : MatchResult     (추천 담당자 목록)
        │   ├── validated : ValidationResult
        │   └── notified  : NotificationResult
        └── errors        : 에이전트별 오류 목록

[폴링 패턴]
  Task 생성 후 워크플로우가 완료되기까지 프론트엔드는
  이 엔드포인트를 주기적으로 호출해 status를 확인한다.
  status가 "completed" 또는 "failed"이면 폴링을 중단한다.
"""

import re

from fastapi import APIRouter, HTTPException

from app.models.workflow import WorkflowRecord
from app.services.workflow_service import WorkflowService

router = APIRouter()

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


@router.get("/{task_id}", response_model=WorkflowRecord)
async def get_workflow(task_id: str):
    """
    task_id에 연결된 가장 최근 워크플로우를 반환한다.

    pending 상태면 에이전트가 아직 실행 중임을 의미.
    completed 상태면 context.steps에 모든 에이전트 결과가 채워져 있다.
    """
    if not UUID_RE.match(task_id):
        raise HTTPException(status_code=400, detail=f"Invalid task_id: {task_id!r}")

    svc = WorkflowService()
    record = await svc.get_workflow_by_task_id(task_id)
    if not record:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return record
