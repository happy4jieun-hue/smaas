from __future__ import annotations

from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from app.models.task import TaskInput


class WorkflowStatus(str, Enum):
    pending    = "pending"
    analyzing  = "analyzing"
    planning   = "planning"
    matching   = "matching"
    validating = "validating"
    saving     = "saving"
    notifying  = "notifying"
    completed  = "completed"
    failed     = "failed"


class AssignmentStatus(str, Enum):
    pending  = "pending"
    approved = "approved"
    changed  = "changed"
    rejected = "rejected"


# ── Agent 결과 타입 ────────────────────────────────────────────

class AnalysisResult(BaseModel):
    category:       str
    complexity:     int               # 1~5
    requiredSkills: List[str]
    estimatedHours: float
    keywords:       List[str]
    summary:        str


class SubTask(BaseModel):
    title:       str
    description: str
    priority:    str                  # high | medium | low
    dependsOn:   List[str] = []


class PlanResult(BaseModel):
    subTasks:            List[SubTask]
    estimatedTotalHours: float


class AssigneeCandidate(BaseModel):
    memberId: str
    score:    int                     # 0~100
    reason:   str


class RoleRecommendationResult(BaseModel):
    """MatcherAgent이 subTask 하나에 대해 생성하는 역할 추천 결과.
    AI는 실제 사람을 고르지 않고 필요한 역할(role)만 추천한다.
    실제 인원 배정은 관리자가 AssignmentReviewPage에서 수행한다.
    """
    subTaskIndex:   int
    subTaskTitle:   str
    suggestedRole:  str   # planner | designer | frontend | backend | qa
    suggestedReason: str


class RolesSummary(BaseModel):
    """전체 업무 기준 역할별 필요 인원 집계."""
    planner:  int = 0
    designer: int = 0
    frontend: int = 0
    backend:  int = 0
    qa:       int = 0


# backward-compat alias (validator_agent 등에서 참조 시 오류 방지)
SubTaskAssignmentResult = RoleRecommendationResult


class MatchResult(BaseModel):
    """역할 추천 결과 목록."""
    assignments:  List[RoleRecommendationResult] = []
    rolesSummary: Optional[RolesSummary] = None


class ValidationResult(BaseModel):
    valid:           bool
    issues:          List[str] = []
    retryFromAgent:  Optional[str] = None


class NotificationResult(BaseModel):
    channels: List[str]
    success:  bool


class AgentError(BaseModel):
    agentName: str
    message:   str
    timestamp: str


class AgentSteps(BaseModel):
    analyzed:  Optional[AnalysisResult]   = None
    planned:   Optional[PlanResult]       = None
    matched:   Optional[MatchResult]      = None
    validated: Optional[ValidationResult] = None
    notified:  Optional[NotificationResult] = None


class AgentContext(BaseModel):
    workflowId: str
    taskId:     str
    input:      TaskInput
    status:     WorkflowStatus
    steps:      AgentSteps = Field(default_factory=AgentSteps)
    errors:     List[AgentError] = []
    startedAt:  str
    updatedAt:  str


class WorkflowRecord(BaseModel):
    id:        str
    taskId:    str
    status:    WorkflowStatus
    context:   AgentContext
    createdAt: str
    updatedAt: str


# ── SubTask Assignment DB 레코드 ───────────────────────────────

class SubTaskAssignmentRecord(BaseModel):
    """subtask_assignments 테이블 행 — API 응답에 사용."""
    id:                  str
    taskId:              str
    workflowId:          str
    subTaskIndex:        int
    subTaskTitle:        str
    subTaskDescription:  Optional[str] = None
    priority:            Optional[str] = None
    suggestedRole:       Optional[str] = None   # AI 추천 역할 (planner|designer|frontend|backend|qa)
    suggestedReason:     Optional[str] = None   # 역할 추천 사유
    candidates:          List[AssigneeCandidate] = []
    recommendedMemberId: Optional[str] = None   # legacy (미사용)
    approvedMemberId:    Optional[str] = None
    approvedBy:          Optional[str] = None   # 승인한 관리자 member_id
    approvedAt:          Optional[str] = None   # 승인 일시
    status:              AssignmentStatus
    workerStatus:        str = "pending_acceptance"  # worker 수락/진행 상태
    reason:              Optional[str] = None
    memo:                Optional[str] = None
    # 반려/재배정 추적
    rejectionReason:     Optional[str] = None
    rejectedAt:          Optional[str] = None
    previousMemberId:    Optional[str] = None
    reassignmentCount:   int = 0
    createdAt:           str
    updatedAt:           str


class AssignmentPatch(BaseModel):
    """PATCH /api/assignments/{id} 요청 body."""
    approvedMemberId: Optional[str] = None
    status:           Optional[AssignmentStatus] = None
    memo:             Optional[str] = None
