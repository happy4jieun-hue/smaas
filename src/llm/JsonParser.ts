/**
 * llm/JsonParser.ts
 * LLM 출력 텍스트에서 JSON을 안전하게 추출하는 유틸리티.
 *
 * Claude는 지시에도 불구하고 아래와 같은 형태로 응답할 수 있다:
 *   - ```json { ... } ```  (코드 블럭 포함)
 *   - "Here is the result:\n{ ... }"  (prefix 텍스트)
 *   - "{ ... }\n\nNote: ..."  (suffix 텍스트)
 *   - 중첩된 코드 블럭, 공백, BOM 문자 등
 *
 * 추출 전략 (순서대로 시도):
 *   1. trim 후 직접 JSON.parse
 *   2. 코드 블럭 내부 추출 (```json ... ```)
 *   3. 모든 코드 펜스 제거 후 파싱
 *   4. 첫 번째 `{` 에서 괄호 균형(balanced) 기반으로 추출
 *   5. 첫 번째 `[` 에서 동일 방식 추출
 */
export class JsonParser {
  /**
   * LLM raw 텍스트에서 JSON을 추출해 T 타입으로 반환한다.
   * 모든 전략이 실패하면 상세 에러를 throw한다.
   */
  static extract<T>(raw: string): T {
    for (const candidate of JsonParser.buildCandidates(raw)) {
      try {
        return JSON.parse(candidate) as T;
      } catch {
        // 다음 후보 시도
      }
    }

    throw new Error(
      `[JsonParser] JSON 추출 실패\n` +
        `출력 길이: ${raw.length}자\n` +
        `앞 300자:\n${raw.slice(0, 300)}`
    );
  }

  // ── private ────────────────────────────────────────────────

  private static buildCandidates(raw: string): string[] {
    const results: string[] = [];

    const add = (s: string) => {
      const t = s.trim();
      if (t) results.push(t);
    };

    // 1. 원본 trim
    const trimmed = raw.trim();
    add(trimmed);

    // 2. ```json ... ``` 또는 ``` ... ``` 내부 추출
    const fenceMatch = trimmed.match(/```(?:json)?\s*([\s\S]*?)\s*```/i);
    if (fenceMatch) add(fenceMatch[1]);

    // 3. 모든 코드 펜스 제거
    const stripped = trimmed
      .replace(/```(?:json)?/gi, "")
      .replace(/```/g, "");
    add(stripped);

    // 4. 첫 번째 `{` 에서 balanced 추출
    const objStart = trimmed.indexOf("{");
    if (objStart !== -1) {
      const extracted = JsonParser.extractBalanced(trimmed, objStart, "{", "}");
      if (extracted) add(extracted);
    }

    // 5. 첫 번째 `[` 에서 balanced 추출
    const arrStart = trimmed.indexOf("[");
    if (arrStart !== -1) {
      const extracted = JsonParser.extractBalanced(trimmed, arrStart, "[", "]");
      if (extracted) add(extracted);
    }

    // 중복 제거
    return [...new Set(results)];
  }

  /**
   * start 위치에서 시작하는 괄호 쌍을 문자열/이스케이프를 고려해 균형을 맞춰 추출한다.
   * 중첩 객체/배열, 문자열 내 괄호, 이스케이프 시퀀스를 모두 올바르게 처리한다.
   */
  private static extractBalanced(
    text: string,
    start: number,
    open: string,
    close: string
  ): string | null {
    let depth = 0;
    let inString = false;
    let escape = false;

    for (let i = start; i < text.length; i++) {
      const ch = text[i];

      if (escape) {
        escape = false;
        continue;
      }
      if (ch === "\\" && inString) {
        escape = true;
        continue;
      }
      if (ch === '"') {
        inString = !inString;
        continue;
      }
      if (inString) continue;

      if (ch === open) {
        depth++;
      } else if (ch === close) {
        depth--;
        if (depth === 0) return text.slice(start, i + 1);
      }
    }

    return null; // 닫는 괄호를 찾지 못함
  }
}
