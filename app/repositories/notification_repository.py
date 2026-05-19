"""
app/repositories/notification_repository.py — notifications 테이블 CRUD
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import select, update

from app.database import AsyncSessionFactory
from app.db.orm_models import NotificationORM
from app.models.assignment import Notification, NotificationCreate, NotificationType
from app.utils.enum_utils import enum_str


class NotificationRepository:

    async def create(self, data: NotificationCreate) -> Notification:
        orm = NotificationORM(
            id=str(uuid4()),
            recipient_member_id=data.recipientMemberId,
            type=enum_str(data.type),
            title=data.title,
            body=data.body,
            is_read=False,
            related_task_id=data.relatedTaskId,
            related_assignment_id=data.relatedAssignmentId,
            created_at=datetime.now(timezone.utc),
        )
        async with AsyncSessionFactory() as session:
            session.add(orm)
            await session.commit()
            await session.refresh(orm)
        return self._to_model(orm)

    async def find_by_member_id(
        self, member_id: str, unread_only: bool = False
    ) -> List[Notification]:
        async with AsyncSessionFactory() as session:
            stmt = (
                select(NotificationORM)
                .where(NotificationORM.recipient_member_id == member_id)
                .order_by(NotificationORM.created_at.desc())
            )
            if unread_only:
                stmt = stmt.where(NotificationORM.is_read == False)
            result = await session.execute(stmt)
            rows = result.scalars().all()
        return [self._to_model(r) for r in rows]

    async def mark_read(self, notification_id: str) -> None:
        async with AsyncSessionFactory() as session:
            await session.execute(
                update(NotificationORM)
                .where(NotificationORM.id == notification_id)
                .values(is_read=True)
            )
            await session.commit()

    async def mark_all_read(self, member_id: str) -> int:
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                update(NotificationORM)
                .where(
                    NotificationORM.recipient_member_id == member_id,
                    NotificationORM.is_read == False,
                )
                .values(is_read=True)
            )
            await session.commit()
        return result.rowcount

    async def count_unread(self, member_id: str) -> int:
        from sqlalchemy import func
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(func.count()).select_from(NotificationORM)
                .where(
                    NotificationORM.recipient_member_id == member_id,
                    NotificationORM.is_read == False,
                )
            )
            return result.scalar_one()

    @staticmethod
    def _to_model(orm: NotificationORM) -> Notification:
        return Notification(
            id=orm.id,
            recipientMemberId=orm.recipient_member_id,
            type=NotificationType(orm.type),
            title=orm.title,
            body=orm.body,
            isRead=orm.is_read,
            relatedTaskId=orm.related_task_id,
            relatedAssignmentId=orm.related_assignment_id,
            createdAt=orm.created_at.isoformat(),
        )
