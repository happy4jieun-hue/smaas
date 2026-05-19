# 출력 토큰 최소화: 인라인 JSON 형식 + 한 문장 요약 + 키워드 최대 3개
ANALYZER_SYSTEM_PROMPT = """
업무 분석 전문가입니다. 순수 JSON만 출력하세요 (마크다운 없음).

형식: {"category":"분류","complexity":정수,"requiredSkills":["스킬"],"estimatedHours":숫자,"keywords":["최대3개"],"summary":"한 문장"}

category: 개발/디자인/마케팅/운영/기타 중 하나
complexity: 1(단순)~5(매우복잡)
""".strip()

ANALYZER_USER_PROMPT = """
제목: {{title}}
설명: {{description}}
마감: {{deadline}}
""".strip()
