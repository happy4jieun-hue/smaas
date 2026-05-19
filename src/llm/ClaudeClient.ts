/**
 * llm/ClaudeClient.ts
 * Anthropic Claude API 호출을 추상화하는 클래스.
 * 모든 에이전트는 직접 SDK를 import하지 않고 이 클라이언트를 통해 LLM을 호출한다.
 * 재시도 로직, 토큰 사용량 로깅 등 공통 처리를 여기서 담당한다.
 */

import Anthropic from "@anthropic-ai/sdk";
import { config } from "../config";

export interface LLMResponse {
  content: string;
  inputTokens: number;
  outputTokens: number;
}

const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 1_000;

export class ClaudeClient {
  private client: Anthropic;
  private model: string;

  constructor() {
    this.client = new Anthropic({ apiKey: config.anthropicApiKey });
    this.model = config.claudeModel;
  }

  async complete(systemPrompt: string, userPrompt: string): Promise<LLMResponse> {
    let lastError: Error | undefined;

    for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
      try {
        const message = await this.client.messages.create({
          model: this.model,
          max_tokens: 4096,
          system: systemPrompt,
          messages: [{ role: "user", content: userPrompt }],
        });

        const content =
          message.content[0].type === "text" ? message.content[0].text : "";

        console.log(
          `[LLM] tokens in=${message.usage.input_tokens} out=${message.usage.output_tokens}`
        );

        return {
          content,
          inputTokens: message.usage.input_tokens,
          outputTokens: message.usage.output_tokens,
        };
      } catch (err) {
        lastError = err as Error;
        console.warn(`[LLM] attempt ${attempt}/${MAX_RETRIES} failed: ${lastError.message}`);
        if (attempt < MAX_RETRIES) {
          await new Promise((r) => setTimeout(r, RETRY_DELAY_MS * attempt));
        }
      }
    }

    throw lastError ?? new Error("LLM request failed after retries");
  }

  // completeAsJson 제거됨 — 각 에이전트에서 complete() + JsonParser.extract() 사용
}
