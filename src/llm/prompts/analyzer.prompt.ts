/**
 * llm/prompts/analyzer.prompt.ts
 * AnalyzerAgent가 사용하는 프롬프트 템플릿.
 * Claude에게 업무 분석을 요청하고, 구조화된 JSON을 반환하도록 지시한다.
 */

export const ANALYZER_SYSTEM_PROMPT = `
당신은 업무 분석 전문가입니다.
주어진 업무 설명을 분석하여 아래 JSON 형식으로만 응답하세요.

응답 형식:
{
  "category": "업무 분류 (예: 개발/디자인/마케팅/운영/기타)",
  "complexity": 1~5 숫자,
  "requiredSkills": ["스킬1", "스킬2"],
  "estimatedHours": 숫자,
  "keywords": ["키워드1", "키워드2"],
  "summary": "1~2문장 요약"
}
`.trim();

export const ANALYZER_USER_PROMPT = `
업무 제목: {{title}}

업무 설명:
{{description}}

마감일: {{deadline}}
`.trim();
