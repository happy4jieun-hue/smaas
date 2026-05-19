"""
app/services/task_service.py — Task 생성·조회 비즈니스 로직
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[역할]
  API Route와 Repository 사이의 중간 레이어.
  HTTP 요청의 유효성 검사(Route 담당)와 SQL 쿼리(Repository 담당)를 제외한
  순수한 비즈니스 로직만 이 파일에 존재한다.

[핵심 설계 — 비동기 워크플로우 시작]
  POST /api/tasks 는 Task DB 저장 후 즉시 응답을 반환한다.
  워크플로우(AI 에이전트 실행)는 asyncio.create_task()로 백그라운드에서 실행된다.
  클라이언트는 응답을 기다리지 않고, 이후 GET /api/workflows/:taskId 로
  진행 상태를 폴링하는 방식으로 동작한다.

[호출 흐름]
  Route → TaskService.create_task()
    ├─ TaskRepository.create()        (DB INSERT, 즉시 반환)
    └─ asyncio.create_task(...)       (백그라운드 실행, 논블로킹)
          └─ WorkflowService.start_workflow()
"""

import asyncio
from typing import List
from uuid import uuid4

from app.models.assignment import NotificationCreate, NotificationType
from app.models.task import Task, TaskInput, TaskStatus
from app.repositories.member_repository import MemberRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.workflow_repository import WorkflowRepository
from app.services.workflow_service import WorkflowService


class TaskService:

    def __init__(self) -> None:
        self._task_repo     = TaskRepository()
        self._workflow_repo = WorkflowRepository()
        self._workflow_svc  = WorkflowService()

    async def create_task(self, input_data: TaskInput) -> Task:
        """
        Task를 DB에 저장하고 즉시 반환한다.
        워크플로우는 백그라운드에서 시작되므로 API 응답 시간과 무관하다.

        [처리 순서]
        1. UUID 생성 → Task Pydantic 모델 구성
        2. TaskRepository.create() → DB INSERT (tasks 테이블)
        3. asyncio.create_task() → 워크플로우를 이벤트 루프에 예약 (논블로킹)
        4. DB에서 받아온 record 반환 (createdAt, updatedAt 포함)
        """
        task = Task(
            id=str(uuid4()),
            title=input_data.title,
            description=input_data.description,
            deadline=input_data.deadline,
            status=TaskStatus.running,  # 생성 즉시 running 상태로 시작
            createdAt="",               # DB 저장 후 _to_model()에서 실제 값으로 채워짐
            updatedAt="",
        )
        record = await self._task_repo.create(task)

        # 워크플로우를 이벤트 루프에 태스크로 등록하고 즉시 반환
        # await 하지 않으므로 클라이언트 응답을 블로킹하지 않는다
        asyncio.create_task(
            self._start_workflow_safe(record.id, input_data)
        )
        return record

    async def delete_task(self, task_id: str) -> None:
        """
        관련 레코드(workflow_steps → assignments → workflows)를 먼저 삭제한 뒤
        Task를 삭제한다. task_id가 존재하지 않으면 KeyError를 발생시킨다.
        """
        exists = await self._task_repo.find_by_id(task_id)
        if not exists:
            raise KeyError(f"Task not found: {task_id}")
        await self._workflow_repo.delete_by_task_id(task_id)
        await self._task_repo.delete_by_id(task_id)

    async def get_all_tasks(self) -> List[Task]:
        """전체 Task 목록을 최신순으로 반환한다."""
        return await self._task_repo.find_all()

    async def get_task_by_id(self, task_id: str) -> Task:
        """
        단건 조회. 존재하지 않으면 KeyError를 발생시켜 Route가 404로 변환한다.
        """
        record = await self._task_repo.find_by_id(task_id)
        if not record:
            raise KeyError(f"Task not found: {task_id}")
        return record

    async def _start_workflow_safe(self, task_id: str, input_data: TaskInput) -> None:
        """
        워크플로우 실행을 감싸는 에러 핸들러.
        WorkflowService에서 예외가 발생하면 Task 상태를 failed로 업데이트한다.
        백그라운드 태스크이므로 여기서 예외가 발생해도 API 응답에는 영향 없다.
        """
        try:
            await self._workflow_svc.start_workflow(task_id, input_data)
            # AI 배정 완료 → 관리자에게 검토 요청 알림
            try:
                managers = await MemberRepository().find_managers()
                notif_repo = NotificationRepository()
                for m in managers:
                    await notif_repo.create(NotificationCreate(
                        recipientMemberId=m.id,
                        type=NotificationType.assignment_review,
                        title="AI 배정 결과 검토가 필요합니다",
                        body=f"'{input_data.title}' 업무의 AI 배정이 완료되었습니다. 담당자를 확인하고 승인해주세요.",
                        relatedTaskId=task_id,
                    ))
            except Exception as ne:
                from app.utils.safe_log import safe_str
                print(f"[TaskService] assignment_review failed: {safe_str(ne)}")
        except Exception as e:
            from app.utils.safe_log import safe_str
            print(f"[TaskService] workflow failed for task {task_id}: {safe_str(e)}")
            await self._task_repo.update_status(task_id, TaskStatus.failed)
