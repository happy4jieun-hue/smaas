"""
main.py — SMAAS FastAPI 앱 진입점
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[전체 요청 흐름]

  프론트엔드 (Vue)
      │  POST /api/tasks        → Task 생성 + Workflow 비동기 시작
      │  GET  /api/tasks/:id    → Task 상태 조회
      │  GET  /api/workflows/:taskId → Workflow 결과 조회
      ▼
  main.py  (FastAPI 앱, 라우터 등록)
      ▼
  app/api/routes/tasks.py | workflows.py  (HTTP 요청 파싱, 입력 검증)
      ▼
  app/services/task_service.py | workflow_service.py  (비즈니스 로직)
      ▼
  app/repositories/task_repository.py | workflow_repository.py  (DB 쿼리)
      ▼
  SQLite (smaas.db)  ←→  app/db/orm_models.py (테이블 정의)

[AI 에이전트 흐름 — Task 생성 직후 백그라운드에서 실행]

  WorkflowService.start_workflow()
      ▼
  OrchestratorAgent.run()
      ▼
  WorkflowEngine.execute()
      ├─ AnalyzerAgent  : 업무 분석 (카테고리, 난이도, 필요 스킬 추출)
      ├─ PlannerAgent   : 서브태스크 분해 및 계획 수립
      ├─ MatcherAgent   : DB 멤버 조회 → Claude가 최적 담당자 추천
      ├─ ValidatorAgent : 전체 결과 품질 검증, 재시도 여부 판단
      └─ NotifierAgent  : Slack 알림 발송

FastAPI 앱 엔트리포인트 — 서버 시작 시 DB 초기화 및 라우터 등록을 담당

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# Windows cp949 콘솔 안전 출력 설정 - 다른 import보다 반드시 먼저 실행
from app.utils.safe_log import configure_safe_logging
configure_safe_logging()

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sqlalchemy import func, select

from app.database import _DB_PATH, AsyncSessionFactory, close_pool, init_pool
from app.db.orm_models import MemberORM
from app.api.routes import assignments, members, tasks, workflows
from app.api.routes import dashboard, my_tasks, notifications, work_plans
from app.api.routes import admin_overview, reassignment


# ── 앱 생명주기 관리 ──────────────────────────────────────────
# lifespan: FastAPI 앱 시작/종료 시 실행되는 컨텍스트 매니저.
# - 시작 시: SQLite 파일 생성 + 테이블 자동 생성 (init_pool)
# - 종료 시: DB 커넥션 풀 정리 (close_pool)
@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.utils.safe_log import configure_safe_logging, install_asyncio_exception_handler
    configure_safe_logging()              # uvicorn이 logger를 설정한 후 재적용
    install_asyncio_exception_handler()   # asyncio 백그라운드 태스크 예외 안전 처리
    await init_pool()
    yield
    await close_pool()


app = FastAPI(title="SMAAS", version="0.1.0", lifespan=lifespan)

# CORS 허용 — 로컬 Vue 개발 서버(기본 포트 5173)에서 API 호출 가능하도록 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 라우터 등록 ───────────────────────────────────────────────
# prefix를 붙여 등록하면 tasks.py 내부 경로("/", "/{id}")가
# 실제로는 "/api/tasks", "/api/tasks/{id}" 로 매핑된다.
app.include_router(tasks.router,         prefix="/api/tasks",         tags=["tasks"])
app.include_router(workflows.router,     prefix="/api/workflows",     tags=["workflows"])
app.include_router(members.router,       prefix="/api/members",       tags=["members"])
app.include_router(assignments.router,   prefix="/api",               tags=["assignments"])
app.include_router(dashboard.router,     prefix="/api/dashboard",     tags=["dashboard"])
app.include_router(my_tasks.router,      prefix="/api",               tags=["my-tasks"])
app.include_router(work_plans.router,    prefix="/api",               tags=["work-plans"])
app.include_router(notifications.router,    prefix="/api/notifications", tags=["notifications"])
app.include_router(admin_overview.router,  prefix="/api/admin",         tags=["admin"])
app.include_router(reassignment.router,    prefix="/api",               tags=["reassignment"])


@app.get("/health")
async def health():
    """서버가 살아있는지 확인하는 헬스체크 엔드포인트."""
    return {"status": "ok"}


@app.get("/debug/db-path")
async def debug_db_path():
    """현재 서버가 바라보는 SQLite 파일의 절대경로를 반환한다."""
    return {"db_path": str(_DB_PATH), "exists": _DB_PATH.exists()}


@app.get("/debug/members-count")
async def debug_members_count():
    """members 테이블의 전체 인원과 capacity > 0 인원을 반환한다."""
    async with AsyncSessionFactory() as session:
        total = (await session.execute(select(func.count()).select_from(MemberORM))).scalar_one()
        available = (
            await session.execute(
                select(func.count()).select_from(MemberORM).where(MemberORM.capacity > 0)
            )
        ).scalar_one()
    return {"totalMembers": total, "availableMembers": available}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """라우터에서 처리되지 않은 예외를 최종 캐치해 JSON 형태로 반환한다."""
    return JSONResponse(status_code=500, content={"error": str(exc)})
