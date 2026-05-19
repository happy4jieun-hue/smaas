"""
app/api/routes/reassignment.py — 반려 / 재배정 API
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PATCH /api/assignments/{id}/reject           worker 반려 (사유 포함)
GET   /api/admin/rejected                    반려된 assignment 목록
POST  /api/admin/assignments/{id}/reassign   관리자 재배정
POST  /api/admin/assignments/{id}/rerun-matching  AI 차기 담당자 재추천
GET   /api/assignments/{id}/history          변경 이력 조회
"""

import json
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.database import AsyncSessionFactory
from app.db.orm_models import MemberORM, TaskORM
from app.llm.claude_client import ClaudeClient
from app.llm.json_parser import JsonParser
from app.llm.prompt_builder import PromptBuilder
from app.llm.prompts.matcher import MATCHER_SYSTEM_PROMPT, MATCHER_USER_PROMPT
from app.models.assignment import (
    AssignmentHistory,
    NotificationCreate,
    NotificationType,
    ReassignBody,
    RejectBody,
    WorkerStatus,
    WorkerStatusPatch,
)
from app.models.workflow import AssigneeCandidate
from app.repositories.assignment_history_repository import AssignmentHistoryRepository
from app.repositories.member_repository import MemberRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.subtask_assignment_repository import SubtaskAssignmentRepository
from app.agents.matcher_agent import _prefilter_members

router = APIRouter()
_asgn_repo    = SubtaskAssignmentRepository()
_history_repo = AssignmentHistoryRepository()
_notif_repo   = NotificationRepository()
_member_repo  = MemberRepository()


# ── 1. worker 반려 ────────────────────────────────────────────

