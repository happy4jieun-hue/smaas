"""
app/llm/json_parser.py — LLM 출력에서 JSON 안전 추출
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[추출 전략 — 순서대로 시도]
  1. 코드펜스 전처리 후 trim → json.loads
  2. ```json ... ``` 코드 블럭 내부 추출
  3. 모든 코드 펜스 제거 후 파싱
  4. 첫 번째 '{' 에서 괄호 균형(balanced brace) 기반 추출
  5. 첫 번째 '[' 에서 동일 방식 추출

[추가된 전처리 — strip_fences()]
  LLM이 ``` 없이 `json` 만 붙이거나 닫는 펜스를 생략하는 경우를 처리한다.
  '{' 이전의 모든 텍스트를 제거하는 브루트포스 전략도 포함한다.
"""

import json
import re
from typing import Any, Optional


class JsonParser:

    @staticmethod
    def extract(raw: str) -> Any:
        """
        LLM 출력 문자열에서 JSON 객체/배열을 추출해 Python 객체로 반환한다.
        모든 전략이 실패하면 ValueError를 발생시킨다.
        """
        for candidate in JsonParser._build_candidates(raw):
            try:
                return json.loads(candidate)
            except (json.JSONDecodeError, ValueError):
                continue

        raise ValueError(
            f"[JsonParser] JSON extract failed - length: {len(raw)}\n"
            f"first 400 chars:\n{raw[:400]}"
        )

    @staticmethod
    def try_extract(raw: str) -> Optional[Any]:
        """파싱 실패 시 예외 대신 None을 반환하는 safe wrapper."""
        try:
            return JsonParser.extract(raw)
        except ValueError:
            return None

    # ── private ────────────────────────────────────────────────

    @staticmethod
    def _build_candidates(raw: str) -> list[str]:
        results: list[str] = []

        def add(s: str) -> None:
            t = s.strip()
            if t and t not in results:
                results.append(t)

        trimmed = raw.strip()

        # 전략 0: 코드펜스 전처리 후 바로 시도 (가장 흔한 케이스)
        preprocessed = JsonParser._strip_fences(trimmed)
        add(preprocessed)

        # 전략 1: 원본 그대로 시도
        add(trimmed)

        # 전략 2: ```json ... ``` 코드 블럭 내부 추출 (닫는 펜스가 있는 경우)
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", trimmed, re.IGNORECASE)
        if fence_match:
            add(fence_match.group(1))

        # 전략 3: 모든 코드 펜스 제거 (닫는 펜스 없이 열리는 펜스만 있는 경우)
        stripped = re.sub(r"```(?:json)?", "", trimmed, flags=re.IGNORECASE)
        stripped = stripped.replace("```", "").strip()
        add(stripped)

        # 전략 4: 첫 번째 '{' 부터 균형 잡힌 객체 추출
        obj_start = trimmed.find("{")
        if obj_start != -1:
            extracted = JsonParser._extract_balanced(trimmed, obj_start, "{", "}")
            if extracted:
                add(extracted)

        # 전략 5: 첫 번째 '[' 부터 균형 잡힌 배열 추출
        arr_start = trimmed.find("[")
        if arr_start != -1:
            extracted = JsonParser._extract_balanced(trimmed, arr_start, "[", "]")
            if extracted:
                add(extracted)

        return results

    @staticmethod
    def _strip_fences(text: str) -> str:
        """
        코드 펜스와 앞뒤 설명 텍스트를 제거하는 전처리.

        처리 순서:
        1. ```json ... ``` 또는 ``` ... ``` 블럭 → 내부만 추출
        2. 위 매칭 실패 시: ``` 기호 전체 제거
        3. 첫 번째 { 또는 [ 이전의 모든 텍스트 제거 (브루트포스)
        """
        # 1단계: 코드 펜스 블럭이 있으면 내부만 추출
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if fence_match:
            return fence_match.group(1).strip()

        # 2단계: 열리는 펜스만 있으면 제거
        text = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE).replace("```", "")

        # 3단계: { 또는 [ 이전 텍스트 제거
        brace_pos   = text.find("{")
        bracket_pos = text.find("[")

        starts = [p for p in (brace_pos, bracket_pos) if p != -1]
        if starts:
            text = text[min(starts):]

        return text.strip()

    @staticmethod
    def _extract_balanced(
        text: str, start: int, open_ch: str, close_ch: str
    ) -> Optional[str]:
        """
        text[start]부터 괄호 depth를 추적해 균형 잡힌 JSON 덩어리를 추출한다.
        문자열 내부의 괄호는 in_string 플래그로 무시한다.
        """
        depth     = 0
        in_string = False
        escape    = False

        for i in range(start, len(text)):
            ch = text[i]

            if escape:
                escape = False
                continue
            if ch == "\\" and in_string:
                escape = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if in_string:
                continue

            if ch == open_ch:
                depth += 1
            elif ch == close_ch:
                depth -= 1
                if depth == 0:
                    return text[start: i + 1]

        return None
