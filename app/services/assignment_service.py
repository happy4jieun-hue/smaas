from typing import List

from app.models.workflow import AssignmentPatch, SubTaskAssignmentRecord
from app.repositories.subtask_assignment_repository import SubtaskAssignmentRepository


class AssignmentService:

    def __init__(self) -> None:
        self._repo = SubtaskAssignmentRepository()

    async def get_by_task_id(self, task_id: str) -> List[SubTaskAssignmentRecord]:
        return await self._repo.find_by_task_id(task_id)

    async def patch(self, assignment_id: str, patch: AssignmentPatch) -> SubTaskAssignmentRecord:
        record = await self._repo.patch(assignment_id, patch)
        if not record:
            raise KeyError(f"Assignment not found: {assignment_id}")
        return record

    async def approve_all(self, task_id: str) -> dict:
        count = await self._repo.approve_all_pending(task_id)
        return {"approvedCount": count}
