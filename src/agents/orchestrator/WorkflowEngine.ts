/**
 * agents/orchestrator/WorkflowEngine.ts
 * 에이전트 실행 순서를 정의하고 단계별로 실행을 위임한다.
 * 각 단계의 성공/실패를 판단하고, Validator가 재시도를 요청하면 해당 지점부터 재실행한다.
 */

import { AgentContext } from "../../types/workflow.types";
import { AgentName } from "../../types/agent.types";
import { AnalyzerAgent } from "../analyzer/AnalyzerAgent";
import { PlannerAgent } from "../planner/PlannerAgent";
import { MatcherAgent } from "../matcher/MatcherAgent";
import { ValidatorAgent } from "../validator/ValidatorAgent";
import { NotifierAgent } from "../notifier/NotifierAgent";

const MAX_RETRIES = 2;

export class WorkflowEngine {
  private analyzer = new AnalyzerAgent();
  private planner = new PlannerAgent();
  private matcher = new MatcherAgent();
  private validator = new ValidatorAgent();
  private notifier = new NotifierAgent();

  /**
   * 컨텍스트를 받아 전체 워크플로우 단계를 순서대로 실행한다.
   * 실행 순서: analyze → plan → match → validate → notify
   * Validator가 재시도를 요청하면 해당 에이전트부터 최대 MAX_RETRIES회 재실행한다.
   */
  async execute(context: AgentContext): Promise<AgentContext> {
    let retryCount = 0;
    let retryFrom: AgentName | undefined;

    const runFrom = async (startFrom?: AgentName): Promise<AgentContext> => {
      const steps: AgentName[] = ["analyzer", "planner", "matcher", "validator"];
      const startIdx = startFrom ? steps.indexOf(startFrom) : 0;

      for (let i = startIdx; i < steps.length; i++) {
        const step = steps[i];
        context = await this.runAgent(step, context);
        if (!this.validateStep(step, context)) {
          context.status = "failed";
          return context;
        }
      }

      // Validator 결과 확인
      const validated = context.steps.validated!;
      if (!validated.valid && validated.retryFromAgent && retryCount < MAX_RETRIES) {
        retryCount++;
        console.log(`[WorkflowEngine] retry #${retryCount} from ${validated.retryFromAgent}`);
        retryFrom = validated.retryFromAgent as AgentName;
        return runFrom(retryFrom);
      }

      // 알림
      context = await this.notifier.execute(context);
      context.status = "completed";
      context.updatedAt = new Date().toISOString();
      return context;
    };

    return runFrom();
  }

  private async runAgent(name: AgentName, ctx: AgentContext): Promise<AgentContext> {
    console.log(`[WorkflowEngine] running agent: ${name}`);
    switch (name) {
      case "analyzer":  return this.analyzer.execute(ctx);
      case "planner":   return this.planner.execute(ctx);
      case "matcher":   return this.matcher.execute(ctx);
      case "validator": return this.validator.execute(ctx);
      case "notifier":  return this.notifier.execute(ctx);
      default: return ctx;
    }
  }

  private validateStep(name: AgentName, ctx: AgentContext): boolean {
    switch (name) {
      case "analyzer":  return this.analyzer.validate(ctx);
      case "planner":   return this.planner.validate(ctx);
      case "matcher":   return this.matcher.validate(ctx);
      case "validator": return this.validator.validate(ctx);
      case "notifier":  return this.notifier.validate(ctx);
      default: return true;
    }
  }
}
