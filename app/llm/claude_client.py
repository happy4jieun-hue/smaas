"""
app/llm/claude_client.py — Anthropic Claude API 비동기 래퍼
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[역할]
  모든 에이전트가 Claude를 호출할 때 이 클래스를 사용한다.

[max_tokens 전략]
  에이전트마다 출력 크기가 다르므로 적절한 값을 지정해 대기 시간을 단축한다.
  Analyzer=800 / Planner=1200 / Matcher=2000 / Validator=400

[재시도 전략]
  API 호출 실패(네트워크 오류, rate limit 등) 시 MAX_RETRIES회까지 재시도한다.
  시도마다 RETRY_DELAY_S * attempt 초 대기해 지수적 백오프를 구현한다.
"""

import asyncio
from dataclasses import dataclass
from typing import Any

import anthropic

from app.config import config
from app.llm.json_parser import JsonParser

MAX_RETRIES   = 3
RETRY_DELAY_S = 1.0


@dataclass
class LLMResponse:
    """Claude API 응답을 담는 데이터 클래스."""
    content:       str
    input_tokens:  int
    output_tokens: int


class ClaudeClient:

    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=config.anthropic_api_key)
        self._model  = config.claude_model

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """
        Claude API를 호출하고 텍스트 응답을 반환한다.
        max_tokens: 에이전트별로 적절한 값을 지정해 출력 대기 시간을 단축한다.
        """
        last_err: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                message = await self._client.messages.create(
                    model=self._model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                content = (
                    message.content[0].text
                    if message.content and message.content[0].type == "text"
                    else ""
                )
                print(
                    f"[LLM] {self._model} max_tokens={max_tokens}"
                    f" in={message.usage.input_tokens}"
                    f" out={message.usage.output_tokens}"
                )
                return LLMResponse(
                    content=content,
                    input_tokens=message.usage.input_tokens,
                    output_tokens=message.usage.output_tokens,
                )
            except Exception as e:
                last_err = e
                print(f"[LLM] attempt {attempt}/{MAX_RETRIES} failed: {e}")
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY_S * attempt)

        raise RuntimeError(f"LLM request failed after {MAX_RETRIES} retries") from last_err

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_parse_retries: int = 2,
        max_tokens: int = 1024,
    ) -> Any:
        """
        JSON 응답을 기대하는 LLM 호출.
        파싱 실패 시 교정 지시를 추가해 최대 max_parse_retries회 재요청한다.
        """
        current_prompt = user_prompt
        last_err: Exception | None = None

        for attempt in range(max_parse_retries + 1):
            resp = await self.complete(system_prompt, current_prompt, max_tokens=max_tokens)

            parsed = JsonParser.try_extract(resp.content)
            if parsed is not None:
                return parsed

            from app.utils.safe_log import safe_str
            safe_preview = safe_str(resp.content[:200])
            last_err = ValueError(
                f"[LLM] JSON parse failed (attempt {attempt + 1}/{max_parse_retries + 1})\n"
                f"response first 200: {safe_preview}"
            )
            print(str(last_err))

            if attempt < max_parse_retries:
                current_prompt = (
                    user_prompt
                    + "\n\n[재요청] 이전 응답이 JSON으로 파싱되지 않았습니다. "
                    "마크다운 코드블럭(```) 없이 순수 JSON 객체만 출력하세요. "
                    "첫 글자는 반드시 { 이어야 합니다."
                )

        raise ValueError(
            f"JSON 파싱 최대 재시도({max_parse_retries}회) 초과"
        ) from last_err
