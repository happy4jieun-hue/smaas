"""
app/agents/validator_agent.py — 결과 검증 에이전트
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[최적화 — 조건부 LLM 호출]
  1. 코드 레벨 빠른 검증(_fast_validate)을 먼저 실행한다.
  2. 모든 항목이 통과하면 LLM을 호출하지 않고 valid=True를 바로 반환한다.
  3. 코드 검증에서 문제가 발견된 경우에만 LLM(max_tokens=400)을 호출해
     retryFromAgent를 결정한다.

[개발 축 검증]
  category가 개발·구축 유형이면 백엔드/프론트엔드/테스트 축이 존재하는지 검사한다.
  누락 시 issues에 추가 → LLM이 retryFromAgent="planner" 를 판단하게 유도한다.
  (planner_agent.py의 _補완_dev_axes 가 이미 1차 보정하므로 이 검사는 안전망 역할)
"""

import json

from app.agents.base_agent import BaseAgent
from app.llm.json_parser import JsonParser
from app.llm.prompt_builder import PromptBuilder
from app.llm.prompts.validator import VALIDATOR_SYSTEM_PROMPT, VALIDATOR_USER_PROMPT
from app.models.workflow import AgentContext, ValidationResult, WorkflowStatus

# 개발·구축 카테고리 감지 키워드 (planner_agent.py와 동일 기준)
_DEV_CATEGORY_KEYWORDS = {"개발", "구축", "시스템", "플랫폼", "소프트웨어", "서비스 개발", "웹", "앱", "application"}

# 검증할 필수 축: (축 이름, 감지 키워드)
# 프롬프트 유도 + planner 보정 이후에도 빠진 경우를 최후 안전망으로 잡는다.
_REQUIRED_DEV_AXES = [
    ("백엔드/서버 개발", ["백엔드", "서버", "backend", "api 개발", "비즈니스 로직"]),
    ("프론트엔드/UI 개발", ["프론트", "frontend", "ui", "화면", "페이지"]),
    ("테스트/검증", ["테스트", "test", "검증", "qa"]),
]


def _is_dev_category(category: str) -> bool:
    cat_lower = category.lower()
    return any(kw in cat_lower for kw in _DEV_CATEGORY_KEYWORDS)


def _fast_validate(context: AgentContext) -> tuple[bool, list[str]]:
    """
    LLM 없이 코드로 필수 항목을 빠르게 검증한다.
    반환: (통과 여부, 이슈 목록)
    """
    issues: list[str] = []

    # Analyzer
    a = context.steps.analyzed
    if not a or not a.category or not (1 <= a.complexity <= 5):
        issues.append("분석 결과 불완전 (category 또는 complexity 이상)")

    # Planner
    p = context.steps.planned
    if not p or not p.subTasks:
        issues.append("계획 결과 없음 (subTasks 비어 있음)")
    elif not all(bool(t.title) for t in p.subTasks):
        issues.append("subTask 중 title이 비어 있음")
    else:
        # 개발 카테고리 축 누락 검사 (안전망)
        if a and _is_dev_category(a.category):
            titles_combined = " ".join(t.title.lower() for t in p.subTasks)
            for axis_name, keywords in _REQUIRED_DEV_AXES:
                if not any(kw in titles_combined for kw in keywords):
                    issues.append(f"개발성 업무에서 필수 축 누락: {axis_name}")

    # Matcher — 역할 추천 결과 검증 (실제 멤버 ID 불필요)
    m = context.steps.matched
    if not m or not m.assignments:
        issues.append("매칭 결과 없음")
    elif not any(a.suggestedRole for a in m.assignments):
        issues.append("추천 역할이 없음 (suggestedRole 전부 누락)")

    return len(issues) == 0, issues


class ValidatorAgent(BaseAgent):

    def __init__(self) -> None:
        super().__init__("validator")

    async def execute(self, context: AgentContext) -> AgentContext:
        context.status = WorkflowStatus.validating

        # 1단계: 코드 검증 — LLM 없이 즉시 실행
        passed, issues = _fast_validate(context)

        if passed:
            # 정상 케이스: LLM 호출 없이 통과
            print("[Validator] fast-validate passed - skipping LLM")
            context.steps.validated = ValidationResult(valid=True, issues=[])
            return context

        # 2단계: 이슈 발견 시에만 LLM 호출해 retryFromAgent 결정
        print(f"[Validator] fast-validate failed {issues} - calling LLM")
        user_prompt = PromptBuilder.build(VALIDATOR_USER_PROMPT, {
            "taskInput":      json.dumps(context.input.model_dump(),                                   ensure_ascii=False),
            "analysisResult": json.dumps(context.steps.analyzed.model_dump()  if context.steps.analyzed  else {}, ensure_ascii=False),
            "planResult":     json.dumps(context.steps.planned.model_dump()   if context.steps.planned   else {}, ensure_ascii=False),
            "matchResult":    json.dumps(context.steps.matched.model_dump()   if context.steps.matched   else {}, ensure_ascii=False),
        })

        try:
            resp = await self.claude.complete(
                VALIDATOR_SYSTEM_PROMPT, user_prompt, max_tokens=400
            )
            data = JsonParser.extract(resp.content)
            context.steps.validated = ValidationResult.model_validate(data)
        except Exception as e:
            # LLM 호출 실패해도 코드 검증 결과로 대체 (워크플로우 중단 방지)
            context.steps.validated = ValidationResult(
                valid=False,
                issues=issues,
                retryFromAgent=None,
            )
            return self.record_error(context, str(e))

        return context

    def validate(self, context: AgentContext) -> bool:
        return context.steps.validated is not None
