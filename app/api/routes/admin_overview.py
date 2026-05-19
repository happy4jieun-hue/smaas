"""
app/api/routes/admin_overview.py — 관리자 전용 조회/완료처리 API
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GET  /api/admin/assignments              전체 배정 목록 (worker_status 필터)
GET  /api/admin/plans                    계획 승인 대기 목록 (assignment 정보 포함)
GET  /api/admin/assignments/{id}/updates 특정 배정의 보고 이력
PATCH /api/admin/assignments/{id}/complete  완료 처리 확정
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.database import AsyncSessionFactory
from app.db.orm_models import MemberORM, SubtaskAssignmentORM, TaskORM, WorkPlanORM, WorkUpdateORM
from app.models.assignment import (
    NotificationCreate,
    NotificationType,
    WorkerStatus,
    WorkerStatusPatch,
)
from app.models.workflow import SubTaskAssignmentRecord
from app.repositories.notification_repository import NotificationRepository
from app.repositories.subtask_assignment_repository import SubtaskAssignmentRepository
from app.repositories.work_plan_repository import WorkPlanRepository

router = APIRouter()
_asgn_repo  = SubtaskAssignmentRepository()
_plan_repo  = WorkPlanRepository()
_notif_repo = NotificationRepository()


# ── 1. 전체 배정 목록 (필터) ─────────────────────────────────

@router.get("/assignments", response_model=List[dict])
async def list_admin_assignments(
    worker_status: Optional[str] = Query(None, description="pending_acceptance|accepted|in_progress|done|completed"),
    status: Optional[str]        = Query(None, description="pending|approved|changed|rejected"),
):
    """
    관리자용 전체 배정 목록.
    member 이름과 task 제목을 포함한 enriched 응답을 반환한다.
    """
    async with AsyncSessionFactory() as session:
        stmt = select(SubtaskAssignmentORM)
        if worker_status:
            stmt = stmt.where(SubtaskAssignmentORM.worker_status == worker_status)
        if status:
            stmt = stmt.where(SubtaskAssignmentORM.status == status)
        stmt = stmt.order_by(SubtaskAssignmentORM.updated_at.desc())
        rows = (await session.execute(stmt)).scalars().all()

        # member 이름 캐시
        member_ids = {r.approved_member_id for r in rows if r.approved_member_id}
        member_ids |= {r.approved_by for r in rows if r.approved_by}
        members: dict[str, str] = {}
        if member_ids:
            m_rows = (
                await session.execute(
                    select(MemberORM).where(MemberORM.id.in_(member_ids))
                )
            ).scalars().all()
            members = {m.id: m.name for m in m_rows}

        # task 제목 캐시
        task_ids = {r.task_id for r in rows}
        tasks: dict[str, str] = {}
        if task_ids:
            t_rows = (
                await session.execute(
                    select(TaskORM).where(TaskORM.id.in_(task_ids))
                )
            ).scalars().all()
            tasks = {t.id: t.title for t in t_rows}

    return [
        {
            "id":                  r.id,
            "taskId":              r.task_id,
            "taskTitle":           tasks.get(r.task_id, ""),
            "workflowId":          r.workflow_id,
            "subTaskIndex":        r.subtask_index,
            "subTaskTitle":        r.subtask_title,
            "subTaskDescription":  r.subtask_description,
            "priority":            r.priority,
            "status":              r.status,
            "workerStatus":        r.worker_status,
            "approvedMemberId":    r.approved_member_id,
            "approvedMemberName":  members.get(r.approved_member_id or "", ""),
            "approvedBy":          r.approved_by,
            "approvedByName":      members.get(r.approved_by or "", ""),
            "approvedAt":          r.approved_at.isoformat() if r.approved_at else None,
            "reason":              r.reason,
            "memo":                r.memo,
            "updatedAt":           r.updated_at.isoformat(),
        }
        for r in rows
    ]


# ── 2. 계획 승인 대기 목록 (enriched) ────────────────────────

@router.get("/plans", response_model=List[dict])
async def list_admin_plans():
    """
    계획 승인 대기 목록 — WorkPlan + Assignment + member 이름 + task 제목 포함.
    """
    async with AsyncSessionFactory() as session:
        plan_rows = (
            await session.execute(
                select(WorkPlanORM)
                .where(WorkPlanORM.status == "submitted")
                .order_by(WorkPlanORM.submitted_at.asc())
            )
        ).scalars().all()

        if not plan_rows:
            return []

        asgn_ids   = {p.assignment_id for p in plan_rows}
        member_ids = {p.member_id for p in plan_rows}

        asgn_rows = (
            await session.execute(
                select(SubtaskAssignmentORM).where(SubtaskAssignmentORM.id.in_(asgn_ids))
            )
        ).scalars().all()
        asgn_map = {a.id: a for a in asgn_rows}

        task_ids = {a.task_id for a in asgn_rows}
        t_rows = (
            await session.execute(select(TaskORM).where(TaskORM.id.in_(task_ids)))
        ).scalars().all()
        task_map = {t.id: t.title for t in t_rows}

        m_rows = (
            await session.execute(select(MemberORM).where(MemberORM.id.in_(member_ids)))
        ).scalars().all()
        member_map = {m.id: m.name for m in m_rows}

    return [
        {
            "planId":         p.id,
            "assignmentId":   p.assignment_id,
            "taskId":         p.task_id,
            "taskTitle":      task_map.get(p.task_id, ""),
            "subTaskTitle":   asgn_map[p.assignment_id].subtask_title if p.assignment_id in asgn_map else "",
            "priority":       asgn_map[p.assignment_id].priority if p.assignment_id in asgn_map else None,
            "memberId":       p.member_id,
            "memberName":     member_map.get(p.member_id, ""),
            "content":        p.content,
            "status":         p.status,
            "feedback":       p.feedback,
            "submittedAt":    p.submitted_at.isoformat(),
            "reviewedAt":     p.reviewed_at.isoformat() if p.reviewed_at else None,
        }
        for p in plan_rows
    ]


# ── 3. 특정 배정의 보고 이력 ─────────────────────────────────

@router.get("/assignments/{assignment_id}/updates", response_model=List[dict])
async def get_assignment_updates(assignment_id: str):
    async with AsyncSessionFactory() as session:
        rows = (
            await session.execute(
                select(WorkUpdateORM)
                .where(WorkUpdateORM.assignment_id == assignment_id)
                .order_by(WorkUpdateORM.created_at.desc())
            )
        ).scalars().all()

        member_ids = {r.member_id for r in rows}
        member_map: dict[str, str] = {}
        if member_ids:
            m_rows = (
                await session.execute(
                    select(MemberORM).where(MemberORM.id.in_(member_ids))
                )
            ).scalars().all()
            member_map = {m.id: m.name for m in m_rows}

    return [
        {
            "id":              r.id,
            "memberId":        r.member_id,
            "memberName":      member_map.get(r.member_id, ""),
            "content":         r.content,
            "progressPercent": r.progress_percent,
            "updateType":      r.update_type,
            "createdAt":       r.created_at.isoformat(),
        }
        for r in rows
    ]


# ── 4. 완료 처리 확정 ─────────────────────────────────────────

@router.patch("/assignments/{assignment_id}/complete")
async def complete_assignment(
    assignment_id: str,
    manager_id: Optional[str] = Query(None, description="완료 처리하는 관리자 member_id"),
):
    """
    관리자가 worker의 완료 보고를 검토하고 공식적으로 완료 처리한다.
    worker_status: done → completed
    worker에게 완료 확정 알림을 발송한다.
    """
    record = await _asgn_repo.find_by_id(assignment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if record.workerStatus != WorkerStatus.done.value:
        raise HTTPException(
            status_code=400,
            detail=f"완료 처리는 worker_status=done 상태에서만 가능합니다. 현재: {record.workerStatus}"
        )

    updated = await _asgn_repo.update_worker_status(
        assignment_id,
        WorkerStatusPatch(workerStatus=WorkerStatus.completed),
    )

    # worker에게 완료 확정 알림
    if record.approvedMemberId:
        await _notif_repo.create(NotificationCreate(
            recipientMemberId=record.approvedMemberId,
            type=NotificationType.completion_reviewed,
            title="업무 완료가 확정되었습니다",
            body=f"'{record.subTaskTitle}' 업무가 관리자에 의해 완료 처리되었습니다. 수고하셨습니다!",
            relatedTaskId=record.taskId,
            relatedAssignmentId=assignment_id,
        ))

    return {"ok": True, "workerStatus": "completed", "assignmentId": assignment_id}
