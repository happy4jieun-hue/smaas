"""
app/models/assignment.py — worker 업무 흐름 관련 Pydantic 모델
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WorkerStatus   : worker의 subTask 수락/진행 상태
WorkPlan       : worker가 제출하는 업무 계획
WorkUpdate     : worker의 진행/완료 보고
Notification   : 인앱 알림
DashboardStats : 관리자 대시보드 집계
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class WorkerStatus(str, Enum):
    pending_acceptance = "pending_acceptance"  # 관리자 승인 → worker 확인 대기
    accepted           = "accepted"            # worker 수락
    rejected           = "rejected"            # worker 반려
    in_progress        = "in_progress"         # 작업 중
    done               = "done"                # 완료 보고됨 (manager 검토 대기)
    completed          = "completed"           # 관리자 완료 처리 확정


class WorkPlanStatus(str, Enum):
    submitted = "submitted"
    approved  = "approved"
    rejected  = "rejected"


class NotificationType(str, Enum):
    task_assigned       = "task_assigned"       # worker: 업무 배정됨
    plan_review         = "plan_review"         # manager: 계획 검토 필요
    plan_approved       = "plan_approved"       # worker: 계획 승인됨
    plan_rejected       = "plan_rejected"       # worker: 계획 반려됨
    progress_submitted  = "progress_submitted"  # manager: 진행 보고 수신
    assignment_review   = "assignment_review"   # manager: 배정 검토 필요
    worker_rejected     = "worker_rejected"     # manager: worker가 반려
    task_registered     = "task_registered"     # manager: 신규 업무 등록
    completion_reviewed = "completion_reviewed" # worker: 완료 처리 확정됨
    reassigned          = "reassigned"          # worker: 재배정됨


# ── WorkPlan ──────────────────────────────────────────────────

class WorkPlan(BaseModel):
    id:            str
    assignmentId:  str
    taskId:        str
    memberId:      str
    content:       str
    status:        WorkPlanStatus
    feedback:      Optional[str] = None
    submittedAt:   str
    reviewedAt:    Optional[str] = None
    createdAt:     str
    updatedAt:     str


class WorkPlanCreate(BaseModel):
    content: str


class WorkPlanPatch(BaseModel):
    status:   Optional[WorkPlanStatus] = None
    feedback: Optional[str] = None


# ── WorkUpdate ────────────────────────────────────────────────

class WorkUpdate(BaseModel):
    id:              str
    assignmentId:    str
    taskId:          str
    memberId:        str
    content:         str
    progressPercent: int         # 0~100
    updateType:      str         # progress | completion
    createdAt:       str


class WorkUpdateCreate(BaseModel):
    content:         str
    progressPercent: int = 0
    updateType:      str = "progress"   # progress | completion


# ── WorkerStatusPatch ─────────────────────────────────────────

class WorkerStatusPatch(BaseModel):
    workerStatus: WorkerStatus
    memo:         Optional[str] = None


# ── 반려 / 재배정 ──────────────────────────────────────────────

class RejectBody(BaseModel):
    """worker가 업무를 반려할 때 전달하는 body."""
    rejectionReason: str


class ReassignBody(BaseModel):
    """관리자가 재배정할 때 전달하는 body."""
    newMemberId: str
    memo:        Optional[str] = None


# ── AssignmentHistory ──────────────────────────────────────────

class AssignmentHistory(BaseModel):
    id:            str
    assignmentId:  str
    action:        str          # rejected | reassigned | accepted | completed
    fromMemberId:  Optional[str] = None
    toMemberId:    Optional[str] = None
    reason:        Optional[str] = None
    memo:          Optional[str] = None
    performedBy:   Optional[str] = None
    createdAt:     str


# ── Notification ──────────────────────────────────────────────

class Notification(BaseModel):
    id:                  str
    recipientMemberId:   str
    type:                NotificationType
    title:               str
    body:                str
    isRead:              bool
    relatedTaskId:       Optional[str] = None
    relatedAssignmentId: Optional[str] = None
    createdAt:           str


class NotificationCreate(BaseModel):
    recipientMemberId:   str
    type:                NotificationType
    title:               str
    body:                str
    relatedTaskId:       Optional[str] = None
    relatedAssignmentId: Optional[str] = None


# ── DashboardStats ────────────────────────────────────────────

class DashboardStats(BaseModel):
    totalTasks:            int
    pendingAssignments:    int   # 관리자 검토 대기 중 subtask 수
    pendingWorkPlans:      int   # 계획 승인 대기 수
    unreadNotifications:   int
    tasksByStatus:         dict  # {status: count}
    recentTasks:           List[dict]  # 최근 5개 task 요약
