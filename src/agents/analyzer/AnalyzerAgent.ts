/**
 * agents/analyzer/AnalyzerAgent.ts
 * 자유 텍스트로 입력된 업무를 분석하는 에이전트.
 * 카테고리, 복잡도, 필요 스킬, 예상 소요 시간, 키워드, 요약을 추출한다.
 * 결과는 context.steps.analyzed에 저장된다.
 */

import { BaseAgent } from "../base/BaseAgent";
import { AgentContext } from "../../types/workflow.types";
import { AnalysisResult } from "../../types/agent.types";
import {
  ANALYZER_SYSTEM_PROMPT,
  ANALYZER_USER_PROMPT,
} from "../../llm/prompts/analyzer.prompt";
import { PromptBuilder } from "../../llm/PromptBuilder";
import { JsonParser } from "../../llm/JsonParser";

export class AnalyzerAgent extends BaseAgent {
  constructor() {
    super("analyzer");
  }

  async execute(context: AgentContext): Promise<AgentContext> {
    context.status = "analyzing";
    context.updatedAt = new Date().toISOString();

    const userPrompt = PromptBuilder.build(ANALYZER_USER_PROMPT, {
      title:       context.input.title,
      description: context.input.description,
      deadline:    context.input.deadline ?? "없음",
    });

    try {
      const { content } = await this.claude.complete(ANALYZER_SYSTEM_PROMPT, userPrompt);
      context.steps.analyzed = JsonParser.extract<AnalysisResult>(content);
    } catch (err) {
      return this.recordError(context, (err as Error).message);
    }

    return context;
  }

  validate(context: AgentContext): boolean {
    const r = context.steps.analyzed;
    return !!r && !!r.category && r.complexity >= 1 && r.complexity <= 5;
  }
}
