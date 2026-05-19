/**
 * agents/base/BaseAgent.ts
 * 모든 에이전트가 상속하는 추상 클래스.
 * 공통 인터페이스(execute, validate)를 강제하고
 * ClaudeClient 인스턴스를 제공한다.
 */

import { ClaudeClient } from "../../llm/ClaudeClient";
import { AgentContext } from "../../types/workflow.types";
import { AgentName } from "../../types/agent.types";

export abstract class BaseAgent {
  readonly name: AgentName;
  protected claude: ClaudeClient;

  constructor(name: AgentName) {
    this.name = name;
    this.claude = new ClaudeClient();
  }

  /**
   * 에이전트 실행. 컨텍스트를 받아 처리하고 업데이트된 컨텍스트를 반환한다.
   */
  abstract execute(context: AgentContext): Promise<AgentContext>;

  /**
   * 자신의 실행 결과가 컨텍스트에 올바르게 저장됐는지 검사한다.
   * Orchestrator가 다음 단계로 넘어가기 전에 호출한다.
   */
  abstract validate(context: AgentContext): boolean;

  /** 에러를 컨텍스트에 기록하는 헬퍼 */
  protected recordError(context: AgentContext, message: string): AgentContext {
    context.errors.push({
      agentName: this.name,
      message,
      timestamp: new Date().toISOString(),
    });
    return context;
  }
}
