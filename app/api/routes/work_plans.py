"""
app/api/routes/work_plans.py — 업무 계획 제출/조회/승인 API
POST  /api/assignments/{id}/work-plan   계획 제출 (worker)
GET   /api/assignments/{id}/work-plan   계획 조회
PATCH /api/work-plans/{id}              계획 승인/반려 (manager)
GET   /api/work-plans/pending           대기 목록 (manager)
POST  /api/assignments/{id}/updates     진행/완료 보고 (worker)
GET   /api/assignments/{id}/updates     보고 목록
"""

from datetime import datetime, timezone
from typing import List
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.database import AsyncSessionFactory
from app.db.orm_models import WorkUpdateORM
from app.models.assignment import (
    NotificationCreate,
    NotificationType,
    WorkPlan,
    WorkPlanCreate,
    WorkPlanPatch,
    WorkPlanStatus,
    WorkUpdate,
    WorkUpdateCreate,
    WorkerStatus,
)
from app.repositories.notification_repository import NotificationRepository
from app.repositories.subtask_assignment_repository import SubtaskAssignmentRepository
from app.repositories.work_plan_repository import WorkPlanRepository

router = APIRouter()
_plan_repo = WorkPlanRepository()
_asgn_repo = SubtaskAssignmentRepository()
_notif_repo = NotificationRepository()


# ── 업무 계획 ─────────────────────────────────────────────────

@router.post("/assignments/{assignment_id}/work-plan", response_model=WorkPlan, status_code=201)
async def submit_work_plan(assignment_id: str, body: WorkPlanCreate, member_id: str):
    """worker가 업무 계획을 제출한다. ?member_id= 쿼리로 제출자를 지정."""
    record = await _asgn_repo.find_by_id(assignment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Assignment not found")

    plan = await _plan_repo.create(assignment_id, record.taskId, member_id, body)

    # 관리자에게 계획 검토 알림 (approved_by가 있으면 해당 관리자에게)
    if record.approvedBy:
        await _notif_repo.create(NotificationCreate(
            recipientMemberId=record.approvedBy,
            type=NotificationType.plan_review,
            title="업무 계획 검토 요청",
            body=f"'{record.subTaskTitle}' 업무 계획이 제출되었습니다. 검토해주세요.",
            relatedTaskId=record.taskId,
            relatedAssignmentId=assignment_id,
        ))

    # worker_status를 in_progress로 전환
    from app.models.assignment import WorkerStatusPatch
    await _asgn_repo.update_worker_status(
        assignment_id, WorkerStatusPatch(workerStatus=WorkerStatus.in_progress)
    )

    return plan


@router.get("/assignments/{assignment_id}/work-plan", response_model=WorkPlan | None)
async def get_work_plan(assignment_id: str):
    return await _plan_repo.find_by_assignment_id(assignment_id)


@router.get("/work-plans/pending", response_model=List[WorkPlan])
async def get_pending_plans():
    """관리자용 — 계획 승인 대기 목록."""
    return await _plan_repo.find_pending()


@router.patch("/work-plans/{plan_id}", response_model=WorkPlan)
async def patch_work_plan(plan_id: str, body: WorkPlanPatch):
    """관리자가 업무 계획을 승인하거나 반려한다."""
    plan = await _plan_repo.patch(plan_id, body)
    if not plan:
        raise HTTPException(status_code=404, detail="WorkPlan not found")

    # worker에게 결과 알림
    notif_type = (
        NotificationType.plan_approved
        if body.status == WorkPlanStatus.approved
        else NotificationType.plan_rejected
    )
    title = "업무 계획이 승인되었습니다" if body.status == WorkPlanStatus.approved else "업무 계획이 반려되었습니다"
    await _notif_repo.create(NotificationCreate(
        recipientMemberId=plan.memberId,
        type=notif_type,
        title=title,
        body=f"'{plan.assignmentId}' 계획이 {'승인' if body.status == WorkPlanStatus.approved else '반려'}되었습니다."
              + (f" 피드백: {body.feedback}" if body.feedback else ""),
        relatedTaskId=plan.taskId,
        relatedAssignmentId=plan.assignmentId,
    ))

    return plan


# ── 진행/완료 보고 ─────────────────────────────────────────────

@router.post("/assignments/{assignment_id}/updates", response_model=WorkUpdate, status_code=201)
async def submit_update(assignment_id: str, body: WorkUpdateCreate, member_id: str):
    """worker의 진행/완료 보고."""
    record = await _asgn_repo.find_by_id(assignment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Assignment not found")

    now = datetime.now(timezone.utc)
    orm = WorkUpdateORM(
        id=str(uuid4()),
        assignment_id=assignment_id,
        task_id=record.taskId,
        member_id=member_id,
        content=body.content,
        progress_percent=body.progressPercent,
        update_type=body.updateType,
        created_at=now,
    )
    async with AsyncSessionFactory() as session:
        session.add(orm)
        await session.commit()
        await session.refresh(orm)

    # 완료 보고 시 worker_status = done
    if body.updateType == "completion":
        from app.models.assignment import WorkerStatusPatch
        await _asgn_repo.update_worker_status(
            assignment_id, WorkerStatusPatch(workerStatus=WorkerStatus.done)
        )

    # 관리자에게 보고 알림
    if record.approvedBy:
        await _notif_repo.create(NotificationCreate(
            recipientMemberId=record.approvedBy,
            type=NotificationType.progress_submitted,
            title=f"{'완료' if body.updateType == 'completion' else '진행'} 보고 수신",
            body=f"'{record.subTaskTitle}' {body.progressPercent}% 완료.",
            relatedTaskId=record.taskId,
            relatedAssignmentId=assignment_id,
        ))

    return WorkUpdate(
        id=orm.id,
        assignmentId=orm.assignment_id,
        taskId=orm.task_id,
        memberId=orm.member_id,
        content=orm.content,
        progressPercent=orm.progress_percent,
        updateType=orm.update_type,
        createdAt=orm.created_at.isoformat(),
    )


@router.get("/assignments/{assignment_id}/updates", response_model=List[WorkUpdate])
async def get_updates(assignment_id: str):
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(WorkUpdateORM)
            .where(WorkUpdateORM.assignment_id == assignment_id)
            .order_by(WorkUpdateORM.created_at.desc())
        )
        rows = result.scalars().all()
    return [
        WorkUpdate(
            id=r.id,
            assignmentId=r.assignment_id,
            taskId=r.task_id,
            memberId=r.member_id,
            content=r.content,
            progressPercent=r.progress_percent,
            updateType=r.update_type,
            createdAt=r.created_at.isoformat(),
        )
        for r in rows
    ]
