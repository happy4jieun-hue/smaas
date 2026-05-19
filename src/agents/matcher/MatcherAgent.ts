/**
 * agents/matcher/MatcherAgent.ts
 * 업무 분석 결과와 DB의 담당자 프로필을 비교하여 최적 담당자를 추천하는 에이전트.
 * MemberRepository에서 가용 인원을 조회하고 Claude에 프로필을 전달한다.
 * 결과는 context.steps.matched에 저장된다.
 */

import { BaseAgent } from "../base/BaseAgent";
import { AgentContext } from "../../types/workflow.types";
import { MatchResult } from "../../types/agent.types";
import {
  MATCHER_SYSTEM_PROMPT,
  MATCHER_USER_PROMPT,
} from "../../llm/prompts/matcher.prompt";
import { PromptBuilder } from "../../llm/PromptBuilder";
import { JsonParser } from "../../llm/JsonParser";
import { MemberRepository } from "../../db/repositories/MemberRepository";

export class MatcherAgent extends BaseAgent {
  private memberRepo: MemberRepository;

  constructor() {
    super("matcher");
    this.memberRepo = new MemberRepository();
  }

  async execute(context: AgentContext): Promise<AgentContext> {
    context.status = "matching";
    context.updatedAt = new Date().toISOString();

    const analyzed = context.steps.analyzed!;

    // 1. DB에서 가용 인원 조회 (capacity > 0, 필요 스킬 교집합 우선)
    const members = await this.memberRepo.findAvailable(analyzed.requiredSkills);

    if (members.length === 0) {
      return this.recordError(
        context,
        "가용 가능한 팀원이 없습니다. 모든 팀원의 capacity가 0이거나 members 테이블이 비어 있습니다."
      );
    }

    // 2. Claude 프롬프트에 주입할 프로필 목록 생성
    const profiles = this.memberRepo.toProfiles(members);
    const memberProfiles = JSON.stringify(profiles, null, 2);

    const userPrompt = PromptBuilder.build(MATCHER_USER_PROMPT, {
      category:       analyzed.category,
      requiredSkills: analyzed.requiredSkills.join(", "),
      complexity:     String(analyzed.complexity),
      estimatedHours: String(analyzed.estimatedHours),
      memberProfiles,
    });

    // 3. Claude 호출
    try {
      const { content } = await this.claude.complete(MATCHER_SYSTEM_PROMPT, userPrompt);
      const result = JsonParser.extract<MatchResult>(content);

      // 4. Claude가 반환한 memberId가 실제 DB에 존재하는지 검증
      const validIds = new Set(members.map((m) => m.id));

      result.candidates = result.candidates.filter((c) => {
        if (!validIds.has(c.memberId)) {
          console.warn(`[MatcherAgent] 알 수 없는 memberId 제거: ${c.memberId}`);
          return false;
        }
        return true;
      });

      // score 내림차순 정렬 보장
      result.candidates.sort((a, b) => b.score - a.score);

      // topCandidateId 일관성 보장
      if (result.candidates.length > 0) {
        result.topCandidateId = result.candidates[0].memberId;
      }

      context.steps.matched = result;
    } catch (err) {
      return this.recordError(context, (err as Error).message);
    }

    return context;
  }

  validate(context: AgentContext): boolean {
    const r = context.steps.matched;
    if (!r) return false;
    if (!Array.isArray(r.candidates) || r.candidates.length === 0) return false;
    if (!r.topCandidateId) return false;
    // topCandidateId가 candidates 목록에 실제로 포함되어 있어야 함
    return r.candidates.some((c) => c.memberId === r.topCandidateId);
  }
}
