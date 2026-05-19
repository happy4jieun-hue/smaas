"""
app/repositories/assignment_history_repository.py — 반려/재배정 감사 로그
"""

from datetime import datetime, timezone
from typing import List
from uuid import uuid4

from sqlalchemy import select

from app.database import AsyncSessionFactory
from app.db.orm_models import AssignmentHistoryORM
from app.models.assignment import AssignmentHistory


class AssignmentHistoryRepository:

    async def create(
        self,
        assignment_id: str,
        action: str,
        performed_by: str | None = None,
        from_member_id: str | None = None,
        to_member_id: str | None = None,
        reason: str | None = None,
        memo: str | None = None,
    ) -> AssignmentHistory:
        orm = AssignmentHistoryORM(
            id=str(uuid4()),
            assignment_id=assignment_id,
            action=action,
            from_member_id=from_member_id,
            to_member_id=to_member_id,
            reason=reason,
            memo=memo,
            performed_by=performed_by,
            created_at=datetime.now(timezone.utc),
        )
        async with AsyncSessionFactory() as session:
            session.add(orm)
            await session.commit()
            await session.refresh(orm)
        return self._to_model(orm)

    async def find_by_assignment_id(self, assignment_id: str) -> List[AssignmentHistory]:
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(AssignmentHistoryORM)
                .where(AssignmentHistoryORM.assignment_id == assignment_id)
                .order_by(AssignmentHistoryORM.created_at.asc())
            )
            rows = result.scalars().all()
        return [self._to_model(r) for r in rows]

    @staticmethod
    def _to_model(orm: AssignmentHistoryORM) -> AssignmentHistory:
        return AssignmentHistory(
            id=orm.id,
            assignmentId=orm.assignment_id,
            action=orm.action,
            fromMemberId=orm.from_member_id,
            toMemberId=orm.to_member_id,
            reason=orm.reason,
            memo=orm.memo,
            performedBy=orm.performed_by,
            createdAt=orm.created_at.isoformat(),
        )
