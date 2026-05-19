"""
app/agents/notifier_agent.py — 알림 발송 에이전트
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[역할]
  워크플로우 마지막 단계. 담당자 배정 완료를 외부 채널(Slack 등)로 알린다.

[Claude API 비호출]
  이 에이전트는 Claude를 사용하지 않는다.
  NotificationService를 통해 설정된 채널로 알림만 발송한다.

[실패 허용 설계]
  validate()가 항상 True를 반환한다.
  Slack 웹훅이 미설정이거나 전송 실패해도 워크플로우가 중단되지 않는다.
  NotificationResult.success로 성공 여부를 기록해 나중에 확인할 수 있다.

[출력 — context.steps.notified (NotificationResult)]
  channels : 성공적으로 알림을 보낸 채널 목록 (["slack"] or [])
  success  : 하나라도 성공했으면 True
"""

from app.agents.base_agent import BaseAgent
from app.models.workflow import AgentContext, NotificationResult
from app.services.notification_service import NotificationService


class NotifierAgent(BaseAgent):

    def __init__(self) -> None:
        super().__init__("notifier")
        self._notification_svc = NotificationService()

    async def execute(self, context: AgentContext) -> AgentContext:
        """
        subTask별 assignments에서 추천 담당자 목록을 추출해 알림 메시지를 구성한다.
        matched 결과가 없으면 배정 없이 완료 알림만 발송한다.
        """
        context.status = "notifying"

        # 새 MatchResult 구조: assignments 리스트에서 추천 담당자 요약 추출
        assignment_summaries: list[str] = []
        if context.steps.matched:
            for a in context.steps.matched.assignments:
                recommended = a.recommendedMemberId or "미정"
                assignment_summaries.append(f"  • [{a.subTaskIndex + 1}] {a.subTaskTitle} → {recommended}")

        try:
            channels = await self._notification_svc.notify(
                task_id=context.taskId,
                assignment_summaries=assignment_summaries,
            )
            context.steps.notified = NotificationResult(
                channels=channels,
                success=len(channels) > 0,
            )
        except Exception as e:
            return self.record_error(context, str(e))

        return context

    def validate(self, context: AgentContext) -> bool:
        """알림 실패가 워크플로우를 중단시키지 않도록 항상 True를 반환한다."""
        return True
