# Agentic Debate Controller — 구현 태스크

## Phase 1: 기본 환경 및 페르소나 설정
- [x] `requirements.txt` 생성 및 의존성 설치
- [x] `debate_controller/__init__.py` 생성
- [x] `debate_controller/config.py` — 전역 설정
- [x] `debate_controller/prompts.py` — 시스템 프롬프트 템플릿

## Phase 2: 코어 토론 루프
- [x] `debate_controller/agent.py` — DebateAgent 클래스 (Ollama native thinking 필드 처리)
- [x] `debate_controller/ui.py` — rich 기반 터미널 UI (스트리밍, 색상)
- [x] `debate_controller/orchestrator.py` — 토론 오케스트레이터 (교차 주입 루프)

## Phase 3: 사용자 제어 인터페이스
- [x] orchestrator.py에 사용자 명령 처리 (Enter/i/t/q) 통합
- [x] `debate_controller/exporter.py` — 마크다운 내보내기

## Phase 4: 컨텍스트 및 메모리 최적화
- [x] `debate_controller/context_manager.py` — 슬라이딩 윈도우 + 요약 옵션
- [x] agent.py에 재시도(retry) 로직 추가

## Phase 5: 진입점 및 통합
- [x] `debate_controller/main.py` — CLI 진입점
- [x] `debate_controller/__main__.py` — 모듈 실행 지원
- [x] 문서화 진행 (`docs/` 저장)

## 심화 기능 구현
- [x] `prompts.py`에 구조적 CoT (Chain-of-Thought) 템플릿 추가
- [x] 주기적인 중재자(Judge) 개입 로직 구현 (`orchestrator.py`)
- [x] UI에 중재자 판정 결과 출력 기능 추가 (`ui.py`)
- [x] 내보내기 마크다운에 중재자 턴 기록 추가 (`exporter.py`)
- [x] 통합 테스트 (5턴, 주기적 Judge 포함) ✅ 성공
