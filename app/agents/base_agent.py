"""
app/agents/base_agent.py — 에이전트 추상 기반 클래스
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[역할]
  모든 에이전트(Analyzer, Planner, Matcher, Validator, Notifier)가 상속하는
  공통 인터페이스를 정의한다.

[설계 원칙]
  - execute(): AgentContext를 받아 처리하고 업데이트된 Context를 반환한다.
               에러 발생 시 예외를 던지지 않고 record_error()로 기록 후 반환.
  - validate(): WorkflowEngine이 각 에이전트 실행 직후 호출해
                결과가 올바른지 확인한다. False면 워크플로우를 중단시킨다.
  - record_error(): context.errors 리스트에 에러를 추가한다.
                    여러 에이전트의 에러가 누적되어 최종 응답에 포함된다.

[AgentContext 공유 방식]
  WorkflowEngine이 하나의 context 객체를 순서대로 각 에이전트에 전달한다.
  각 에이전트는 context.steps.analyzed / .planned / .matched / ... 에
  자신의 결과를 저장하고, 다음 에이전트는 이전 결과를 읽어 사용한다.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone

from app.llm.claude_client import ClaudeClient
from app.models.workflow import AgentContext, AgentError


class BaseAgent(ABC):

    def __init__(self, name: str) -> None:
        self.name   = name
        self.claude = ClaudeClient()  # 모든 에이전트가 Claude API 클라이언트를 공유

    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentContext:
        """에이전트 핵심 로직. context를 읽고 처리 결과를 context.steps에 저장한 뒤 반환."""
        ...

    @abstractmethod
    def validate(self, context: AgentContext) -> bool:
        """execute() 이후 결과가 유효한지 검사한다. False면 WorkflowEngine이 워크플로우를 중단."""
        ...

    def record_error(self, context: AgentContext, message: str) -> AgentContext:
        """
        에러를 context.errors에 추가하고 context를 그대로 반환한다.
        WorkflowEngine이 이후 validate()를 호출해 중단 여부를 결정한다.
        예외를 바깥으로 전파하지 않기 때문에 다른 에이전트는 정상 실행을 시도할 수 있다.
        """
        context.errors.append(
            AgentError(
                agentName=self.name,
                message=message,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        return context
