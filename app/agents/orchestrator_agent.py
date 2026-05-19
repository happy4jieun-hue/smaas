"""
app/agents/orchestrator_agent.py — 워크플로우 실행 진입점
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[역할]
  WorkflowService로부터 실행 요청을 받아 AgentContext를 초기화하고
  WorkflowEngine에 실행을 위임한다.

[책임 분리]
  OrchestratorAgent : Context 초기화 + WorkflowEngine 호출
  WorkflowEngine    : 에이전트 순서 제어, 재시도 로직
  각 Agent          : 실제 Claude API 호출 및 결과 저장

[AgentContext 초기화]
  workflowId, taskId, input(업무 내용), 빈 steps/errors를 설정한다.
  이 Context가 모든 에이전트를 거치며 결과로 채워진다.
"""

from datetime import datetime, timezone

from app.agents.workflow_engine import WorkflowEngine
from app.models.task import TaskInput
from app.models.workflow import AgentContext, AgentSteps, WorkflowStatus


class OrchestratorAgent:

    def __init__(self) -> None:
        self._engine = WorkflowEngine()

    async def run(
        self,
        input_data: TaskInput,
        *,
        workflow_id: str,
        task_id: str,
        workflow_repo=None,
    ) -> AgentContext:
        """
        에이전트 파이프라인을 실행하고 최종 AgentContext를 반환한다.

        [처리 흐름]
        1. 빈 AgentContext 구성 (steps는 모두 None)
        2. WorkflowEngine.execute() 에 Context 전달
        3. 엔진이 각 에이전트를 순서대로 실행하며 steps를 채워나감
        4. 완성된 Context(status=completed/failed) 반환
        """
        now = datetime.now(timezone.utc).isoformat()
        context = AgentContext(
            workflowId=workflow_id,
            taskId=task_id,
            input=input_data,
            status=WorkflowStatus.pending,
            steps=AgentSteps(),  # 모든 step이 None — 에이전트 실행 후 채워짐
            errors=[],
            startedAt=now,
            updatedAt=now,
        )
        return await self._engine.execute(
            context,
            workflow_repo=workflow_repo,
            workflow_id=workflow_id,
        )
