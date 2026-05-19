# Claude Code MCP Workflow Guide

이 문서는 Claude Code에서 Slack MCP와 Notion MCP를 활용해 에이전트 작업 결과를 정리하고 공유하는 방법을 설명합니다.

## 목적

Claude Code의 역할별 에이전트가 생성한 결과를 채팅에만 남기지 않고, Notion에는 기록으로 정리하고 Slack에는 공유 메시지로 전달하기 위한 운영 흐름을 정의합니다.

이 방식은 Claude Code를 단순 코드 보조 도구로 쓰는 것이 아니라, 작업 결과를 문서화하고 팀에 공유하는 협업 흐름으로 확장하기 위한 것입니다.

## 기본 흐름

```text
1. 사용자가 Claude Code에 작업 지시
2. 역할별 에이전트가 작업 수행
3. Claude가 결과를 요약
4. Notion MCP로 결과를 지정 페이지에 정리
5. Slack MCP로 공유 메시지 초안 작성
6. 사용자가 승인하면 Slack에 전송