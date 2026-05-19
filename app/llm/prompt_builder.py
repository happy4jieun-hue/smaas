"""
app/llm/prompt_builder.py — 프롬프트 템플릿 변수 치환
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[역할]
  프롬프트 파일(llm/prompts/*.py)에 정의된 템플릿 문자열에서
  {{변수명}} 형식의 플레이스홀더를 실제 값으로 치환한다.

[사용 예]
  template = "업무: {{title}}. 마감: {{deadline}}"
  result = PromptBuilder.build(template, {"title": "개발", "deadline": "없음"})
  # → "업무: 개발. 마감: 없음"

[설계 이유]
  템플릿과 로직을 분리하기 위해 프롬프트 문자열을 별도 파일에 관리한다.
  각 에이전트는 실행 시점의 context 값을 이 클래스를 통해 프롬프트에 주입한다.
"""


class PromptBuilder:

    @staticmethod
    def build(template: str, variables: dict) -> str:
        """
        template 내의 {{key}} 플레이스홀더를 variables[key]로 치환한다.
        변수가 없는 플레이스홀더는 그대로 남는다 (에러 없음).
        모든 값은 str()로 변환되어 숫자, 리스트 등도 처리 가능하다.
        """
        result = template
        for key, value in variables.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))
        return result
