"""
app/database.py — SQLAlchemy 비동기 엔진 및 세션 팩토리
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[역할]
  - SQLite 파일(smaas.db)에 대한 비동기 커넥션 엔진을 생성한다(비동기 DB 엔진 및 세션 관리 — SQLite 연결과 테이블 생성을 초기화)
  - 모든 Repository는 여기서 export된 AsyncSessionFactory를 통해 DB에 접근한다
  - Base: ORM 모델의 공통 부모 클래스 (메타데이터 등록 역할)

[실행 시점]
  앱 시작(lifespan) → init_pool() 호출 → DB 파일 + 테이블 자동 생성
  앱 종료(lifespan) → close_pool() 호출 → 커넥션 반환

[SQLite + asyncio 조합]
  aiosqlite 드라이버가 동기 SQLite I/O를 스레드풀 위에서 실행해
  asyncio 이벤트 루프를 블로킹하지 않도록 처리한다.
  연결 URL 형식: sqlite+aiosqlite:///./smaas.db
"""

from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

# 이 파일(app/database.py)의 위치를 기준으로 프로젝트 루트를 계산한다.
# __file__ → .../smaas/app/database.py
# .parent   → .../smaas/app
# .parent   → .../smaas          ← 프로젝트 루트
_DB_PATH = Path(__file__).resolve().parent.parent / "smaas.db"
DATABASE_URL = f"sqlite+aiosqlite:///{_DB_PATH}"

print(f"[DB] USING DB FILE: {_DB_PATH}")

# create_async_engine: 비동기 DB 커넥션 풀 생성
# check_same_thread=False: SQLite 기본 제약(같은 스레드만 허용)을 해제해
# asyncio + 스레드풀 조합에서도 안전하게 동작하도록 설정
engine = create_async_engine(
    DATABASE_URL,
    echo=False,                             # True로 바꾸면 실행 SQL이 콘솔에 출력됨
    connect_args={"check_same_thread": False},
)

# AsyncSessionFactory: Repository에서 `async with AsyncSessionFactory() as session:` 으로 사용
# expire_on_commit=False: commit 후에도 ORM 객체의 속성이 만료되지 않아 재쿼리 없이 반환 가능
AsyncSessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False
)


class Base(DeclarativeBase):
    """
    모든 SQLAlchemy ORM 모델이 상속받는 베이스 클래스.
    Base.metadata에 각 모델의 테이블 정보가 등록되어
    create_all() 호출 시 한 번에 생성된다.
    """
    pass


async def init_pool() -> None:
    """
    앱 시작 시 한 번 호출된다.

    1. orm_models 임포트 → Base.metadata에 모든 테이블 정보 등록
    2. create_all()   → 신규 테이블 생성 (기존 테이블은 스킵)
    3. run_migrations() → 기존 테이블의 누락 컬럼 추가 (ALTER TABLE ADD COLUMN)
    """
    from app.db import orm_models  # noqa: F401 — 임포트만으로 메타데이터에 테이블 등록됨
    from app.db.migrations import run_migrations

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await run_migrations(engine)


async def close_pool() -> None:
    """앱 종료 시 엔진(커넥션 풀)을 정리한다."""
    await engine.dispose()
