"""
app/repositories/task_repository.py — tasks 테이블 CRUD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[역할]
  SQL 쿼리를 캡슐화한다. Service 레이어는 DB 직접 접근 없이
  이 클래스의 메서드만 호출한다.

[호출 흐름]
  API Route → TaskService → TaskRepository → SQLite (tasks 테이블)

[세션 사용 패턴]
  `async with AsyncSessionFactory() as session:` 블록 안에서 쿼리를 실행한다.
  블록을 벗어나면 세션이 자동으로 닫히고 커넥션이 풀에 반환된다.
  commit()을 직접 호출하는 이유: autocommit 모드가 아니기 때문.
"""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import delete, select, update

from app.database import AsyncSessionFactory
from app.db.orm_models import TaskORM
from app.models.task import Task, TaskStatus
from app.utils.enum_utils import enum_str


class TaskRepository:

    async def create(self, task: Task) -> Task:
        """
        tasks 테이블에 새 행을 INSERT하고, DB가 채운 created_at/updated_at을
        포함한 완전한 Task 모델을 반환한다.

        session.refresh(orm): INSERT 직후 DB의 실제 타임스탬프 값을 ORM 객체에 반영.
        """
        now = datetime.now(timezone.utc)
        orm = TaskORM(
            id=task.id,
            title=task.title,
            description=task.description,
            deadline=task.deadline,
            status=enum_str(task.status),
            created_at=now,
            updated_at=now,
        )
        async with AsyncSessionFactory() as session:
            session.add(orm)
            await session.commit()
            await session.refresh(orm)  # DB 저장 후 최신 상태로 동기화
        return self._to_model(orm)

    async def find_all(self) -> List[Task]:
        """
        tasks 테이블 전체를 최신순(created_at DESC)으로 조회한다.
        TaskListPage에서 목록 렌더링에 사용.
        """
        from sqlalchemy import desc
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(TaskORM).order_by(desc(TaskORM.created_at))
            )
            rows = result.scalars().all()
        return [self._to_model(r) for r in rows]

    async def find_by_id(self, task_id: str) -> Optional[Task]:
        """
        PRIMARY KEY로 단건 조회한다.
        없으면 None을 반환 — 예외를 던지지 않는다.
        존재 여부 판단은 Service 레이어가 담당.
        """
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(TaskORM).where(TaskORM.id == task_id)
            )
            orm = result.scalar_one_or_none()
        return self._to_model(orm) if orm else None

    async def delete_by_id(self, task_id: str) -> bool:
        """
        task_id로 Task를 삭제한다.
        존재하면 True, 없으면 False를 반환.
        관련 워크플로우·스텝·배정은 WorkflowRepository.delete_by_task_id()에서 먼저 정리한다.
        """
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                delete(TaskORM).where(TaskORM.id == task_id)
            )
            await session.commit()
        return result.rowcount > 0

    async def update_status(self, task_id: str, status: TaskStatus) -> None:
        """
        워크플로우 실패 시 TaskService가 호출해 Task를 failed 상태로 변경한다.
        UPDATE 구문으로 status와 updated_at만 변경한다.
        """
        async with AsyncSessionFactory() as session:
            await session.execute(
                update(TaskORM)
                .where(TaskORM.id == task_id)
                .values(status=enum_str(status), updated_at=datetime.now(timezone.utc))
            )
            await session.commit()

    @staticmethod
    def _to_model(orm: TaskORM) -> Task:
        """
        ORM 객체(DB 행) → Pydantic Task 모델 변환.
        API 응답으로 직렬화 가능한 형태로 변환하는 역할.
        이 메서드 덕분에 Service/Route 레이어는 SQLAlchemy를 몰라도 된다.
        """
        return Task(
            id=orm.id,
            title=orm.title,
            description=orm.description,
            deadline=orm.deadline,
            status=TaskStatus(orm.status),
            createdAt=orm.created_at.isoformat(),
            updatedAt=orm.updated_at.isoformat(),
        )
