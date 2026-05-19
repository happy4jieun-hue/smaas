"""
app/api/routes/dashboard.py — 관리자 대시보드 통계 API
GET /api/dashboard
"""

from fastapi import APIRouter
from sqlalchemy import func, select

from app.database import AsyncSessionFactory
from app.db.orm_models import SubtaskAssignmentORM, TaskORM
from app.models.assignment import DashboardStats
from app.repositories.work_plan_repository import WorkPlanRepository

router = APIRouter()
_plan_repo = WorkPlanRepository()


@router.get("", response_model=DashboardStats)
async def get_dashboard():
    async with AsyncSessionFactory() as session:
        # 전체 task 수
        total_tasks = (
            await session.execute(select(func.count()).select_from(TaskORM))
        ).scalar_one()

        # task 상태별 집계
        status_rows = (
            await session.execute(
                select(TaskORM.status, func.count().label("cnt"))
                .group_by(TaskORM.status)
            )
        ).all()
        tasks_by_status = {r[0]: r[1] for r in status_rows}

        # 관리자 검토 대기 중인 subtask 수 (status=pending)
        pending_assignments = (
            await session.execute(
                select(func.count()).select_from(SubtaskAssignmentORM)
                .where(SubtaskAssignmentORM.status == "pending")
            )
        ).scalar_one()

        # 최근 task 5개
        recent_rows = (
            await session.execute(
                select(TaskORM).order_by(TaskORM.created_at.desc()).limit(5)
            )
        ).scalars().all()
        recent_tasks = [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "deadline": t.deadline,
                "createdAt": t.created_at.isoformat(),
            }
            for t in recent_rows
        ]

    pending_plans = await _plan_repo.count_pending()

    return DashboardStats(
        totalTasks=total_tasks,
        pendingAssignments=pending_assignments,
        pendingWorkPlans=pending_plans,
        unreadNotifications=0,   # member_id 없이 전체 통계 — 추후 확장
        tasksByStatus=tasks_by_status,
        recentTasks=recent_tasks,
    )
