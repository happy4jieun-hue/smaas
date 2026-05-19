"""
app/agents/workflow_engine.py — 에이전트 실행 순서 및 재시도 제어
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[최적화 — 단계별 즉시 DB 저장]
  각 에이전트 실행 완료 직후 workflow_repo.update_workflow()를 호출해
  프론트가 폴링 시 단계별 진행 상태를 즉시 확인할 수 있다.
  workflow_repo / workflow_id가 None이면 중간 저장을 건너뛴다(하위 호환).
"""

from typing import Optional

from app.agents.analyzer_agent  import AnalyzerAgent
from app.agents.matcher_agent   import MatcherAgent
from app.agents.notifier_agent  import NotifierAgent
from app.agents.planner_agent   import PlannerAgent
from app.agents.validator_agent import ValidatorAgent
from app.models.workflow import AgentContext, WorkflowStatus

MAX_RETRIES = 2
STEP_ORDER  = ["analyzer", "planner", "matcher", "validator"]


class WorkflowEngine:

    def __init__(self) -> None:
        self._agents = {
            "analyzer":  AnalyzerAgent(),
            "planner":   PlannerAgent(),
            "matcher":   MatcherAgent(),
            "validator": ValidatorAgent(),
            "notifier":  NotifierAgent(),
        }

    async def execute(
        self,
        context: AgentContext,
        *,
        workflow_repo=None,
        workflow_id: Optional[str] = None,
    ) -> AgentContext:
        """
        에이전트 파이프라인을 실행한다.
        workflow_repo + workflow_id가 주어지면 각 단계 완료 시 DB를 즉시 갱신한다.
        """
        retry_count = 0

        async def _save(ctx: AgentContext) -> None:
            """단계 완료 직후 DB 갱신 (repo가 없으면 무시)."""
            if workflow_repo and workflow_id:
                await workflow_repo.update_workflow(workflow_id, ctx.status, ctx)

        async def run_from(start_from: str | None = None) -> AgentContext:
            nonlocal retry_count, context

            start_idx = STEP_ORDER.index(start_from) if start_from else 0

            for step in STEP_ORDER[start_idx:]:
                print(f"[WorkflowEngine] running: {step}")
                context = await self._agents[step].execute(context)

                # 단계 완료 → 즉시 DB 저장 (프론트 폴링에 반영)
                await _save(context)

                if not self._agents[step].validate(context):
                    context.status = WorkflowStatus.failed
                    await _save(context)
                    return context

            # Validator 재시도 판단
            validated = context.steps.validated
            if (
                validated
                and not validated.valid
                and validated.retryFromAgent
                and validated.retryFromAgent in STEP_ORDER
                and retry_count < MAX_RETRIES
            ):
                retry_count += 1
                print(f"[WorkflowEngine] retry #{retry_count} from {validated.retryFromAgent}")
                return await run_from(validated.retryFromAgent)

            # Notifier (항상 실행, 실패해도 완료로 처리)
            context = await self._agents["notifier"].execute(context)
            context.status = WorkflowStatus.completed
            return context

        return await run_from()
