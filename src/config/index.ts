/**
 * config/index.ts
 * 환경변수를 한 곳에서 읽고 타입 안전하게 내보낸다.
 * 모든 모듈은 process.env 대신 이 파일을 통해 설정값에 접근한다.
 */

import "dotenv/config";

export const config = {
  port: Number(process.env.PORT) || 3000,
  nodeEnv: process.env.NODE_ENV || "development",

  // Claude API
  anthropicApiKey: process.env.ANTHROPIC_API_KEY || "",
  claudeModel: process.env.CLAUDE_MODEL || "claude-opus-4-6",

  // PostgreSQL
  db: {
    host: process.env.DB_HOST || "localhost",
    port: Number(process.env.DB_PORT) || 5432,
    name: process.env.DB_NAME || "smaas",
    user: process.env.DB_USER || "smaas_user",
    password: process.env.DB_PASSWORD || "",
  },

  // 알림 채널
  slack: {
    webhookUrl: process.env.SLACK_WEBHOOK_URL || "",
  },
  smtp: {
    host: process.env.SMTP_HOST || "",
    port: Number(process.env.SMTP_PORT) || 587,
    user: process.env.SMTP_USER || "",
    pass: process.env.SMTP_PASS || "",
  },
} as const;
