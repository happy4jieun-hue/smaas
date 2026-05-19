"""
app/db/orm_models.py — SQLAlchemy ORM 테이블 정의
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
테이블 관계:
  tasks  1:N  workflows, subtask_assignments, work_plans, work_updates
  members  ← 배정 추천 대상, work_plans/updates 작성자, 알림 수신자
  subtask_assignments  1:1  work_plans
  subtask_assignments  1:N  work_updates
  subtask_assignments  →  notifications
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── tasks ─────────────────────────────────────────────────────

class TaskORM(Base):
    __tablename__ = "tasks"

    id:          Mapped[str]        = mapped_column(String(36),  primary_key=True)
    title:       Mapped[str]        = mapped_column(String(255), nullable=False)
    description: Mapped[str]        = mapped_column(Text,        nullable=False)
    deadline:    Mapped[str | None] = mapped_column(String(50),  nullable=True)
    status:       Mapped[str]        = mapped_column(String(20),  nullable=False, default="pending")
    created_at:   Mapped[datetime]   = mapped_column(DateTime,    nullable=False, default=_now)
    updated_at:   Mapped[datetime]   = mapped_column(DateTime,    nullable=False, default=_now, onupdate=_now)


# ── workflows ─────────────────────────────────────────────────

class WorkflowORM(Base):
    __tablename__ = "workflows"

    id:         Mapped[str]    = mapped_column(String(36), primary_key=True)
    task_id:    Mapped[str]    = mapped_column(String(36), ForeignKey("tasks.id"), nullable=False)
    status:     Mapped[str]    = mapped_column(String(20), nullable=False, default="pending")
    context:    Mapped[dict]   = mapped_column(JSON,       nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_now, onupdate=_now)


# ── workflow_steps ────────────────────────────────────────────

class WorkflowStepORM(Base):
    __tablename__ = "workflow_steps"
    __table_args__ = (
        UniqueConstraint("workflow_id", "step_name", name="uq_workflow_step"),
    )

    id:          Mapped[str]         = mapped_column(String(36), primary_key=True)
    workflow_id: Mapped[str]         = mapped_column(String(36), ForeignKey("workflows.id"), nullable=False)
    step_name:   Mapped[str]         = mapped_column(String(20), nullable=False)
    step_status: Mapped[str]         = mapped_column(String(10), nullable=False)
    input:       Mapped[dict]        = mapped_column(JSON,       nullable=False, default=dict)
    output:      Mapped[dict | None] = mapped_column(JSON,       nullable=True)
    error:       Mapped[str | None]  = mapped_column(Text,       nullable=True)
    created_at:  Mapped[datetime]    = mapped_column(DateTime,   nullable=False, default=_now)


# ── assignments (레거시 히스토리용) ───────────────────────────

class AssignmentORM(Base):
    __tablename__ = "assignments"
    __table_args__ = (
        CheckConstraint("score BETWEEN 0 AND 100", name="ck_score_range"),
    )

    id:          Mapped[str]    = mapped_column(String(36),   primary_key=True)
    task_id:     Mapped[str]    = mapped_column(String(36),   ForeignKey("tasks.id"), nullable=False)
    member_id:   Mapped[str]    = mapped_column(String(36),   nullable=False)
    score:       Mapped[int]    = mapped_column(SmallInteger, nullable=False)
    reason:      Mapped[str]    = mapped_column(Text,         nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime,  nullable=False, default=_now)


# ── members ───────────────────────────────────────────────────

class MemberORM(Base):
    __tablename__ = "members"

    id:                       Mapped[str]        = mapped_column(String(36),  primary_key=True)
    name:                     Mapped[str]        = mapped_column(String(100), nullable=False)
    email:                    Mapped[str | None] = mapped_column(String(255), nullable=True)
    team:                     Mapped[str | None] = mapped_column(String(100), nullable=True)
    role:                     Mapped[str | None] = mapped_column(String(100), nullable=True)    # 직책 (예: Backend Engineer)
    grade:                    Mapped[str | None] = mapped_column(String(50),  nullable=True)    # 직급 (예: Senior)
    user_role:                Mapped[str]        = mapped_column(String(20),  nullable=False, default="worker")  # manager | worker
    skills:                   Mapped[list]       = mapped_column(JSON,        nullable=False, default=list)
    preferred_stages:         Mapped[list]       = mapped_column(JSON,        nullable=False, default=list)
    services:                 Mapped[list]       = mapped_column(JSON,        nullable=False, default=list)
    capacity:                 Mapped[int]        = mapped_column(Integer,     nullable=False, default=100)
    current_load:             Mapped[int]        = mapped_column(Integer,     nullable=False, default=0)
    available_hours_today:    Mapped[float]      = mapped_column(Float,       nullable=False, default=8.0)
    available_hours_tomorrow: Mapped[float]      = mapped_column(Float,       nullable=False, default=8.0)
    timezone:                 Mapped[str]        = mapped_column(String(50),  nullable=False, default="Asia/Seoul")
    created_at:               Mapped[datetime]   = mapped_column(DateTime,    nullable=False, default=_now)
    updated_at:               Mapped[datetime]   = mapped_column(DateTime,    nullable=False, default=_now, onupdate=_now)


# ── subtask_assignments ────────────────────────────────────────
# 관리자 승인 흐름: status (AI→관리자), worker_status (worker 수락/보고)

class SubtaskAssignmentORM(Base):
    __tablename__ = "subtask_assignments"
    __table_args__ = (
        UniqueConstraint("workflow_id", "subtask_index", name="uq_subtask_assignment"),
    )

    id:                    Mapped[str]          = mapped_column(String(36),  primary_key=True)
    task_id:               Mapped[str]          = mapped_column(String(36),  ForeignKey("tasks.id"),     nullable=False)
    workflow_id:           Mapped[str]          = mapped_column(String(36),  ForeignKey("workflows.id"), nullable=False)
    subtask_index:         Mapped[int]          = mapped_column(Integer,     nullable=False)
    subtask_title:         Mapped[str]          = mapped_column(Text,        nullable=False)
    subtask_description:   Mapped[str | None]   = mapped_column(Text,        nullable=True)
    priority:              Mapped[str | None]   = mapped_column(String(20),  nullable=True)
    candidates:            Mapped[list]         = mapped_column(JSON,        nullable=False, default=list)
    recommended_member_id: Mapped[str | None]   = mapped_column(String(36),  nullable=True)
    approved_member_id:    Mapped[str | None]   = mapped_column(String(36),  nullable=True)
    approved_by:           Mapped[str | None]   = mapped_column(String(36),  nullable=True)   # 승인한 관리자 member_id
    approved_at:           Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status:                Mapped[str]          = mapped_column(String(20),  nullable=False, default="pending")         # AI→관리자 검토 상태
    worker_status:         Mapped[str]          = mapped_column(String(30),  nullable=False, default="pending_acceptance")  # worker 행동 상태
    suggested_role:        Mapped[str | None]   = mapped_column(String(50),  nullable=True)   # AI 추천 역할 (planner|designer|frontend|backend|qa)
    suggested_reason:      Mapped[str | None]   = mapped_column(Text,        nullable=True)   # 역할 추천 사유
    reason:                Mapped[str | None]   = mapped_column(Text,        nullable=True)
    memo:                  Mapped[str | None]   = mapped_column(Text,        nullable=True)
    # ── 반려/재배정 추적 ──
    rejection_reason:      Mapped[str | None]   = mapped_column(Text,        nullable=True)
    rejected_at:           Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    previous_member_id:    Mapped[str | None]   = mapped_column(String(36),  nullable=True)   # 재배정 직전 담당자
    reassignment_count:    Mapped[int]          = mapped_column(Integer,     nullable=False, default=0)
    created_at:            Mapped[datetime]     = mapped_column(DateTime,    nullable=False, default=_now)
    updated_at:            Mapped[datetime]     = mapped_column(DateTime,    nullable=False, default=_now, onupdate=_now)


# ── work_plans ────────────────────────────────────────────────
# worker가 승인된 subTask에 대해 제출하는 업무 계획

class WorkPlanORM(Base):
    __tablename__ = "work_plans"

    id:             Mapped[str]          = mapped_column(String(36),  primary_key=True)
    assignment_id:  Mapped[str]          = mapped_column(String(36),  ForeignKey("subtask_assignments.id"), nullable=False)
    task_id:        Mapped[str]          = mapped_column(String(36),  ForeignKey("tasks.id"), nullable=False)
    member_id:      Mapped[str]          = mapped_column(String(36),  nullable=False)
    content:        Mapped[str]          = mapped_column(Text,        nullable=False)
    status:         Mapped[str]          = mapped_column(String(20),  nullable=False, default="submitted")  # submitted/approved/rejected
    feedback:       Mapped[str | None]   = mapped_column(Text,        nullable=True)
    submitted_at:   Mapped[datetime]     = mapped_column(DateTime,    nullable=False, default=_now)
    reviewed_at:    Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at:     Mapped[datetime]     = mapped_column(DateTime,    nullable=False, default=_now)
    updated_at:     Mapped[datetime]     = mapped_column(DateTime,    nullable=False, default=_now, onupdate=_now)


# ── work_updates ──────────────────────────────────────────────
# worker의 진행 보고 / 완료 보고

class WorkUpdateORM(Base):
    __tablename__ = "work_updates"

    id:              Mapped[str]      = mapped_column(String(36),  primary_key=True)
    assignment_id:   Mapped[str]      = mapped_column(String(36),  ForeignKey("subtask_assignments.id"), nullable=False)
    task_id:         Mapped[str]      = mapped_column(String(36),  ForeignKey("tasks.id"), nullable=False)
    member_id:       Mapped[str]      = mapped_column(String(36),  nullable=False)
    content:         Mapped[str]      = mapped_column(Text,        nullable=False)
    progress_percent: Mapped[int]     = mapped_column(Integer,     nullable=False, default=0)   # 0~100
    update_type:     Mapped[str]      = mapped_column(String(20),  nullable=False, default="progress")  # progress | completion
    created_at:      Mapped[datetime] = mapped_column(DateTime,    nullable=False, default=_now)


# ── notifications ─────────────────────────────────────────────
# 인앱 알림 — 역할별 이벤트를 DB에 기록하고 프론트가 폴링/조회한다

# ── assignment_history ─────────────────────────────────────────
# 반려 / 재배정 / 수락 등 상태 변경 감사 로그

class AssignmentHistoryORM(Base):
    __tablename__ = "assignment_history"

    id:              Mapped[str]          = mapped_column(String(36),  primary_key=True)
    assignment_id:   Mapped[str]          = mapped_column(String(36),  ForeignKey("subtask_assignments.id"), nullable=False)
    action:          Mapped[str]          = mapped_column(String(30),  nullable=False)   # rejected | reassigned | accepted | completed
    from_member_id:  Mapped[str | None]   = mapped_column(String(36),  nullable=True)    # 이전 담당자
    to_member_id:    Mapped[str | None]   = mapped_column(String(36),  nullable=True)    # 새 담당자
    reason:          Mapped[str | None]   = mapped_column(Text,        nullable=True)    # 사유 (반려 이유 등)
    memo:            Mapped[str | None]   = mapped_column(Text,        nullable=True)    # 관리자 메모
    performed_by:    Mapped[str | None]   = mapped_column(String(36),  nullable=True)    # 행위자 member_id
    created_at:      Mapped[datetime]     = mapped_column(DateTime,    nullable=False, default=_now)


# ── notifications ─────────────────────────────────────────────
# 인앱 알림 — 역할별 이벤트를 DB에 기록하고 프론트가 폴링/조회한다

class NotificationORM(Base):
    __tablename__ = "notifications"

    id:                    Mapped[str]          = mapped_column(String(36),  primary_key=True)
    recipient_member_id:   Mapped[str]          = mapped_column(String(36),  nullable=False)   # 수신자 member_id
    type:                  Mapped[str]          = mapped_column(String(50),  nullable=False)   # task_assigned / plan_review / etc.
    title:                 Mapped[str]          = mapped_column(String(255), nullable=False)
    body:                  Mapped[str]          = mapped_column(Text,        nullable=False)
    is_read:               Mapped[bool]         = mapped_column(Boolean,     nullable=False, default=False)
    related_task_id:       Mapped[str | None]   = mapped_column(String(36),  nullable=True)
    related_assignment_id: Mapped[str | None]   = mapped_column(String(36),  nullable=True)
    created_at:            Mapped[datetime]     = mapped_column(DateTime,    nullable=False, default=_now)
