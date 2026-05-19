"""
app/repositories/work_plan_repository.py — work_plans 테이블 CRUD
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, update

from app.database import AsyncSessionFactory
from app.db.orm_models import WorkPlanORM
from app.models.assignment import WorkPlan, WorkPlanCreate, WorkPlanPatch, WorkPlanStatus
from app.utils.enum_utils import enum_str


class WorkPlanRepository:

    async def create(
        self, assignment_id: str, task_id: str, member_id: str, data: WorkPlanCreate
    ) -> WorkPlan:
        now = datetime.now(timezone.utc)
        orm = WorkPlanORM(
            id=str(uuid4()),
            assignment_id=assignment_id,
            task_id=task_id,
            member_id=member_id,
            content=data.content,
            status=WorkPlanStatus.submitted.value,
            submitted_at=now,
            created_at=now,
            updated_at=now,
        )
        async with AsyncSessionFactory() as session:
            session.add(orm)
            await session.commit()
            await session.refresh(orm)
        return self._to_model(orm)

    async def find_by_assignment_id(self, assignment_id: str) -> Optional[WorkPlan]:
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(WorkPlanORM)
                .where(WorkPlanORM.assignment_id == assignment_id)
                .order_by(WorkPlanORM.created_at.desc())
                .limit(1)
            )
            orm = result.scalar_one_or_none()
        return self._to_model(orm) if orm else None

    async def find_pending(self) -> list[WorkPlan]:
        """관리자 계획 승인 대기 목록."""
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(WorkPlanORM)
                .where(WorkPlanORM.status == WorkPlanStatus.submitted.value)
                .order_by(WorkPlanORM.submitted_at.asc())
            )
            rows = result.scalars().all()
        return [self._to_model(r) for r in rows]

    async def patch(self, plan_id: str, patch: WorkPlanPatch) -> Optional[WorkPlan]:
        values: dict = {"updated_at": datetime.now(timezone.utc)}
        if patch.status is not None:
            values["status"] = enum_str(patch.status)
            if enum_str(patch.status) in ("approved", "rejected"):
                values["reviewed_at"] = datetime.now(timezone.utc)
        if patch.feedback is not None:
            values["feedback"] = patch.feedback

        async with AsyncSessionFactory() as session:
            await session.execute(
                update(WorkPlanORM).where(WorkPlanORM.id == plan_id).values(**values)
            )
            await session.commit()

        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(WorkPlanORM).where(WorkPlanORM.id == plan_id)
            )
            orm = result.scalar_one_or_none()
        return self._to_model(orm) if orm else None

    async def count_pending(self) -> int:
        from sqlalchemy import func
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(func.count()).select_from(WorkPlanORM)
                .where(WorkPlanORM.status == WorkPlanStatus.submitted.value)
            )
            return result.scalar_one()

    @staticmethod
    def _to_model(orm: WorkPlanORM) -> WorkPlan:
        return WorkPlan(
            id=orm.id,
            assignmentId=orm.assignment_id,
            taskId=orm.task_id,
            memberId=orm.member_id,
            content=orm.content,
            status=WorkPlanStatus(orm.status),
            feedback=orm.feedback,
            submittedAt=orm.submitted_at.isoformat(),
            reviewedAt=orm.reviewed_at.isoformat() if orm.reviewed_at else None,
            createdAt=orm.created_at.isoformat(),
            updatedAt=orm.updated_at.isoformat(),
        )
