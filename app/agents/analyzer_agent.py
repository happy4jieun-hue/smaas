"""
app/agents/analyzer_agent.py — 업무 분석 에이전트
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[역할]
  워크플로우의 첫 번째 단계. 사용자가 입력한 업무(title, description)를
  Claude에게 전달해 구조화된 분석 결과를 얻는다.

[출력 — context.steps.analyzed (AnalysisResult)]
  category       : 업무 분류 (개발/디자인/마케팅 등)
  complexity     : 난이도 1~5
  requiredSkills : 필요 스킬 목록 → MatcherAgent가 사용
  estimatedHours : 예상 소요 시간 → PlannerAgent가 사용
  keywords       : 핵심 키워드
  summary        : 1~2문장 요약 → PlannerAgent 프롬프트에 포함

[다음 에이전트]
  PlannerAgent가 analyzed.summary, analyzed.complexity 등을 읽어 계획을 수립한다.
"""

from app.agents.base_agent import BaseAgent
from app.llm.json_parser import JsonParser
from app.llm.prompt_builder import PromptBuilder
from app.llm.prompts.analyzer import ANALYZER_SYSTEM_PROMPT, ANALYZER_USER_PROMPT
from app.models.workflow import AgentContext, AnalysisResult, WorkflowStatus


class AnalyzerAgent(BaseAgent):

    def __init__(self) -> None:
        super().__init__("analyzer")

    async def execute(self, context: AgentContext) -> AgentContext:
        """
        [처리 흐름]
        1. context.input(title, description, deadline)으로 프롬프트 구성
        2. Claude API 호출 → 자연어 텍스트 응답 수신
        3. JsonParser.extract()로 JSON 파싱 (코드 블럭 제거, 균형 추출 등)
        4. AnalysisResult Pydantic 모델로 검증 후 context.steps.analyzed에 저장
        """
        context.status = WorkflowStatus.analyzing

        user_prompt = PromptBuilder.build(ANALYZER_USER_PROMPT, {
            "title":       context.input.title,
            "description": context.input.description,
            "deadline":    context.input.deadline or "없음",
        })

        try:
            resp = await self.claude.complete(ANALYZER_SYSTEM_PROMPT, user_prompt, max_tokens=800)
            data = JsonParser.extract(resp.content)  # LLM 출력에서 JSON 안전하게 추출
            context.steps.analyzed = AnalysisResult.model_validate(data)
        except Exception as e:
            return self.record_error(context, str(e))

        return context

    def validate(self, context: AgentContext) -> bool:
        """category가 있고 complexity가 유효 범위(1~5)인지 검사."""
        r = context.steps.analyzed
        return r is not None and bool(r.category) and 1 <= r.complexity <= 5
