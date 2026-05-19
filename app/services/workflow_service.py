"""
app/services/workflow_service.py — Workflow 생명주기 관리
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[역할]
  에이전트 실행 전후의 DB 상태 관리를 담당한다.
  OrchestratorAgent를 호출해 실제 AI 처리를 위임하고,
  결과를 WorkflowRepository를 통해 DB에 저장한다.

[핵심 설계 — pending 선저장]
  에이전트 실행은 시간이 걸린다 (Claude API 호출 × 5회).
  실행 전에 pending 레코드를 먼저 INSERT해두면:
  - 프론트가 Task 생성 직후 workflow를 조회해도 404가 발생하지 않는다
  - 진행 중임을 나타내는 status="pending"을 즉시 보여줄 수 있다

[지연 임포트 — OrchestratorAgent]
  `from app.agents.orchestrator_agent import OrchestratorAgent`를
  함수 내부에서 임포트하는 이유: 순환 의존성 방지.
  (Orchestrator → WorkflowEngine → Agent들 → 다시 Service를 임포트하는 경우)
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from app.models.task import TaskInput
from app.models.workflow import AgentContext, AgentSteps, WorkflowRecord, WorkflowStatus
from app.repositories.workflow_repository import WorkflowRepository


class WorkflowService:

    def __init__(self) -> None:
        self._workflow_repo = WorkflowRepository()

    async def start_workflow(self, task_id: str, input_data: TaskInput) -> None:
        """
        에이전트 파이프라인을 실행하고 결과를 DB에 저장한다.
        TaskService._start_workflow_safe()가 백그라운드에서 이 메서드를 호출한다.

        [처리 순서]
        1. workflow_id 생성, 초기 AgentContext 구성
        2. DB에 pending 레코드 INSERT (프론트 즉시 조회 대응)
        3. OrchestratorAgent.run() 호출 → 5개 에이전트 순차 실행
        4a. 성공: 완성된 context로 DB UPDATE (status=completed)
        4b. 실패: 에러 정보를 담은 context로 DB UPDATE (status=failed)
        """
        # 지연 임포트 — 모듈 로드 시 순환 의존성 회피
        from app.agents.orchestrator_agent import OrchestratorAgent

        workflow_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # 1단계: pending 레코드 선저장 — 에이전트 실행 전에 DB에 존재를 알림
        initial_ctx = AgentContext(
            workflowId=workflow_id,
            taskId=task_id,
            input=input_data,
            status=WorkflowStatus.pending,
            steps=AgentSteps(),   # 아직 아무 에이전트도 실행되지 않은 빈 상태
            errors=[],
            startedAt=now,
            updatedAt=now,
        )
        await self._workflow_repo.create_workflow(
            workflow_id, task_id, WorkflowStatus.pending, initial_ctx
        )

        # 2단계: 에이전트 실행 (Analyzer → Planner → Matcher → Validator → Notifier)
        try:
            orchestrator = OrchestratorAgent()
            context = await orchestrator.run(
                input_data,
                workflow_id=workflow_id,
                task_id=task_id,
                workflow_repo=self._workflow_repo,
            )
            # 3a단계: 성공 — 최종 context(steps 포함)로 DB 업데이트
            await self._workflow_repo.update_workflow(
                workflow_id, context.status, context
            )
        except Exception as e:
            from app.utils.safe_log import safe_str
            print(f"[WorkflowService] error: {safe_str(e)}")
            # 3b단계: 실패 — 에러 정보를 context에 담아 DB 업데이트
            failed_ctx = initial_ctx.model_copy(
                update={
                    "status":    WorkflowStatus.failed,
                    "errors":    [{"agentName": "workflow-service", "message": str(e), "timestamp": now}],
                    "updatedAt": datetime.now(timezone.utc).isoformat(),
                }
            )
            await self._workflow_repo.update_workflow(
                workflow_id, WorkflowStatus.failed, failed_ctx
            )

    async def get_workflow_by_task_id(self, task_id: str) -> Optional[WorkflowRecord]:
        """
        GET /api/workflows/:taskId 요청 시 WorkflowController가 호출한다.
        가장 최근 워크플로우를 반환하며, 없으면 None.
        """
        return await self._workflow_repo.find_by_task_id(task_id)
