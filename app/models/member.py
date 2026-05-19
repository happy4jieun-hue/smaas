from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class MemberProfile(BaseModel):
    """Claude 프롬프트에 전달하는 멤버 정보 (내부 정보 제외)."""
    id:                    str
    name:                  str
    team:                  Optional[str]
    role:                  Optional[str]
    grade:                 Optional[str]
    skills:                List[str]
    preferred_stages:      List[str]
    services:              List[str]
    capacity:              int
    current_load:          int
    available_hours_today: float


class MemberRecord(MemberProfile):
    """DB에서 읽어온 완전한 멤버 정보."""
    email:                    Optional[str]
    userRole:                 str            # manager | worker
    available_hours_tomorrow: float
    timezone:                 str
    createdAt:                str
    updatedAt:                str


class MemberInput(BaseModel):
    """POST /api/members 요청 body."""
    name:                    str
    email:                   Optional[str] = None
    team:                    Optional[str] = None
    role:                    Optional[str] = None
    grade:                   Optional[str] = None
    userRole:                str = "worker"  # manager | worker
    skills:                  List[str] = []
    preferred_stages:        List[str] = []
    services:                List[str] = []
    capacity:                int = 100
    current_load:            int = 0
    available_hours_today:   float = 8.0
    available_hours_tomorrow: float = 8.0
    timezone:                str = "Asia/Seoul"


class MemberUpdate(BaseModel):
    """PATCH /api/members/{id} 요청 body — 모든 필드 선택적."""
    name:                    Optional[str] = None
    email:                   Optional[str] = None
    team:                    Optional[str] = None
    role:                    Optional[str] = None
    grade:                   Optional[str] = None
    userRole:                Optional[str] = None  # manager | worker
    skills:                  Optional[List[str]] = None
    preferred_stages:        Optional[List[str]] = None
    services:                Optional[List[str]] = None
    capacity:                Optional[int] = None
    current_load:            Optional[int] = None
    available_hours_today:   Optional[float] = None
    available_hours_tomorrow: Optional[float] = None
    timezone:                Optional[str] = None
