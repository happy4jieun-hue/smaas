"""
app/agents/matcher_agent.py - subTask 역할 추천 에이전트

[설계 원칙]
  AI는 실제 사람을 직접 선택하지 않고, subTask별로 필요한 역할(role)을 추천한다.
  실제 인원 배정은 관리자가 AssignmentReviewPage에서 수행한다.

[추천 전략 - 2단계]
  1. LLM 호출: 역할 추천 (planner/designer/frontend/backend/qa)
  2. LLM 누락/실패: 키워드 기반 코드 레벨 역할 감지로 fallback

[hard fail 없음]
  members가 없어도 역할 추천은 항상 가능하므로 workflow를 중단하지 않는다.
"""

import json
from collections import Counter

from app.agents.base_agent import BaseAgent
from app.llm.json_parser import JsonParser
from app.llm.prompt_builder import PromptBuilder
from app.llm.prompts.matcher import MATCHER_SYSTEM_PROMPT, MATCHER_USER_PROMPT
from app.models.workflow import (
    AgentContext,
    MatchResult,
    RoleRecommendationResult,
    RolesSummary,
    WorkflowStatus,
)
from app.repositories.subtask_assignment_repository import SubtaskAssignmentRepository

# ── 역할 키워드 매핑 ────────────────────────────────────────────────────────
_ROLE_KEYWORDS: dict[str, list[str]] = {
    "planner": [
        "기획", "정책", "요구사항", "기능 정의", "화면 리스트", "ia",
        "검토", "정리", "분석", "정의", "스펙", "planning", "scope", "범위", "정의서",
    ],
    "designer": [
        "ui", "ux", "화면", "디자인", "와이어프레임", "figma", "피그마",
        "인터랙션", "플로우", "시각", "그래픽", "mockup", "목업", "prototype",
    ],
    "frontend": [
        "프론트", "frontend", "react", "vue", "javascript", "typescript",
        "html", "css", "웹", "페이지", "컴포넌트", "ui 개발", "화면 개발", "상태관리",
    ],
    "backend": [
        "백엔드", "서버", "api", "db", "데이터베이스", "backend",
        "비즈니스 로직", "배포", "인프라", "devops", "api 설계", "인증", "비즈니스",
    ],
    "qa": [
        "테스트", "qa", "검증", "검수", "test", "품질", "unit test", "통합 테스트",
        "시나리오", "회귀",
    ],
}

_VALID_ROLES = set(_ROLE_KEYWORDS.keys())

# 역할 판단 우선순위 (앞쪽이 더 구체적 → 먼저 검사)
_ROLE_PRIORITY = ["qa", "designer", "planner", "frontend", "backend"]


def _detect_role(text: str) -> str:
    """서브태스크 제목/설명에서 역할을 감지한다. 기본값: backend"""
    t = text.lower()
    for role in _ROLE_PRIORITY:
        if any(kw in t for kw in _ROLE_KEYWORDS[role]):
            return role
    return "backend"


def _code_recommend(
    subtask_index: int,
    subtask_title: str,
    subtask_description: str = "",
) -> RoleRecommendationResult:
    """키워드 기반 코드 레벨 역할 추천 (LLM fallback)."""
    role = _detect_role(subtask_title + " " + subtask_description)
    return RoleRecommendationResult(
        subTaskIndex=subtask_index,
        subTaskTitle=subtask_title,
        suggestedRole=role,
        suggestedReason=f"키워드 기반 역할 감지: {role}",
    )


class MatcherAgent(BaseAgent):

    def __init__(self) -> None:
        super().__init__("matcher")
        self._assignment_repo = SubtaskAssignmentRepository()

    async def execute(self, context: AgentContext) -> AgentContext:
        context.status = WorkflowStatus.matching
        analyzed = context.steps.analyzed
        planned  = context.steps.planned

        if not planned or not planned.subTasks:
            return self.record_error(context, "Planner result missing.")

        subtasks_json = json.dumps(
            [
                {
                    "index":       i,
                    "title":       st.title,
                    "description": st.description or "",
                    "priority":    st.priority,
                }
                for i, st in enumerate(planned.subTasks)
            ],
            ensure_ascii=False,
        )

        user_prompt = PromptBuilder.build(MATCHER_USER_PROMPT, {
            "category":       analyzed.category       if analyzed else "",
            "complexity":     str(analyzed.complexity) if analyzed else "3",
            "estimatedHours": str(analyzed.estimatedHours) if analyzed else "0",
            "subTasksJson":   subtasks_json,
        })

        assignments: list[RoleRecommendationResult] = []
        roles_summary = RolesSummary()

        # ── LLM 호출 ──────────────────────────────────────────────────────────
        try:
            resp = await self.claude.complete(
                MATCHER_SYSTEM_PROMPT, user_prompt, max_tokens=2000,
            )
            data        = JsonParser.extract(resp.content)
            raw_assigns = data.get("assignments", [])

            for raw in raw_assigns:
                idx = raw.get("subTaskIndex", 0)
                if idx >= len(planned.subTasks):
                    continue

                role = (raw.get("suggestedRole") or "").lower().strip()
                if role not in _VALID_ROLES:
                    role = _detect_role(planned.subTasks[idx].title)

                assignments.append(RoleRecommendationResult(
                    subTaskIndex=idx,
                    subTaskTitle=raw.get("subTaskTitle") or planned.subTasks[idx].title,
                    suggestedRole=role,
                    suggestedReason=raw.get("suggestedReason") or f"{role} 역할 필요",
                ))

            # rolesSummary 파싱
            rs = data.get("rolesSummary", {})
            roles_summary = RolesSummary(
                planner=int(rs.get("planner", 0)),
                designer=int(rs.get("designer", 0)),
                frontend=int(rs.get("frontend", 0)),
                backend=int(rs.get("backend", 0)),
                qa=int(rs.get("qa", 0)),
            )

        except Exception as e:
            from app.utils.safe_log import safe_str
            print(f"[Matcher] LLM failed: {safe_str(e)} -> code fallback")

        # ── LLM 누락 subTask 코드 fallback으로 보완 ────────────────────────────
        covered = {a.subTaskIndex for a in assignments}
        for i, st in enumerate(planned.subTasks):
            if i not in covered:
                assignments.append(_code_recommend(i, st.title, st.description or ""))

        assignments.sort(key=lambda a: a.subTaskIndex)

        # rolesSummary가 전부 0이면 실제 집계로 채움
        if not any([roles_summary.planner, roles_summary.designer,
                    roles_summary.frontend, roles_summary.backend, roles_summary.qa]):
            cnt = Counter(a.suggestedRole for a in assignments)
            roles_summary = RolesSummary(
                planner=cnt.get("planner", 0),
                designer=cnt.get("designer", 0),
                frontend=cnt.get("frontend", 0),
                backend=cnt.get("backend", 0),
                qa=cnt.get("qa", 0),
            )

        context.steps.matched = MatchResult(
            assignments=assignments,
            rolesSummary=roles_summary,
        )

        await self._save(context, planned, assignments)
        return context

    async def _save(self, context: AgentContext, planned, assignments: list) -> None:
        try:
            await self._assignment_repo.save_assignments(
                task_id=context.taskId,
                workflow_id=context.workflowId,
                assignments=assignments,
                subtasks_meta=planned.subTasks,
            )
        except Exception as e:
            from app.utils.safe_log import safe_str
            print(f"[Matcher] DB save error: {safe_str(e)}")

    def validate(self, context: AgentContext) -> bool:
        r = context.steps.matched
        if not r or not r.assignments:
            return False
        return any(a.suggestedRole for a in r.assignments)
