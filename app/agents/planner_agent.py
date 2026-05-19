"""
app/agents/planner_agent.py — 업무 계획 수립 에이전트
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[역할]
  워크플로우 두 번째 단계. AnalyzerAgent의 결과를 기반으로
  업무를 실행 가능한 서브태스크로 분해하고 순서와 우선순위를 결정한다.

[개발 축 자동 보정]
  category에 개발·구축 키워드가 포함된 경우 _補완_dev_axes()가 실행되어
  누락된 핵심 축(요구사항/DB·API/백엔드/프론트엔드/테스트/배포)을 자동으로 추가한다.
  LLM 프롬프트로 먼저 유도하고, 코드 후처리로 이중 보장한다.

[출력 — context.steps.planned (PlanResult)]
  subTasks            : 서브태스크 목록 (최대 7개)
  estimatedTotalHours : 전체 예상 시간
"""

from app.agents.base_agent import BaseAgent
from app.llm.prompt_builder import PromptBuilder
from app.llm.prompts.planner import PLANNER_SYSTEM_PROMPT, PLANNER_USER_PROMPT
from app.models.workflow import AgentContext, AnalysisResult, PlanResult, SubTask, WorkflowStatus

_VALID_PRIORITIES = {"high", "medium", "low"}
MAX_SUBTASKS = 7  # 개발 축 6개 + 여유 1개

# 개발·구축 카테고리로 판단하는 키워드
_DEV_CATEGORY_KEYWORDS = {"개발", "구축", "시스템", "플랫폼", "소프트웨어", "서비스 개발", "웹", "앱", "application"}

# (축 이름, 감지 키워드 목록, 누락 시 삽입할 기본 SubTask)
_DEV_AXES: list[tuple[str, list[str], SubTask]] = [
    (
        "요구사항/범위 정의",
        ["요구사항", "범위", "기획", "정의", "scope"],
        SubTask(
            title="요구사항 및 범위 정의",
            description="구현 범위와 기능 요구사항을 확정하고 이해관계자와 합의한다.",
            priority="high",
            dependsOn=[],
        ),
    ),
    (
        "DB/API 설계",
        ["db", "api 설계", "데이터 설계", "스키마", "모델링", "erd"],
        SubTask(
            title="DB 및 API 설계",
            description="데이터 모델, 테이블 스키마, API 인터페이스를 설계한다.",
            priority="high",
            dependsOn=["요구사항 및 범위 정의"],
        ),
    ),
    (
        "백엔드 개발",
        ["백엔드", "서버", "backend", "api 개발", "비즈니스 로직", "서비스 로직"],
        SubTask(
            title="백엔드 개발",
            description="서버 사이드 비즈니스 로직과 API 엔드포인트를 구현한다.",
            priority="high",
            dependsOn=["DB 및 API 설계"],
        ),
    ),
    (
        "프론트엔드 개발",
        ["프론트", "frontend", "ui", "화면", "페이지", "컴포넌트"],
        SubTask(
            title="프론트엔드 개발",
            description="사용자 인터페이스 화면과 API 연동 흐름을 구현한다.",
            priority="high",
            dependsOn=["백엔드 개발"],
        ),
    ),
    (
        "테스트/검증",
        ["테스트", "test", "검증", "qa", "검수", "단위 테스트", "통합 테스트"],
        SubTask(
            title="테스트 및 검증",
            description="단위·통합 테스트를 실행하고 주요 기능을 검수한다.",
            priority="medium",
            dependsOn=["백엔드 개발", "프론트엔드 개발"],
        ),
    ),
    (
        "배포/운영 준비",
        ["배포", "deploy", "운영", "릴리즈", "release", "ci", "cd"],
        SubTask(
            title="배포 및 운영 준비",
            description="배포 환경을 구성하고 운영 모니터링 및 롤백 계획을 수립한다.",
            priority="medium",
            dependsOn=["테스트 및 검증"],
        ),
    ),
]


def _is_dev_category(category: str) -> bool:
    """category 문자열에 개발·구축 관련 키워드가 포함되어 있으면 True."""
    cat_lower = category.lower()
    return any(kw in cat_lower for kw in _DEV_CATEGORY_KEYWORDS)


def _补완_dev_axes(plan: PlanResult, analyzed: AnalysisResult) -> PlanResult:
    """
    개발 카테고리 업무에서 누락된 핵심 구현 축을 자동으로 추가한다.
    LLM이 이미 해당 축을 포함했으면 건너뛴다(title 키워드 기반 감지).
    """
    if not _is_dev_category(analyzed.category):
        return plan

    # 기존 subTask title 전체를 소문자 합산해 키워드 포함 여부 검사
    existing_titles = " ".join(t.title.lower() for t in plan.subTasks)

    for axis_name, keywords, fallback in _DEV_AXES:
        if not any(kw in existing_titles for kw in keywords):
            print(f"[Planner] dev axis missing -> inserting: {axis_name}")
            plan.subTasks.append(fallback)
            # 추가된 title이 이후 축 감지에도 반영되도록 갱신
            existing_titles += " " + fallback.title.lower()

    return plan


class PlannerAgent(BaseAgent):

    def __init__(self) -> None:
        super().__init__("planner")

    async def execute(self, context: AgentContext) -> AgentContext:
        context.status = WorkflowStatus.planning
        analyzed = context.steps.analyzed

        user_prompt = PromptBuilder.build(PLANNER_USER_PROMPT, {
            "summary":        analyzed.summary,
            "category":       analyzed.category,
            "complexity":     str(analyzed.complexity),
            "estimatedHours": str(analyzed.estimatedHours),
            "requiredSkills": ", ".join(analyzed.requiredSkills),
        })

        try:
            data = await self.claude.complete_json(
                PLANNER_SYSTEM_PROMPT,
                user_prompt,
                max_parse_retries=1,
                max_tokens=1500,  # 최대 7개 subTask를 수용하기 위해 1200→1500
            )

            plan = PlanResult.model_validate(data)

            # subTasks가 비어 있으면 단일 태스크로 보정
            if not plan.subTasks:
                plan.subTasks = [
                    SubTask(
                        title=analyzed.summary[:80],
                        description=analyzed.summary,
                        priority="medium",
                        dependsOn=[],
                    )
                ]

            # priority 값 보정 (상한 자르기 전에 실행)
            for task in plan.subTasks:
                if task.priority not in _VALID_PRIORITIES:
                    task.priority = "medium"

            # 개발 축 누락 자동 보정 (LLM 결과 후처리)
            plan = _补완_dev_axes(plan, analyzed)

            # 상한 초과분 잘라내기
            plan.subTasks = plan.subTasks[:MAX_SUBTASKS]

            context.steps.planned = plan

        except Exception as e:
            return self.record_error(context, str(e))

        return context

    def validate(self, context: AgentContext) -> bool:
        r = context.steps.planned
        if r is None or not r.subTasks:
            return False
        return all(bool(t.title) for t in r.subTasks)
