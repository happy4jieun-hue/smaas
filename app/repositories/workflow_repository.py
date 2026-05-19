"""
app/repositories/workflow_repository.py — workflows / workflow_steps / assignments 테이블
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[역할]
  워크플로우 생성·수정·조회와 에이전트 단계 결과 저장을 담당한다.
  Service 레이어(WorkflowService)가 이 클래스를 통해서만 DB에 접근한다.

[핵심 설계 — pending 선저장]
  1. start_workflow() 시작 시 즉시 pending 레코드를 INSERT
     → 프론트가 GET /api/workflows/:taskId 를 바로 호출해도 404가 발생하지 않는다
  2. 에이전트 실행이 끝나면 update_workflow()로 최종 상태와 context를 덮어쓴다

[Upsert 전략 — workflow_steps]
  에이전트가 재시도될 때 같은 (workflow_id, step_name) 행이 다시 INSERT되면
  ON CONFLICT DO UPDATE로 기존 행을 덮어쓴다.
  SQLite dialect의 `sqlite_insert`를 사용해야 이 기능이 동작한다.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.database import AsyncSessionFactory
from app.db.orm_models import AssignmentORM, WorkflowORM, WorkflowStepORM
from app.models.workflow import AgentContext, WorkflowRecord, WorkflowStatus
from app.utils.enum_utils import enum_str


class WorkflowRepository:

    async def delete_by_task_id(self, task_id: str) -> None:
        """
        task_id에 연결된 레코드를 FK 자식부터 순서대로 삭제한다.
        workflow_steps → subtask_assignments → assignments → workflows
        """
        from app.db.orm_models import SubtaskAssignmentORM
        async with AsyncSessionFactory() as session:
            # 1. 이 task의 workflow id 목록 수집
            result = await session.execute(
                select(WorkflowORM.id).where(WorkflowORM.task_id == task_id)
            )
            workflow_ids = [row[0] for row in result.all()]

            # 2. workflow_steps 삭제
            if workflow_ids:
                await session.execute(
                    delete(WorkflowStepORM).where(
                        WorkflowStepORM.workflow_id.in_(workflow_ids)
                    )
                )

            # 3. subtask_assignments 삭제 (task_id FK)
            await session.execute(
                delete(SubtaskAssignmentORM).where(
                    SubtaskAssignmentORM.task_id == task_id
                )
            )

            # 4. assignments 삭제 (task_id FK)
            await session.execute(
                delete(AssignmentORM).where(AssignmentORM.task_id == task_id)
            )

            # 5. workflows 삭제
            await session.execute(
                delete(WorkflowORM).where(WorkflowORM.task_id == task_id)
            )

            await session.commit()

    async def create_workflow(
        self,
        workflow_id: str,
        task_id: str,
        status: WorkflowStatus,
        context: AgentContext,
    ) -> None:
        """
        워크플로우 초기 레코드를 DB에 저장한다.
        WorkflowService.start_workflow()가 에이전트 실행 전에 호출한다.

        context.model_dump(mode="json"):
          Pydantic 모델 → Python dict 변환.
          JSON 컬럼에 저장되므로 datetime 등이 문자열로 직렬화된다.
        """
        now = datetime.now(timezone.utc)
        orm = WorkflowORM(
            id=workflow_id,
            task_id=task_id,
            status=enum_str(status),
            context=context.model_dump(mode="json"),  # AgentContext 전체를 JSON으로 직렬화
            created_at=now,
            updated_at=now,
        )
        async with AsyncSessionFactory() as session:
            session.add(orm)
            await session.commit()

    async def update_workflow(
        self,
        workflow_id: str,
        status: WorkflowStatus,
        context: AgentContext,
    ) -> None:
        """
        에이전트 실행 완료(또는 실패) 후 status와 context를 최종 상태로 갱신한다.
        UPDATE 구문으로 두 컬럼만 변경하므로 불필요한 오버헤드가 없다.
        """
        async with AsyncSessionFactory() as session:
            await session.execute(
                update(WorkflowORM)
                .where(WorkflowORM.id == workflow_id)
                .values(
                    status=enum_str(status),
                    context=context.model_dump(mode="json"),
                    updated_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()

    async def find_by_task_id(self, task_id: str) -> Optional[WorkflowRecord]:
        """
        task_id로 가장 최근 워크플로우를 조회한다.
        GET /api/workflows/:taskId 가 호출될 때 실행된다.

        ORDER BY created_at DESC LIMIT 1:
          동일 task에 재실행이 생겨도 최신 워크플로우만 반환한다.
        """
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(WorkflowORM)
                .where(WorkflowORM.task_id == task_id)
                .order_by(WorkflowORM.created_at.desc())
                .limit(1)
            )
            orm = result.scalar_one_or_none()
        return self._to_model(orm) if orm else None

    async def create_step(
        self,
        workflow_id: str,
        step_name: str,
        step_status: str,
        input_data: dict,
        output_data: Optional[dict],
        error: Optional[str],
    ) -> None:
        """
        에이전트 단계 결과를 workflow_steps 테이블에 저장한다.

        ON CONFLICT DO UPDATE (Upsert):
          동일 (workflow_id, step_name)이 이미 있으면 덮어쓴다.
          에이전트 재시도 시 이전 실패 결과가 성공 결과로 교체된다.
          sqlite_insert (SQLite 방언)을 사용해야 이 구문이 지원된다.
        """
        step_id = str(uuid4())
        stmt = (
            sqlite_insert(WorkflowStepORM)
            .values(
                id=step_id,
                workflow_id=workflow_id,
                step_name=step_name,
                step_status=step_status,
                input=input_data,
                output=output_data,
                error=error,
                created_at=datetime.now(timezone.utc),
            )
            .on_conflict_do_update(
                index_elements=["workflow_id", "step_name"],
                set_={
                    "step_status": step_status,
                    "input":       input_data,
                    "output":      output_data,
                    "error":       error,
                    "created_at":  datetime.now(timezone.utc),
                },
            )
        )
        async with AsyncSessionFactory() as session:
            await session.execute(stmt)
            await session.commit()

    async def create_assignment(
        self,
        task_id: str,
        member_id: str,
        score: int,
        reason: str,
    ) -> None:
        """
        MatcherAgent가 선택한 최종 담당자를 assignments 테이블에 기록한다.
        재매칭 시 새 행을 추가하여 배정 히스토리를 보존한다.
        """
        orm = AssignmentORM(
            id=str(uuid4()),
            task_id=task_id,
            member_id=member_id,
            score=score,
            reason=reason,
            assigned_at=datetime.now(timezone.utc),
        )
        async with AsyncSessionFactory() as session:
            session.add(orm)
            await session.commit()

    @staticmethod
    def _to_model(orm: WorkflowORM) -> WorkflowRecord:
        """
        ORM 객체 → Pydantic WorkflowRecord 변환.
        context 컬럼(JSON dict)을 AgentContext Pydantic 모델로 역직렬화한다.
        이 변환 덕분에 API 응답에 steps, errors 등이 구조화된 형태로 포함된다.
        """
        ctx = orm.context if isinstance(orm.context, dict) else {}
        return WorkflowRecord(
            id=orm.id,
            taskId=orm.task_id,
            status=WorkflowStatus(orm.status),
            context=AgentContext.model_validate(ctx),  # dict → AgentContext Pydantic 모델
            createdAt=orm.created_at.isoformat(),
            updatedAt=orm.updated_at.isoformat(),
        )
