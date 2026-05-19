"""
app/api/routes/tasks.py — /api/tasks 엔드포인트
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[역할]
  HTTP 요청을 파싱하고 입력값을 검증한 뒤 TaskService에 위임한다.
  비즈니스 로직은 여기에 없다 — 입력/출력 변환과 에러 코드 매핑만 담당.(비즈ㄴ니스 로직은 service 위임)

[등록 위치]
  main.py: app.include_router(tasks.router, prefix="/api/tasks")
  → 이 파일의 "/" → POST /api/tasks
  → 이 파일의 "/{task_id}" → GET /api/tasks/{task_id}

[UUID 검증]
  FastAPI의 자동 파싱에만 의존하지 않고 정규식으로 직접 검증한다.
  UUID 형식이 잘못된 경우 DB까지 가기 전에 400으로 차단해 불필요한 쿼리를 막는다.

[호출 흐름]
  POST /api/tasks
    └─ create_task() → TaskService.create_task() → DB INSERT + 백그라운드 워크플로우 시작

  GET /api/tasks/{task_id}
    └─ get_task() → TaskService.get_task_by_id() → DB SELECT
"""

import re

from fastapi import APIRouter, HTTPException, Response

from typing import List

from app.models.assignment import NotificationCreate, NotificationType
from app.models.task import Task, TaskInput
from app.repositories.member_repository import MemberRepository
from app.repositories.notification_repository import NotificationRepository
from app.services.task_service import TaskService

_notif_repo  = NotificationRepository()
_member_repo = MemberRepository()

router = APIRouter()

# UUID v4 정규식: 8-4-4-4-12 형식의 소문자 16진수
UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


@router.get("", response_model=List[Task])
async def list_tasks():
    """전체 Task 목록을 최신순으로 반환한다."""
    svc = TaskService()
    try:
        return await svc.get_all_tasks()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", status_code=201, response_model=Task)
async def create_task(body: TaskInput):
    """
    새 업무를 생성한다. 성공 시 즉시 Task를 반환하고,
    AI 에이전트 워크플로우는 백그라운드에서 시작된다.

    body: FastAPI가 요청 JSON을 TaskInput Pydantic 모델로 자동 파싱.
    status_code=201: 리소스 생성 성공을 나타내는 HTTP Created 상태코드.
    """
    svc = TaskService()
    try:
        task = await svc.create_task(body)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # 모든 관리자에게 신규 업무 등록 알림
    try:
        managers = await _member_repo.find_managers()
        for m in managers:
            await _notif_repo.create(NotificationCreate(
                recipientMemberId=m.id,
                type=NotificationType.task_registered,
                title="신규 업무가 등록되었습니다",
                body=f"'{body.title}' 업무가 등록되었습니다. AI 배정이 진행 중입니다.",
                relatedTaskId=task.id,
            ))
    except Exception:
        pass  # 알림 실패가 업무 생성 응답을 막지 않도록

    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: str):
    """Task와 관련 워크플로우·스텝·배정을 모두 삭제한다."""
    if not UUID_RE.match(task_id):
        raise HTTPException(status_code=400, detail=f"Invalid task_id: {task_id!r}")
    svc = TaskService()
    try:
        await svc.delete_task(task_id)
        return Response(status_code=204)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: str):
    """
    task_id로 업무 상태를 조회한다.
    워크플로우 진행 중이면 status="running", 완료되면 "completed"가 반환된다.
    """
    # DB 쿼리 전에 UUID 형식 검증 — 잘못된 형식이면 400 반환
    if not UUID_RE.match(task_id):
        raise HTTPException(status_code=400, detail=f"Invalid task_id: {task_id!r}")

    svc = TaskService()
    try:
        return await svc.get_task_by_id(task_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
