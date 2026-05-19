/**
 * services/NotificationService.ts
 * Slack, Email, Webhook 등 외부 채널로 알림을 전송하는 서비스.
 * NotifierAgent에서 직접 외부 API를 호출하지 않고 이 서비스에 위임한다.
 * 채널별 포맷 변환과 전송 실패 처리를 담당한다.
 */

import https from "https";
import { AgentContext } from "../types/workflow.types";
import { NotificationResult } from "../types/agent.types";
import { config } from "../config";

export class NotificationService {
  async send(context: AgentContext): Promise<NotificationResult> {
    const channels: string[] = [];
    const errors: string[] = [];

    if (config.slack.webhookUrl) {
      try {
        await this.sendSlack(context);
        channels.push("slack");
      } catch (err) {
        errors.push(`slack: ${(err as Error).message}`);
      }
    }

    if (config.smtp.host && config.smtp.user) {
      try {
        await this.sendEmail(context);
        channels.push("email");
      } catch (err) {
        errors.push(`email: ${(err as Error).message}`);
      }
    }

    if (errors.length > 0) {
      console.warn("[NotificationService] partial failures:", errors.join(", "));
    }

    return { channels, success: channels.length > 0 || errors.length === 0 };
  }

  private async sendSlack(context: AgentContext): Promise<void> {
    const matched = context.steps.matched;
    const text =
      `*[Smaas] 워크플로우 완료*\n` +
      `업무: ${context.input.title}\n` +
      `담당자 ID: ${matched?.topCandidateId ?? "미배정"}\n` +
      `상태: ${context.status}`;

    await this.postJson(config.slack.webhookUrl, { text });
  }

  private async sendEmail(_context: AgentContext): Promise<void> {
    // SMTP 전송은 nodemailer 등 라이브러리 연동 후 구현
    console.log("[NotificationService] email 전송은 nodemailer 연동 후 활성화됩니다.");
  }

  private postJson(url: string, body: object): Promise<void> {
    return new Promise((resolve, reject) => {
      const data = JSON.stringify(body);
      const parsed = new URL(url);
      const req = https.request(
        {
          hostname: parsed.hostname,
          path: parsed.pathname + parsed.search,
          method: "POST",
          headers: { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(data) },
        },
        (res) => {
          if (res.statusCode && res.statusCode >= 400) {
            reject(new Error(`HTTP ${res.statusCode}`));
          } else {
            resolve();
          }
        }
      );
      req.on("error", reject);
      req.write(data);
      req.end();
    });
  }
}
