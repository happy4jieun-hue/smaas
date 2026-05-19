"""
app/utils/enum_utils.py — Enum / str 혼용 안전 처리 유틸
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pydantic 모델 필드에 validate_assignment=True 없이 순수 str이
할당되는 경우에도 DB 저장 시 안전하게 문자열 값을 추출한다.
"""

from enum import Enum


def enum_str(x) -> str:
    """
    Enum이면 x.value, 이미 str이면 그대로 반환.
    None이 오면 빈 문자열 대신 TypeError를 일으키지 않도록 None을 그대로 반환.
    """
    if isinstance(x, Enum):
        return x.value
    return x  # str 또는 None 모두 허용
