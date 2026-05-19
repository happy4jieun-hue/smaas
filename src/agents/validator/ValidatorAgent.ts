/**
 * agents/validator/ValidatorAgent.ts
 * 이전 모든 에이전트의 결과를 종합적으로 검증하는 에이전트.
 * 문제가 발견되면 어느 에이전트부터 재시도해야 하는지 판단한다.
 * 결과는 context.steps.validated에 저장된다.
 */

import { BaseAgent } from "../base/BaseAgent";
import { AgentContext } from "../../types/workflow.types";
import { ValidationResult } from "../../types/agent.types";
import {
  VALIDATOR_SYSTEM_PROMPT,
  VALIDATOR_USER_PROMPT,
} from "../../llm/prompts/validator.prompt";
import { PromptBuilder } from "../../llm/PromptBuilder";
import { JsonParser } from "../../llm/JsonParser";

export class ValidatorAgent extends BaseAgent {
  constructor() {
    super("validator");
  }

  async execute(context: AgentContext): Promise<AgentContext> {
    context.status = "validating";
    context.updatedAt = new Date().toISOString();

    const userPrompt = PromptBuilder.build(VALIDATOR_USER_PROMPT, {
      taskInput:      JSON.stringify(context.input),
      analysisResult: JSON.stringify(context.steps.analyzed),
      planResult:     JSON.stringify(context.steps.planned),
      matchResult:    JSON.stringify(context.steps.matched),
    });

    try {
      const { content } = await this.claude.complete(VALIDATOR_SYSTEM_PROMPT, userPrompt);
      context.steps.validated = JsonParser.extract<ValidationResult>(content);
    } catch (err) {
      return this.recordError(context, (err as Error).message);
    }

    return context;
  }

  validate(context: AgentContext): boolean {
    return context.steps.validated !== undefined;
  }
}
