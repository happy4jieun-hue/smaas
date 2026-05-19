"""
app/api/routes/my_tasks.py — worker 내 업무 / 전체 업무 현황 API
GET  /api/assignments/overview              전체 또는 담당자 필터 업무 현황 (enriched)
GET  /api/members/{member_id}/assignments   내 업무 목록
GET  /api/assignments/{id}                  assignment 단건 조회
PATCH /api/assignments/{id}/worker-status  수락/반려/진행/완료
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.database import AsyncSessionFactory
from app.db.orm_models import MemberORM, SubtaskAssignmentORM, TaskORM
from app.models.assignment import (
    NotificationCreate,
    NotificationType,
    WorkerStatus,
    WorkerStatusPatch,
)
from app.models.workflow import SubTaskAssignmentRecord
from app.repositories.notification_repository import NotificationRepository
from app.repositories.subtask_assignment_repository import SubtaskAssignmentRepository

router = APIRouter()
_asgn_repo = SubtaskAssignmentRepository()
_notif_repo = NotificationRepository()


@router.get("/assignments/overview", response_model=List[dict])
async def get_assignments_overview(
    assignee_id: Optional[str] = Query(None, description="담당자 member_id. 미입력 시 전체"),
):
    """
    업무 현황 전체 조회 (task명 + 멤버명 포함).
    assignee_id 지정 시 해당 멤버가 담당하는 assignment만 반환.
    manager는 assignee_id 없이 전체 조회, worker는 자신의 id 전달.
    """
    async with AsyncSessionFactory() as session:
        stmt = select(SubtaskAssignmentORM)
        if assignee_id:
            stmt = stmt.where(SubtaskAssignmentORM.approved_member_id == assignee_id)
        stmt = stmt.order_by(SubtaskAssignmentORM.task_id, SubtaskAssignmentORM.subtask_index)
        rows = (await session.execute(stmt)).scalars().all()

        member_ids: set[str] = set()
        task_ids:   set[str] = set()
        for r in rows:
            task_ids.add(r.task_id)
            if r.approved_member_id: member_ids.add(r.approved_member_id)

        member_map: dict[str, str] = {}
        if member_ids:
            m_rows = (await session.execute(
                select(MemberORM).where(MemberORM.id.in_(member_ids))
            )).scalars().all()
            member_map = {m.id: m.name for m in m_rows}

        task_map: dict[str, dict] = {}
        if task_ids:
            t_rows = (await session.execute(
                select(TaskORM).where(TaskORM.id.in_(task_ids))
            )).scalars().all()
            task_map = {t.id: {"title": t.title, "status": t.status, "deadline": t.deadline} for t in t_rows}

    return [
        {
            "id":                r.id,
            "taskId":            r.task_id,
            "taskTitle":         task_map.get(r.task_id, {}).get("title", ""),
            "taskStatus":        task_map.get(r.task_id, {}).get("status", ""),
            "taskDeadline":      task_map.get(r.task_id, {}).get("deadline"),
            "subTaskIndex":      r.subtask_index,
            "subTaskTitle":      r.subtask_title,
            "subTaskDescription": r.subtask_description,
            "priority":          r.priority,
            "status":            r.status,
            "workerStatus":      r.worker_status,
            "approvedMemberId":  r.approved_member_id,
            "approvedMemberName": member_map.get(r.approved_member_id or "", "미배정"),
            "approvedAt":        r.approved_at.isoformat() if r.approved_at else None,
            "memo":              r.memo,
            "updatedAt":         r.updated_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/members/{member_id}/assignments", response_model=list[SubTaskAssignmentRecord])
async def get_my_assignments(member_id: str):
    """worker가 배정받은 subtask 목록 (approved_member_id 기준)."""
    return await _asgn_repo.find_by_member_id(member_id)


@router.get("/assignments/{assignment_id}", response_model=SubTaskAssignmentRecord)
async def get_assignment(assignment_id: str):
    """assignment 단건 조회."""
    record = await _asgn_repo.find_by_id(assignment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return record


@router.patch("/assignments/{assignment_id}/worker-status", response_model=SubTaskAssignmentRecord)
async def update_worker_status(assignment_id: str, patch: WorkerStatusPatch):
    """
    worker 수락/반려/진행/완료 처리.
    반려 시 관리자에게 알림 발송.
    """
    record = await _asgn_repo.find_by_id(assignment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Assignment not found")

    updated = await _asgn_repo.update_worker_status(assignment_id, patch)

    # worker가 반려 → 관리자에게 알림 (approved_by가 있으면 해당 관리자에게)
    if patch.workerStatus == WorkerStatus.rejected and record.approvedBy:
        await _notif_repo.create(NotificationCreate(
            recipientMemberId=record.approvedBy,
            type=NotificationType.worker_rejected,
            title="worker가 업무를 반려했습니다",
            body=f"subTask '{record.subTaskTitle}' 을(를) worker가 반려했습니다. 재배정이 필요합니다.",
            relatedTaskId=record.taskId,
            relatedAssignmentId=assignment_id,
        ))

    return updated
