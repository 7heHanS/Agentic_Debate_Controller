"""Agentic Debate Controller - CLI 진입점

사용법:
    # 가상환경 활성화 후
    python -m debate_controller "AI는 인간의 일자리를 대체해야 하는가?"
    python -m debate_controller --max-turns 5 "원자력 발전소를 확대해야 하는가?"
    python -m debate_controller  # 대화형으로 주제 입력
"""

import argparse
import logging
import sys

from .config import MAX_TURNS, MODEL_NAME, TEMPERATURE
from .orchestrator import DebateOrchestrator


def parse_args() -> argparse.Namespace:
    """CLI 인자를 파싱합니다."""
    parser = argparse.ArgumentParser(
        prog="debate_controller",
        description="🎯 단일 LLM 다중 페르소나 토론 시스템",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "예시:\n"
            '  python -m debate_controller "AI는 인간의 일자리를 대체해야 하는가?"\n'
            '  python -m debate_controller -n 5 -t 0.8 "원자력 발전소를 확대해야 하는가?"'
        ),
    )

    parser.add_argument(
        "topic",
        nargs="?",
        default=None,
        help="토론 주제 (미입력 시 대화형으로 입력)",
    )
    parser.add_argument(
        "-m", "--model",
        default=MODEL_NAME,
        help=f"사용할 Ollama 모델 (기본: {MODEL_NAME})",
    )
    parser.add_argument(
        "-n", "--max-turns",
        type=int,
        default=MAX_TURNS,
        help=f"최대 턴 수 (기본: {MAX_TURNS})",
    )
    parser.add_argument(
        "-t", "--temperature",
        type=float,
        default=TEMPERATURE,
        help=f"LLM 온도 (기본: {TEMPERATURE})",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="디버그 로깅 활성화",
    )

    return parser.parse_args()


def main():
    """메인 함수."""
    args = parse_args()

    # 로깅 설정
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="[%(levelname)s] %(name)s: %(message)s",
    )

    # 토론 주제 결정
    topic = args.topic
    if not topic:
        try:
            topic = input("🎯 토론 주제를 입력하세요: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n종료합니다.")
            sys.exit(0)

    if not topic:
        print("❌ 토론 주제가 지정되지 않았습니다.")
        sys.exit(1)

    # 오케스트레이터 실행
    orchestrator = DebateOrchestrator(
        topic=topic,
        model=args.model,
        max_turns=args.max_turns,
        temperature=args.temperature,
    )

    try:
        orchestrator.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
        orchestrator._finish()
    except Exception as e:
        logging.error(f"예기치 않은 오류: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
