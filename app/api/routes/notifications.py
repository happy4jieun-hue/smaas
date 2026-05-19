"""
app/api/routes/notifications.py — 인앱 알림 API
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GET  /api/notifications?member_id=          알림 목록
GET  /api/notifications/count?member_id=    미읽음 수 (폴링용 경량 엔드포인트)
PATCH /api/notifications/{id}/read          읽음 처리
POST  /api/notifications/read-all           전체 읽음
GET  /api/notifications/stream?member_id=   SSE 스트림 (2차 확장용)

[폴링 → SSE 전환 전략]
  1차: App.vue가 30s 간격으로 GET /count 폴링
  2차: App.vue가 GET /stream (SSE) 연결 → 미읽음 수 변화 시 즉시 푸시
  백엔드 코드는 이미 2차를 지원한다. 프론트만 EventSource로 전환하면 된다.
"""

import asyncio
import json
from typing import List

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.models.assignment import Notification
from app.repositories.notification_repository import NotificationRepository

router = APIRouter()
_repo = NotificationRepository()


# ── 1. 목록 조회 ───────────────────────────────────────────────

@router.get("", response_model=List[Notification])
async def list_notifications(
    member_id: str = Query(..., description="수신자 member_id"),
    unread_only: bool = Query(False),
):
    return await _repo.find_by_member_id(member_id, unread_only=unread_only)


# ── 2. 미읽음 수 (경량 폴링 전용) ────────────────────────────

@router.get("/count")
async def get_unread_count(member_id: str = Query(..., description="수신자 member_id")):
    """
    미읽음 알림 수만 반환한다.
    App.vue가 30s 마다 이 엔드포인트를 호출해 badge를 갱신한다.
    전체 목록(GET /)보다 DB 부하가 훨씬 낮다.
    """
    count = await _repo.count_unread(member_id)
    return {"count": count}


# ── 3. 읽음 처리 ───────────────────────────────────────────────

@router.patch("/{notification_id}/read")
async def mark_read(notification_id: str):
    await _repo.mark_read(notification_id)
    return {"ok": True}


@router.post("/read-all")
async def mark_all_read(member_id: str = Query(...)):
    count = await _repo.mark_all_read(member_id)
    return {"marked": count}


# ── 4. SSE 스트림 (2차 확장용) ────────────────────────────────

@router.get("/stream")
async def notification_stream(member_id: str = Query(..., description="수신자 member_id")):
    """
    Server-Sent Events 스트림.
    미읽음 수가 변화할 때마다 클라이언트에 즉시 푸시한다.

    [프론트 전환 방법 — 2차 작업 시]
      // App.vue의 pollUnread() + setInterval 제거 후:
      const es = new EventSource(`/api/notifications/stream?member_id=${memberId}`)
      es.onmessage = (e) => {
        const data = JSON.parse(e.data)
        unreadCount.value = data.count
      }
      // onUnmounted: es.close()

    [현재 1차] App.vue는 여전히 30s 폴링을 사용하며 이 엔드포인트는 미사용.
    백엔드는 이미 준비되어 있다.
    """
    async def generator():
        last_count = -1
        while True:
            try:
                count = await _repo.count_unread(member_id)
                if count != last_count:
                    last_count = count
                    yield f"data: {json.dumps({'count': count})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                break
            await asyncio.sleep(10)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
