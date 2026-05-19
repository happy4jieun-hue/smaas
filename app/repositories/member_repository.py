"""
app/repositories/member_repository.py — members 테이블 CRUD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[역할]
  MatcherAgent가 사용하는 팀원 조회 및 Members CRUD를 담당한다.
  capacity > 0 (업무 수용 가능) 인 멤버만 Matcher에 전달하며,
  필요 스킬이 주어지면 스킬이 겹치는 멤버만 필터링한다.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import delete, select

from app.database import AsyncSessionFactory
from app.db.orm_models import MemberORM
from app.models.member import MemberInput, MemberProfile, MemberRecord, MemberUpdate


class MemberRepository:

    # ── Matcher용 조회 ──────────────────────────────────────

    async def find_available(
        self, required_skills: Optional[List[str]] = None
    ) -> List[MemberRecord]:
        """
        capacity > 0 인 멤버를 조회하고, 스킬 필터를 적용해 반환한다.
        capacity 내림차순 정렬 — Claude 프롬프트에서 여유 있는 멤버가 먼저 보임.
        """
        async with AsyncSessionFactory() as session:
            total_result = await session.execute(select(MemberORM))
            total_count = len(total_result.scalars().all())

            result = await session.execute(
                select(MemberORM).where(MemberORM.capacity > 0)
            )
            rows = result.scalars().all()

        print(f"[MemberRepo] total={total_count}, capacity>0={len(rows)}, required_skills={required_skills}")

        members = [self._to_record(r) for r in rows]

        if required_skills:
            required_set = {s.lower() for s in required_skills}
            skill_filtered = [
                m for m in members
                if required_set & {s.lower() for s in m.skills}
            ]
            if skill_filtered:
                print(f"[MemberRepo] skill-filtered={len(skill_filtered)} of {len(members)}")
                members = skill_filtered
            else:
                # soft fallback: 스킬 일치 없어도 전원 후보로 사용
                print(f"[MemberRepo] skill filter empty -> soft fallback to all {len(members)}")

        return sorted(members, key=lambda m: m.capacity, reverse=True)

    def to_profiles(self, members: List[MemberRecord]) -> List[MemberProfile]:
        """Claude 프롬프트용 프로필 — 내부 정보(email 등) 제외."""
        return [
            MemberProfile(
                id=m.id,
                name=m.name,
                team=m.team,
                role=m.role,
                grade=m.grade,
                skills=m.skills,
                preferred_stages=m.preferred_stages,
                services=m.services,
                capacity=m.capacity,
                current_load=m.current_load,
                available_hours_today=m.available_hours_today,
            )
            for m in members
        ]

    # ── Members CRUD ────────────────────────────────────────

    async def find_managers(self) -> List[MemberRecord]:
        """user_role == 'manager' 인 멤버 목록 반환 (전체 알림 발송용)."""
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(MemberORM).where(MemberORM.user_role == "manager")
            )
            rows = result.scalars().all()
        return [self._to_record(r) for r in rows]

    async def find_all(self) -> List[MemberRecord]:
        async with AsyncSessionFactory() as session:
            result = await session.execute(select(MemberORM).order_by(MemberORM.name))
            rows = result.scalars().all()
        return [self._to_record(r) for r in rows]

    async def find_by_id(self, member_id: str) -> Optional[MemberRecord]:
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(MemberORM).where(MemberORM.id == member_id)
            )
            orm = result.scalar_one_or_none()
        return self._to_record(orm) if orm else None

    async def create(self, data: MemberInput) -> MemberRecord:
        now = datetime.now(timezone.utc)
        orm = MemberORM(
            id=str(uuid4()),
            name=data.name,
            email=data.email,
            team=data.team,
            role=data.role,
            grade=data.grade,
            user_role=data.userRole,
            skills=data.skills,
            preferred_stages=data.preferred_stages,
            services=data.services,
            capacity=data.capacity,
            current_load=data.current_load,
            available_hours_today=data.available_hours_today,
            available_hours_tomorrow=data.available_hours_tomorrow,
            timezone=data.timezone,
            created_at=now,
            updated_at=now,
        )
        async with AsyncSessionFactory() as session:
            session.add(orm)
            await session.commit()
            await session.refresh(orm)
        return self._to_record(orm)

    async def update(self, member_id: str, data: MemberUpdate) -> Optional[MemberRecord]:
        raw = data.model_dump()
        # userRole(camel) → user_role(snake) 변환 후 None 제거
        if "userRole" in raw:
            raw["user_role"] = raw.pop("userRole")
        updates = {k: v for k, v in raw.items() if v is not None}
        if not updates:
            return await self.find_by_id(member_id)
        updates["updated_at"] = datetime.now(timezone.utc)

        from sqlalchemy import update as sql_update
        async with AsyncSessionFactory() as session:
            await session.execute(
                sql_update(MemberORM).where(MemberORM.id == member_id).values(**updates)
            )
            await session.commit()
        return await self.find_by_id(member_id)

    async def delete_by_id(self, member_id: str) -> bool:
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                delete(MemberORM).where(MemberORM.id == member_id)
            )
            await session.commit()
        return result.rowcount > 0

    @staticmethod
    def _to_record(orm: MemberORM) -> MemberRecord:
        return MemberRecord(
            id=orm.id,
            name=orm.name,
            email=orm.email,
            team=orm.team,
            role=orm.role,
            grade=orm.grade,
            userRole=orm.user_role or "worker",
            skills=orm.skills if isinstance(orm.skills, list) else [],
            preferred_stages=orm.preferred_stages if isinstance(orm.preferred_stages, list) else [],
            services=orm.services if isinstance(orm.services, list) else [],
            capacity=orm.capacity,
            current_load=orm.current_load,
            available_hours_today=orm.available_hours_today,
            available_hours_tomorrow=orm.available_hours_tomorrow,
            timezone=orm.timezone,
            createdAt=orm.created_at.isoformat(),
            updatedAt=orm.updated_at.isoformat(),
        )