@router.patch("/assignments/{assignment_id}/reject")
async def reject_assignment(
    assignment_id: str,
    body: RejectBody,
    member_id: Optional[str] = Query(None, description="반려하는 worker member_id"),
):
    """
    worker가 업무를 반려한다.
    - worker_status: rejected
    - rejection_reason 저장
    - 관리자에게 알림
    - 이력 기록
    """
    record = await _asgn_repo.find_by_id(assignment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if record.workerStatus not in ("pending_acceptance", "accepted"):
        raise HTTPException(
            status_code=400,
            detail=f"반려는 pending_acceptance 또는 accepted 상태에서만 가능합니다. 현재: {record.workerStatus}",
        )

    updated = await _asgn_repo.reject(
        assignment_id,
        rejected_by=member_id or "",
        reason=body.rejectionReason,
    )

    # 이력 기록
    await _history_repo.create(
        assignment_id=assignment_id,
        action="rejected",
        performed_by=member_id,
        from_member_id=record.approvedMemberId,
        reason=body.rejectionReason,
    )

    # 관리자에게 알림
    if record.approvedBy:
        await _notif_repo.create(NotificationCreate(
            recipientMemberId=record.approvedBy,
            type=NotificationType.worker_rejected,
            title="업무가 반려되었습니다",
            body=f"'{record.subTaskTitle}' 업무를 worker가 반려했습니다. 재배정이 필요합니다.\n사유: {body.rejectionReason}",
            relatedTaskId=record.taskId,
            relatedAssignmentId=assignment_id,
        ))

    return updated


# ── 2. 반려된 assignment 목록 ─────────────────────────────────

@router.get("/admin/rejected", response_model=List[dict])
async def list_rejected():
    """관리자용 — 반려된 assignment 목록 (member/task 이름 포함)."""
    records = await _asgn_repo.find_rejected()
    if not records:
        return []

    async with AsyncSessionFactory() as session:
        member_ids = set()
        task_ids   = set()
        for r in records:
            task_ids.add(r.taskId)
            if r.approvedMemberId: member_ids.add(r.approvedMemberId)
            if r.previousMemberId: member_ids.add(r.previousMemberId)
            if r.approvedBy:       member_ids.add(r.approvedBy)

        m_rows = (await session.execute(select(MemberORM).where(MemberORM.id.in_(member_ids)))).scalars().all()
        member_map = {m.id: m.name for m in m_rows}

        t_rows = (await session.execute(select(TaskORM).where(TaskORM.id.in_(task_ids)))).scalars().all()
        task_map = {t.id: t.title for t in t_rows}

    return [
        {
            "id":                r.id,
            "taskId":            r.taskId,
            "taskTitle":         task_map.get(r.taskId, ""),
            "subTaskTitle":      r.subTaskTitle,
            "subTaskDescription": r.subTaskDescription,
            "priority":          r.priority,
            "workerStatus":      r.workerStatus,
            "rejectionReason":   r.rejectionReason,
            "rejectedAt":        r.rejectedAt,
            "approvedMemberId":  r.approvedMemberId,
            "approvedMemberName": member_map.get(r.approvedMemberId or "", ""),
            "previousMemberId":  r.previousMemberId,
            "previousMemberName": member_map.get(r.previousMemberId or "", ""),
            "reassignmentCount": r.reassignmentCount,
            "candidates":        [c.model_dump() for c in r.candidates],
            "updatedAt":         r.updatedAt,
        }
        for r in records
    ]


# ── 3. 관리자 재배정 ──────────────────────────────────────────

@router.post("/admin/assignments/{assignment_id}/reassign")
async def reassign(
    assignment_id: str,
    body: ReassignBody,
    manager_id: Optional[str] = Query(None, description="재배정하는 관리자 member_id"),
):
    """
    관리자가 반려된 assignment를 새 멤버에게 재배정한다.
    - approved_member_id 변경
    - previous_member_id 보존
    - worker_status → pending_acceptance
    - 이력 기록
    - 새 worker에게 알림
    """
    record = await _asgn_repo.find_by_id(assignment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Assignment not found")

    updated = await _asgn_repo.reassign(
        assignment_id,
        new_member_id=body.newMemberId,
        reassigned_by=manager_id or "",
        memo=body.memo,
    )

    # 이력 기록
    await _history_repo.create(
        assignment_id=assignment_id,
        action="reassigned",
        performed_by=manager_id,
        from_member_id=record.approvedMemberId,
        to_member_id=body.newMemberId,
        memo=body.memo,
    )

    # 새 worker에게 알림
    await _notif_repo.create(NotificationCreate(
        recipientMemberId=body.newMemberId,
        type=NotificationType.reassigned,
        title="업무가 재배정되었습니다",
        body=f"'{record.subTaskTitle}' 업무가 재배정되었습니다. 확인 후 수락해주세요.",
        relatedTaskId=record.taskId,
        relatedAssignmentId=assignment_id,
    ))

    return updated


# ── 4. AI 차기 담당자 재추천 ──────────────────────────────────

@router.post("/admin/assignments/{assignment_id}/rerun-matching")
async def rerun_matching(
    assignment_id: str,
    exclude_member_id: Optional[str] = Query(None, description="제외할 member_id (반려자)"),
):
    """
    반려된 assignment에 대해 AI가 차기 담당자를 재추천한다.
    - 기존 반려자를 제외하고 다시 매칭
    - DB는 업데이트하지 않음 — 관리자가 결과를 보고 reassign 결정
    """
    record = await _asgn_repo.find_by_id(assignment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Assignment not found")

    # 가용 멤버 조회
    all_members = await _member_repo.find_available()
    if exclude_member_id:
        all_members = [m for m in all_members if m.id != exclude_member_id]
    # 이미 반려한 사람도 제외 (approvedMemberId)
    if record.approvedMemberId:
        all_members = [m for m in all_members if m.id != record.approvedMemberId]

    if not all_members:
        raise HTTPException(status_code=400, detail="재추천 가능한 멤버가 없습니다.")

    top_members = _prefilter_members(all_members, [], top_k=5)
    profiles    = _member_repo.to_profiles(top_members)

    subtask_json = json.dumps(
        [{"index": record.subTaskIndex, "title": record.subTaskTitle,
          "description": record.subTaskDescription or "", "priority": record.priority or "medium",
          "dependsOn": []}],
        ensure_ascii=False,
    )
    member_json = json.dumps([p.model_dump() for p in profiles], ensure_ascii=False)

    user_prompt = PromptBuilder.build(MATCHER_USER_PROMPT, {
        "category":       "재배정",
        "requiredSkills": "",
        "complexity":     "3",
        "estimatedHours": "8",
        "subTasksJson":   subtask_json,
        "memberProfiles": member_json,
    })

    try:
        claude = ClaudeClient()
        resp   = await claude.complete(MATCHER_SYSTEM_PROMPT, user_prompt, max_tokens=800)
        data   = JsonParser.extract(resp.content)
        valid_ids = {m.id for m in all_members}
        raw_assigns = data.get("assignments", [])

        candidates = []
        recommended_id = None
        if raw_assigns:
            raw = raw_assigns[0]
            candidates = [
                AssigneeCandidate.model_validate(c)
                for c in raw.get("candidates", [])
                if c.get("memberId") in valid_ids
            ]
            candidates.sort(key=lambda c: c.score, reverse=True)
            recommended_id = raw.get("recommendedMemberId")
            if recommended_id not in valid_ids:
                recommended_id = candidates[0].memberId if candidates else None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 매칭 실패: {e}")

    return {
        "assignmentId":        assignment_id,
        "nextRecommendedMemberId": recommended_id,
        "candidates":          [c.model_dump() for c in candidates],
    }


# ── 5. 변경 이력 조회 ─────────────────────────────────────────

@router.get("/assignments/{assignment_id}/history", response_model=List[AssignmentHistory])
async def get_history(assignment_id: str):
    """assignment의 반려/재배정 이력 조회."""
    return await _history_repo.find_by_assignment_id(assignment_id)
