"""
app/services/notification_service.py — 외부 알림 발송
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[역할]
  NotifierAgent에서 호출해 Slack 알림을 발송한다.
  subTask별 배정 요약을 메시지에 포함한다.

[알림 전송 실패 처리]
  Slack 웹훅 오류가 전체 워크플로우를 중단시키면 안 된다.
  예외를 던지지 않고 False를 반환하며,
  NotifierAgent.validate()도 항상 True를 반환해 알림 실패를 허용한다.

[SLACK_WEBHOOK_URL 미설정]
  .env에 값이 없으면 전송을 건너뛰고 빈 channels 목록을 반환한다.
  로컬 개발 환경에서는 Slack 없이도 워크플로우 전체가 동작한다.
"""

from typing import List

import httpx

from app.config import config


class NotificationService:

    async def send_slack(self, message: str) -> bool:
        """
        Slack Incoming Webhook으로 메시지를 비동기 전송한다.
        httpx.AsyncClient를 사용해 이벤트 루프를 블로킹하지 않는다.
        """
        if not config.slack_webhook_url:
            print("[NotificationService] Slack webhook not configured, skipping")
            return False
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    config.slack_webhook_url,
                    json={"text": message},
                    timeout=5,
                )
                return resp.status_code == 200
        except Exception as e:
            print(f"[NotificationService] Slack error: {e}")
            return False

    async def notify(
        self,
        task_id: str,
        assignment_summaries: List[str],
    ) -> List[str]:
        """
        subTask별 배정 요약을 포함한 워크플로우 완료 알림을 발송한다.
        성공한 채널 목록을 반환한다.
        """
        if assignment_summaries:
            body = "\n".join(assignment_summaries)
        else:
            body = "  • 배정 정보 없음"

        msg = (
            f":white_check_mark: *SMAAS* 업무 배정 완료\n"
            f"• Task: `{task_id}`\n"
            f"• subTask별 담당자:\n{body}"
        )
        channels: List[str] = []
        if await self.send_slack(msg):
            channels.append("slack")
        return channels
