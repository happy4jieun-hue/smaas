/**
 * llm/prompts/planner.prompt.ts
 * PlannerAgent가 사용하는 프롬프트 템플릿.
 * 업무를 서브태스크로 분해하고 의존관계와 우선순위를 결정하도록 지시한다.
 */

export const PLANNER_SYSTEM_PROMPT = `
당신은 프로젝트 계획 전문가입니다.
주어진 업무를 실행 가능한 서브태스크로 분해하여 아래 JSON 형식으로만 응답하세요.
복잡도가 1~2인 단순 업무는 서브태스크 없이 단일 태스크로 유지하세요.

응답 형식:
{
  "subTasks": [
    {
      "title": "서브태스크 이름",
      "description": "설명",
      "priority": "high | medium | low",
      "dependsOn": ["의존하는 서브태스크 title"]
    }
  ],
  "estimatedTotalHours": 숫자
}
`.trim();

export const PLANNER_USER_PROMPT = `
업무 요약: {{summary}}
카테고리: {{category}}
복잡도: {{complexity}}
예상 시간: {{estimatedHours}}시간
필요 스킬: {{requiredSkills}}
`.trim();
