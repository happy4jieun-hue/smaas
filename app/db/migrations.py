"""
app/db/migrations.py — SQLite 스키마 마이그레이션
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
멱등(idempotent) — 이미 존재하는 컬럼/테이블은 건너뛴다.
신규 테이블(work_plans, work_updates, notifications)은 create_all()이 처리한다.
"""

import logging
from typing import List

from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


# (테이블명, 컬럼명, ALTER TABLE SQL)
_NEW_COLUMNS: List[tuple[str, str, str]] = [
    # members — 기존 컬럼들
    ("members", "role",                   "ALTER TABLE members ADD COLUMN role TEXT"),
    ("members", "grade",                  "ALTER TABLE members ADD COLUMN grade TEXT"),
    ("members", "preferred_stages",       "ALTER TABLE members ADD COLUMN preferred_stages JSON NOT NULL DEFAULT '[]'"),
    ("members", "services",               "ALTER TABLE members ADD COLUMN services JSON NOT NULL DEFAULT '[]'"),
    ("members", "current_load",           "ALTER TABLE members ADD COLUMN current_load INTEGER NOT NULL DEFAULT 0"),
    ("members", "available_hours_today",  "ALTER TABLE members ADD COLUMN available_hours_today REAL NOT NULL DEFAULT 8.0"),
    ("members", "available_hours_tomorrow", "ALTER TABLE members ADD COLUMN available_hours_tomorrow REAL NOT NULL DEFAULT 8.0"),
    ("members", "timezone",               "ALTER TABLE members ADD COLUMN timezone TEXT NOT NULL DEFAULT 'Asia/Seoul'"),
    # members — 신규: 시스템 역할 (manager | worker)
    ("members", "user_role",              "ALTER TABLE members ADD COLUMN user_role TEXT NOT NULL DEFAULT 'worker'"),

    # subtask_assignments — 신규 컬럼
    ("subtask_assignments", "worker_status",      "ALTER TABLE subtask_assignments ADD COLUMN worker_status TEXT NOT NULL DEFAULT 'pending_acceptance'"),
    ("subtask_assignments", "approved_by",        "ALTER TABLE subtask_assignments ADD COLUMN approved_by TEXT"),
    ("subtask_assignments", "approved_at",        "ALTER TABLE subtask_assignments ADD COLUMN approved_at DATETIME"),
    # subtask_assignments — AI 역할 추천 (role recommendation 구조)
    ("subtask_assignments", "suggested_role",     "ALTER TABLE subtask_assignments ADD COLUMN suggested_role TEXT"),
    ("subtask_assignments", "suggested_reason",   "ALTER TABLE subtask_assignments ADD COLUMN suggested_reason TEXT"),
    # subtask_assignments — 반려/재배정 추적
    ("subtask_assignments", "rejection_reason",   "ALTER TABLE subtask_assignments ADD COLUMN rejection_reason TEXT"),
    ("subtask_assignments", "rejected_at",        "ALTER TABLE subtask_assignments ADD COLUMN rejected_at DATETIME"),
    ("subtask_assignments", "previous_member_id", "ALTER TABLE subtask_assignments ADD COLUMN previous_member_id TEXT"),
    ("subtask_assignments", "reassignment_count", "ALTER TABLE subtask_assignments ADD COLUMN reassignment_count INTEGER NOT NULL DEFAULT 0"),
]


async def _get_columns(conn, table: str) -> set[str]:
    result = await conn.exec_driver_sql(f"PRAGMA table_info({table})")
    rows = result.fetchall()
    return {row[1] for row in rows}


async def run_migrations(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        for table, col_name, alter_sql in _NEW_COLUMNS:
            existing = await _get_columns(conn, table)
            if col_name not in existing:
                await conn.exec_driver_sql(alter_sql)
                print(f"[Migration] {table}.{col_name} 추가")
            # 이미 존재하면 skip (멱등)

        print("[Migration] done - DB schema up to date")
