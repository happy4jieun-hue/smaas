from typing import List

from app.models.member import MemberInput, MemberRecord, MemberUpdate
from app.repositories.member_repository import MemberRepository


class MemberService:

    def __init__(self) -> None:
        self._repo = MemberRepository()

    async def get_all(self) -> List[MemberRecord]:
        return await self._repo.find_all()

    async def get_by_id(self, member_id: str) -> MemberRecord:
        record = await self._repo.find_by_id(member_id)
        if not record:
            raise KeyError(f"Member not found: {member_id}")
        return record

    async def create(self, data: MemberInput) -> MemberRecord:
        return await self._repo.create(data)

    async def update(self, member_id: str, data: MemberUpdate) -> MemberRecord:
        record = await self._repo.update(member_id, data)
        if not record:
            raise KeyError(f"Member not found: {member_id}")
        return record

    async def delete(self, member_id: str) -> None:
        deleted = await self._repo.delete_by_id(member_id)
        if not deleted:
            raise KeyError(f"Member not found: {member_id}")
