"""마크다운 내보내기

토론 내역을 구조화된 마크다운 파일로 저장합니다.
"""

import os
from datetime import datetime
from pathlib import Path


def export_debate(
    topic: str,
    model: str,
    turns: list[dict],
    export_dir: str = "exports",
) -> str:
    """토론 내역을 마크다운 파일로 내보냅니다.

    Args:
        topic: 토론 주제
        model: 사용된 모델 이름
        turns: 턴 기록 리스트. 각 항목:
            {
                "turn": int,
                "pro": str,       # 찬성측 발언
                "con": str,       # 반대측 발언
                "injection": str | None,  # 사용자 개입 (있는 경우)
            }
        export_dir: 저장 디렉토리 경로

    Returns:
        저장된 파일의 절대 경로
    """
    # 디렉토리 생성
    base_dir = Path(__file__).parent.parent / export_dir
    base_dir.mkdir(parents=True, exist_ok=True)

    # 파일명 생성
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"debate_{timestamp}.md"
    filepath = base_dir / filename

    # 마크다운 생성
    lines = [
        f"# 토론 기록: {topic}",
        "",
        f"- **날짜**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **모델**: {model}",
        f"- **총 턴 수**: {len(turns)}",
        "",
        "---",
        "",
    ]

    for turn_data in turns:
        turn_num = turn_data["turn"]
        lines.append(f"## 턴 {turn_num}")
        lines.append("")

        # 찬성측 발언
        lines.append("### 👍 찬성측")
        lines.append("")
        lines.append(turn_data.get("pro", "(발언 없음)"))
        lines.append("")

        # 사용자 개입 (찬성 발언 후, 반대 발언 전에 있었던 경우)
        injection = turn_data.get("injection")
        if injection:
            lines.append("### 💬 사용자 개입")
            lines.append("")
            lines.append(f"> {injection}")
            lines.append("")

        # 반대측 발언
        lines.append("### 👎 반대측")
        lines.append("")
        lines.append(turn_data.get("con", "(발언 없음)"))
        lines.append("")

        # 중재자(Judge) 개입
        judge = turn_data.get("judge")
        if judge:
            lines.append("### ⚖️ 중재자 판정")
            lines.append("")
            lines.append(f"> {judge}")
            lines.append("")

        lines.append("---")
        lines.append("")

    # 파일 쓰기
    filepath.write_text("\n".join(lines), encoding="utf-8")

    return str(filepath.resolve())


def export_debug_log(
    thinking_log: list[dict],
    export_dir: str = "exports",
) -> str | None:
    """thinking 토큰 디버그 로그를 파일로 내보냅니다.

    Args:
        thinking_log: thinking 기록 리스트. 각 항목:
            {
                "turn": int,
                "agent": str,   # "pro" | "con"
                "thinking": str,
            }
        export_dir: 저장 디렉토리 경로

    Returns:
        저장된 파일의 절대 경로. 기록이 없으면 None.
    """
    # thinking 내용이 있는 항목만 필터
    has_thinking = [entry for entry in thinking_log if entry.get("thinking")]
    if not has_thinking:
        return None

    base_dir = Path(__file__).parent.parent / export_dir
    base_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"debug_{timestamp}.log"
    filepath = base_dir / filename

    lines = [
        f"=== Thinking Token Debug Log ===",
        f"Timestamp: {datetime.now().isoformat()}",
        "",
    ]

    for entry in has_thinking:
        lines.append(f"--- Turn {entry['turn']} / {entry['agent'].upper()} ---")
        lines.append(entry["thinking"])
        lines.append("")

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return str(filepath.resolve())
