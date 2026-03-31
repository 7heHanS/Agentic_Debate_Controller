# Agentic Debate Controller — 구현 완료 Walkthrough

## 프로젝트 개요

단일 LLM(**Qwen 3.5 9B**, Ollama 로컬 서빙)을 활용하여 찬성/반대 페르소나의 두 에이전트가 자율 토론하는 터미널 애플리케이션을 구현했습니다.

---

## 파일 구조

```
Agentic_Debate_Controller/
├── .gitignore
├── .venv/                           # Python 가상환경
├── requirements.txt                 # ollama, rich
├── debate_controller/
│   ├── __init__.py                  # 패키지 초기화
│   ├── __main__.py                  # python -m debate_controller 지원
│   ├── main.py                      # CLI 진입점 (argparse)
│   ├── config.py                    # 전역 설정 (VRAM 최적화)
│   ├── prompts.py                   # 시스템 프롬프트 템플릿
│   ├── agent.py                     # DebateAgent 클래스
│   ├── orchestrator.py              # 토론 오케스트레이터
│   ├── ui.py                        # rich 기반 터미널 UI
│   ├── context_manager.py           # 슬라이딩 윈도우 컨텍스트 관리
│   └── exporter.py                  # 마크다운 내보내기
└── exports/                         # 토론 기록 저장소
```

---

## 핵심 설계

### 교차 주입 (Cross-Injection)
- 찬성측 발언 → `assistant` role로 자기 히스토리에 기록, `user` role로 반대측 히스토리에 주입
- 반대측 발언 → 동일 방식으로 역방향 주입

### Ollama Thinking 모드 처리
> [!IMPORTANT]
> **발견된 핵심 이슈**: Qwen 3.5 + Ollama는 `<think>` 태그가 아닌 **별도의 `thinking` 필드**로 사고 과정을 분리합니다. `think=True`로 호출하면 thinking 토큰이 `num_predict` 예산을 소비하여 **실제 content가 빈 문자열**로 반환됩니다.
>
> **해결**: `think=False`로 호출하여 `num_predict=256` 토큰 전부를 실제 응답에 사용하도록 변경했습니다.

### VRAM 최적화 (11GB 환경)
- `CONTEXT_WINDOW_SIZE = 4096` (4-bit 양자화 기준 안정적)
- `MAX_RESPONSE_TOKENS = 256`
- 기본 **단순 잘라내기(Truncation)** 방식의 슬라이딩 윈도우 (LLM 요약은 옵션)

---

## 변경된 파일

| 파일 | 상태 | 설명 |
|------|------|------|
| [requirements.txt](requirements.txt) | NEW | ollama, rich 의존성 |
| [config.py](debate_controller/config.py) | NEW | VRAM 최적화된 전역 설정 |
| [prompts.py](debate_controller/prompts.py) | NEW | 시스템 프롬프트 템플릿 |
| [agent.py](debate_controller/agent.py) | NEW | Ollama native thinking 필드 지원 |
| [ui.py](debate_controller/ui.py) | NEW | 색상 구분 스트리밍 패널 |
| [orchestrator.py](debate_controller/orchestrator.py) | NEW | 교차 주입 토론 루프 |
| [context_manager.py](debate_controller/context_manager.py) | NEW | 슬라이딩 윈도우 + 요약 옵션 |
| [exporter.py](debate_controller/exporter.py) | NEW | 마크다운 + 디버그 로그 내보내기 |
| [main.py](debate_controller/main.py) | NEW | CLI 진입점 |

---

## 테스트 결과

### 통합 테스트 (2턴)
- **주제**: "AI는 인간의 일자리를 대체해야 하는가?"
- **결과**: ✅ 정상 종료
- **확인 사항**:
  - 찬성측/반대측 패널 색상 구분 표시 정상
  - 토큰 단위 실시간 스트리밍 정상
  - 교차 주입 정상 (반대측이 찬성측 논점을 반박)
  - 마크다운 내보내기 정상 (전체 토론 내용 포함)
  - 사용자 명령 프롬프트 정상 (Enter로 다음 턴 진행)

---

## 사용법

```bash
# 가상환경 활성화
source .venv/bin/activate

# 주제를 인자로 지정
python -m debate_controller "AI는 인간의 일자리를 대체해야 하는가?"

# 옵션 사용
python -m debate_controller -n 5 -t 0.8 "원자력 발전소를 확대해야 하는가?"

# 대화형으로 주제 입력
python -m debate_controller

# 디버그 로깅 활성화
python -m debate_controller -v "기본소득 도입 찬반"
```

### 토론 중 사용자 명령
| 키 | 동작 |
|-----|------|
| `Enter` | 다음 턴으로 진행 |
| `i` | 다음 화자에게 논리 개입 |
| `t` | 토론 주제 방향 수정 |
| `q` | 토론 종료 + 마크다운 저장 |
