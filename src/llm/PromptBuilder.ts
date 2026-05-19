/**
 * llm/PromptBuilder.ts
 * 각 에이전트의 프롬프트 템플릿에 런타임 데이터를 주입하는 유틸리티.
 * 템플릿 문자열의 {{key}} 플레이스홀더를 실제 값으로 치환한다.
 */

export class PromptBuilder {
  /**
   * 템플릿의 {{key}} 형식 플레이스홀더를 variables 객체의 값으로 치환한다.
   * @example
   * PromptBuilder.build("업무: {{title}}", { title: "API 개발" })
   * // => "업무: API 개발"
   */
  static build(template: string, variables: Record<string, string | number>): string {
    return template.replace(/\{\{(\w+)\}\}/g, (_, key) => {
      const value = variables[key];
      return value !== undefined ? String(value) : `{{${key}}}`;
    });
  }
}
