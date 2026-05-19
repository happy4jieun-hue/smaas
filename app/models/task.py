from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel


class TaskStatus(str, Enum):
    pending   = "pending"
    running   = "running"
    completed = "completed"
    failed    = "failed"


class TaskInput(BaseModel):
    title:       str
    description: str
    deadline:    Optional[str] = None


class Task(TaskInput):
    id:        str
    status:    TaskStatus
    createdAt: str
    updatedAt: str
