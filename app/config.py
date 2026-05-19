"""
app/config.py — 환경변수 중앙 관리
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
pydantic-settings를 사용해 .env 파일을 읽고 타입 안전하게 제공한다.
모든 모듈은 process.env 대신 여기서 내보내는 `config` 객체를 통해
설정값에 접근해야 한다 — 값이 바뀌어도 이 파일 하나만 수정하면 된다.

필수 설정:
  ANTHROPIC_API_KEY  Claude API 키 (없으면 에이전트 호출 불가)

선택 설정:
  SLACK_WEBHOOK_URL  Slack 알림용 Incoming Webhook URL
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    # env_file: 로컬 실행 시 .env 파일에서 값을 읽는다
    # extra="ignore": .env에 정의되지 않은 키가 있어도 에러 없이 무시한다
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    port:     int = 3000
    node_env: str = "development"

    # ── Claude API ───────────────────────────────────────────
    anthropic_api_key: str = ""
    claude_model:      str = "claude-opus-4-6"

    # ── SQLite (파일 경로는 database.py에서 직접 지정) ───────
    # PostgreSQL 시절의 db_* 설정은 제거됨

    # ── 알림 채널 ────────────────────────────────────────────
    slack_webhook_url: str = ""   # 비어 있으면 NotificationService가 전송을 건너뜀


# 싱글턴처럼 사용 — 전 모듈에서 `from app.config import config` 로 임포트
config = Config()
