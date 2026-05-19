"""
app/api/routes/assignments.py — subTask 배정 승인 엔드포인트
GET  /api/tasks/{task_id}/assignments        → subTask 배정 목록 조회
PATCH /api/assignments/{assignment_id}       → 승인/변경/반려 (+ worker 알림)
POST /api/tasks/{task_id}/assignments/approve-all → 일괄 승인 (+ worker 알림)
"""

import re
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.models.assignment import NotificationCreate, NotificationType
from app.models.workflow import AssignmentPatch, SubTaskAssignmentRecord
from app.repositories.notification_repository import NotificationRepository
from app.repositories.subtask_assignment_repository import SubtaskAssignmentRepository
from app.services.assignment_service import AssignmentService

router = APIRouter()
_notif_repo = NotificationRepository()
_asgn_repo = SubtaskAssignmentRepository()

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


@router.get("/tasks/{task_id}/assignments", response_model=List[SubTaskAssignmentRecord])
async def get_assignments(task_id: str):
    if not UUID_RE.match(task_id):
        raise HTTPException(status_code=400, detail=f"Invalid task_id: {task_id!r}")
    return await AssignmentService().get_by_task_id(task_id)


@router.patch("/assignments/{assignment_id}", response_model=SubTaskAssignmentRecord)
async def patch_assignment(
    assignment_id: str,
    body: AssignmentPatch,
    approved_by: Optional[str] = Query(None, description="승인한 관리자 member_id"),
):
    if not UUID_RE.match(assignment_id):
        raise HTTPException(status_code=400, detail=f"Invalid assignment_id: {assignment_id!r}")
    try:
        updated = await _asgn_repo.patch(assignment_id, body, approved_by=approved_by)
        if not updated:
            raise KeyError(f"Assignment not found: {assignment_id}")
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 승인/변경 시 worker에게 알림
    status_str = body.status.value if body.status else None
    if status_str in ("approved", "changed") and updated.approvedMemberId:
        await _notif_repo.create(NotificationCreate(
            recipientMemberId=updated.approvedMemberId,
            type=NotificationType.task_assigned,
            title="업무가 배정되었습니다",
            body=f"subTask '{updated.subTaskTitle}' 이(가) 배정되었습니다. 확인 후 수락해주세요.",
            relatedTaskId=updated.taskId,
            relatedAssignmentId=assignment_id,
        ))

    return updated


@router.post("/tasks/{task_id}/assignments/approve-all")
async def approve_all(
    task_id: str,
    approved_by: Optional[str] = Query(None, description="승인한 관리자 member_id"),
):
    if not UUID_RE.match(task_id):
        raise HTTPException(status_code=400, detail=f"Invalid task_id: {task_id!r}")

    count = await _asgn_repo.approve_all_pending(task_id, approved_by=approved_by)

    # 일괄 승인 후 각 worker에게 알림
    assignments = await _asgn_repo.find_by_task_id(task_id)
    for a in assignments:
        if a.approvedMemberId and a.status == "approved":
            await _notif_repo.create(NotificationCreate(
                recipientMemberId=a.approvedMemberId,
                type=NotificationType.task_assigned,
                title="업무가 배정되었습니다",
                body=f"subTask '{a.subTaskTitle}' 이(가) 배정되었습니다. 확인 후 수락해주세요.",
                relatedTaskId=task_id,
                relatedAssignmentId=a.id,
            ))

    return {"approvedCount": count}
