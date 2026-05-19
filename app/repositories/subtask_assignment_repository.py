"""
app/repositories/subtask_assignment_repository.py — subtask_assignments 테이블 CRUD
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.database import AsyncSessionFactory
from app.db.orm_models import SubtaskAssignmentORM
from app.utils.enum_utils import enum_str
from app.models.assignment import WorkerStatus, WorkerStatusPatch
from app.models.workflow import (
    AssigneeCandidate,
    AssignmentPatch,
    AssignmentStatus,
    RoleRecommendationResult,
    SubTaskAssignmentRecord,
)


class SubtaskAssignmentRepository:

    async def save_assignments(
        self,
        task_id: str,
        workflow_id: str,
        assignments: List[RoleRecommendationResult],
        subtasks_meta: list,
    ) -> None:
        """역할 추천 결과를 subtask_assignments 테이블에 저장한다."""
        now = datetime.now(timezone.utc)
        async with AsyncSessionFactory() as session:
            for asgn in assignments:
                meta = subtasks_meta[asgn.subTaskIndex] if asgn.subTaskIndex < len(subtasks_meta) else None

                stmt = (
                    sqlite_insert(SubtaskAssignmentORM)
                    .values(
                        id=str(uuid4()),
                        task_id=task_id,
                        workflow_id=workflow_id,
                        subtask_index=asgn.subTaskIndex,
                        subtask_title=asgn.subTaskTitle,
                        subtask_description=meta.description if meta else None,
                        priority=meta.priority if meta else None,
                        suggested_role=asgn.suggestedRole,
                        suggested_reason=asgn.suggestedReason,
                        candidates=[],              # 역할 추천 구조에서 candidates 미사용
                        recommended_member_id=None, # legacy 컬럼 — 미사용
                        approved_member_id=None,
                        approved_by=None,
                        approved_at=None,
                        status=AssignmentStatus.pending.value,
                        worker_status=WorkerStatus.pending_acceptance.value,
                        reason=asgn.suggestedReason,
                        memo=None,
                        created_at=now,
                        updated_at=now,
                    )
                    .on_conflict_do_update(
                        index_elements=["workflow_id", "subtask_index"],
                        set_={
                            "suggested_role":   asgn.suggestedRole,
                            "suggested_reason": asgn.suggestedReason,
                            "candidates":       [],
                            "reason":           asgn.suggestedReason,
                            "status":           AssignmentStatus.pending.value,
                            "worker_status":    WorkerStatus.pending_acceptance.value,
                            "updated_at":       now,
                        },
                    )
                )
                await session.execute(stmt)
            await session.commit()

    async def find_by_task_id(self, task_id: str) -> List[SubTaskAssignmentRecord]:
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(SubtaskAssignmentORM)
                .where(SubtaskAssignmentORM.task_id == task_id)
                .order_by(SubtaskAssignmentORM.subtask_index)
            )
            rows = result.scalars().all()
        return [self._to_model(r) for r in rows]

    async def find_by_member_id(self, member_id: str) -> List[SubTaskAssignmentRecord]:
        """worker의 내 업무 목록 — approved_member_id 기준."""
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(SubtaskAssignmentORM)
                .where(SubtaskAssignmentORM.approved_member_id == member_id)
                .order_by(SubtaskAssignmentORM.updated_at.desc())
            )
            rows = result.scalars().all()
        return [self._to_model(r) for r in rows]

    async def find_by_id(self, assignment_id: str) -> Optional[SubTaskAssignmentRecord]:
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(SubtaskAssignmentORM).where(SubtaskAssignmentORM.id == assignment_id)
            )
            orm = result.scalar_one_or_none()
        return self._to_model(orm) if orm else None

    async def patch(
        self, assignment_id: str, patch: AssignmentPatch, approved_by: Optional[str] = None
    ) -> Optional[SubTaskAssignmentRecord]:
        """관리자 승인/수정/반려. 승인 시 worker_status를 pending_acceptance로 설정."""
        now = datetime.now(timezone.utc)
        values: dict = {"updated_at": now}

        if patch.status is not None:
            values["status"] = enum_str(patch.status)
            # 관리자가 승인/변경하면 worker에게 수락 대기 상태로 전환
            if enum_str(patch.status) in ("approved", "changed"):
                values["worker_status"] = WorkerStatus.pending_acceptance.value
                values["approved_at"] = now
                if approved_by:
                    values["approved_by"] = approved_by
        if patch.approvedMemberId is not None:
            values["approved_member_id"] = patch.approvedMemberId
        if patch.memo is not None:
            values["memo"] = patch.memo

        async with AsyncSessionFactory() as session:
            await session.execute(
                update(SubtaskAssignmentORM)
                .where(SubtaskAssignmentORM.id == assignment_id)
                .values(**values)
            )
            await session.commit()

        return await self.find_by_id(assignment_id)

    async def update_worker_status(
        self, assignment_id: str, patch: WorkerStatusPatch
    ) -> Optional[SubTaskAssignmentRecord]:
        """worker 수락/반려/진행/완료 처리."""
        values: dict = {
            "worker_status": enum_str(patch.workerStatus),
            "updated_at":    datetime.now(timezone.utc),
        }
        if patch.memo is not None:
            values["memo"] = patch.memo

        async with AsyncSessionFactory() as session:
            await session.execute(
                update(SubtaskAssignmentORM)
                .where(SubtaskAssignmentORM.id == assignment_id)
                .values(**values)
            )
            await session.commit()

        return await self.find_by_id(assignment_id)

    async def approve_all_pending(self, task_id: str, approved_by: Optional[str] = None) -> int:
        """approved_member_id가 이미 선택된 pending 항목만 일괄 승인한다.
        담당자가 선택되지 않은 항목은 건너뛴다 (관리자가 직접 배정해야 함).
        """
        now = datetime.now(timezone.utc)
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(SubtaskAssignmentORM)
                .where(
                    SubtaskAssignmentORM.task_id == task_id,
                    SubtaskAssignmentORM.status == AssignmentStatus.pending.value,
                    SubtaskAssignmentORM.approved_member_id.is_not(None),
                )
            )
            pending_rows = result.scalars().all()

            for row in pending_rows:
                await session.execute(
                    update(SubtaskAssignmentORM)
                    .where(SubtaskAssignmentORM.id == row.id)
                    .values(
                        status=AssignmentStatus.approved.value,
                        approved_by=approved_by,
                        approved_at=now,
                        worker_status=WorkerStatus.pending_acceptance.value,
                        updated_at=now,
                    )
                )
            await session.commit()
        return len(pending_rows)

    async def reject(
        self, assignment_id: str, rejected_by: str, reason: str
    ) -> Optional[SubTaskAssignmentRecord]:
        """worker가 업무를 반려. worker_status=rejected, rejection_reason 저장."""
        now = datetime.now(timezone.utc)
        async with AsyncSessionFactory() as session:
            await session.execute(
                update(SubtaskAssignmentORM)
                .where(SubtaskAssignmentORM.id == assignment_id)
                .values(
                    worker_status=WorkerStatus.rejected.value,
                    rejection_reason=reason,
                    rejected_at=now,
                    updated_at=now,
                )
            )
            await session.commit()
        return await self.find_by_id(assignment_id)

    async def reassign(
        self,
        assignment_id: str,
        new_member_id: str,
        reassigned_by: str,
        memo: Optional[str] = None,
    ) -> Optional[SubTaskAssignmentRecord]:
        """관리자가 재배정. previous_member_id 보존, worker_status 초기화."""
        now = datetime.now(timezone.utc)
        current = await self.find_by_id(assignment_id)
        if not current:
            return None
        async with AsyncSessionFactory() as session:
            await session.execute(
                update(SubtaskAssignmentORM)
                .where(SubtaskAssignmentORM.id == assignment_id)
                .values(
                    approved_member_id=new_member_id,
                    previous_member_id=current.approvedMemberId,
                    worker_status=WorkerStatus.pending_acceptance.value,
                    approved_by=reassigned_by,
                    approved_at=now,
                    reassignment_count=(current.reassignmentCount or 0) + 1,
                    memo=memo,
                    updated_at=now,
                )
            )
            await session.commit()
        return await self.find_by_id(assignment_id)

    async def find_rejected(self) -> List[SubTaskAssignmentRecord]:
        """반려된 assignment 전체 목록."""
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(SubtaskAssignmentORM)
                .where(SubtaskAssignmentORM.worker_status == WorkerStatus.rejected.value)
                .order_by(SubtaskAssignmentORM.updated_at.desc())
            )
            rows = result.scalars().all()
        return [self._to_model(r) for r in rows]

    async def delete_by_task_id(self, task_id: str) -> None:
        from sqlalchemy import delete as sql_delete
        async with AsyncSessionFactory() as session:
            await session.execute(
                sql_delete(SubtaskAssignmentORM).where(
                    SubtaskAssignmentORM.task_id == task_id
                )
            )
            await session.commit()

    @staticmethod
    def _to_model(orm: SubtaskAssignmentORM) -> SubTaskAssignmentRecord:
        raw = orm.candidates if isinstance(orm.candidates, list) else []
        candidates = [AssigneeCandidate.model_validate(c) for c in raw]
        return SubTaskAssignmentRecord(
            id=orm.id,
            taskId=orm.task_id,
            workflowId=orm.workflow_id,
            subTaskIndex=orm.subtask_index,
            subTaskTitle=orm.subtask_title,
            subTaskDescription=orm.subtask_description,
            priority=orm.priority,
            suggestedRole=orm.suggested_role,
            suggestedReason=orm.suggested_reason,
            candidates=candidates,
            recommendedMemberId=orm.recommended_member_id,
            approvedMemberId=orm.approved_member_id,
            approvedBy=orm.approved_by,
            approvedAt=orm.approved_at.isoformat() if orm.approved_at else None,
            status=AssignmentStatus(orm.status),
            workerStatus=orm.worker_status or "pending_acceptance",
            reason=orm.reason,
            memo=orm.memo,
            rejectionReason=orm.rejection_reason,
            rejectedAt=orm.rejected_at.isoformat() if orm.rejected_at else None,
            previousMemberId=orm.previous_member_id,
            reassignmentCount=orm.reassignment_count or 0,
            createdAt=orm.created_at.isoformat(),
            updatedAt=orm.updated_at.isoformat(),
        )
