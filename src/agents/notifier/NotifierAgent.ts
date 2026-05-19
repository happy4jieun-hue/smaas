/**
 * agents/notifier/NotifierAgent.ts
 * 워크플로우 최종 결과를 외부 채널로 전송하는 에이전트.
 * Slack, Email, Webhook 등 채널별 포맷을 분기 처리한다.
 * NotificationService에 전송을 위임하고, 결과를 context.steps.notified에 저장한다.
 */

import { BaseAgent } from "../base/BaseAgent";
import { AgentContext } from "../../types/workflow.types";
import { NotificationService } from "../../services/NotificationService";

export class NotifierAgent extends BaseAgent {
  private notificationService: NotificationService;

  constructor() {
    super("notifier");
    this.notificationService = new NotificationService();
  }

  async execute(context: AgentContext): Promise<AgentContext> {
    context.status = "notifying";
    context.updatedAt = new Date().toISOString();

    try {
      const result = await this.notificationService.send(context);
      context.steps.notified = result;
    } catch (err) {
      return this.recordError(context, (err as Error).message);
    }

    return context;
  }

  validate(context: AgentContext): boolean {
    return context.steps.notified?.success === true;
  }
}
