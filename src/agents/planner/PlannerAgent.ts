/**
 * agents/planner/PlannerAgent.ts
 * 업무 분석 결과를 기반으로 세부 실행 계획(서브태스크)을 수립하는 에이전트.
 * 결과는 context.steps.planned에 저장된다.
 */

import { BaseAgent } from "../base/BaseAgent";
import { AgentContext } from "../../types/workflow.types";
import { PlanResult } from "../../types/agent.types";
import {
  PLANNER_SYSTEM_PROMPT,
  PLANNER_USER_PROMPT,
} from "../../llm/prompts/planner.prompt";
import { PromptBuilder } from "../../llm/PromptBuilder";
import { JsonParser } from "../../llm/JsonParser";

export class PlannerAgent extends BaseAgent {
  constructor() {
    super("planner");
  }

  async execute(context: AgentContext): Promise<AgentContext> {
    context.status = "planning";
    context.updatedAt = new Date().toISOString();

    const analyzed = context.steps.analyzed!;

    const userPrompt = PromptBuilder.build(PLANNER_USER_PROMPT, {
      summary:        analyzed.summary,
      category:       analyzed.category,
      complexity:     String(analyzed.complexity),
      estimatedHours: String(analyzed.estimatedHours),
      requiredSkills: analyzed.requiredSkills.join(", "),
    });

    try {
      const { content } = await this.claude.complete(PLANNER_SYSTEM_PROMPT, userPrompt);
      context.steps.planned = JsonParser.extract<PlanResult>(content);
    } catch (err) {
      return this.recordError(context, (err as Error).message);
    }

    return context;
  }

  validate(context: AgentContext): boolean {
    const r = context.steps.planned;
    return !!r && Array.isArray(r.subTasks) && r.subTasks.length > 0;
  }
}
