"""rich 기반 터미널 UI

찬성측(파란색)과 반대측(빨간색)을 시각적으로 구분하여
토큰 단위 실시간 스트리밍 출력을 제공합니다.
"""

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from .agent import DebateAgent

# ── 스타일 상수 ──────────────────────────────────────────
COLORS = {
    "pro": "blue",
    "con": "red",
}
LABELS = {
    "pro": "👍 찬성측",
    "con": "👎 반대측",
}


class DebateUI:
    """토론 터미널 UI 관리자."""

    def __init__(self):
        self.console = Console()

    def show_header(self, topic: str, model: str):
        """토론 시작 헤더를 출력합니다."""
        self.console.print()
        header = Panel(
            f"[bold bright_white]{topic}[/bold bright_white]",
            title="[bold bright_yellow]🎯 토론 주제[/bold bright_yellow]",
            subtitle=f"[dim]모델: {model}[/dim]",
            border_style="bright_yellow",
            padding=(1, 2),
        )
        self.console.print(header)
        self.console.print()

    def show_turn_header(self, turn: int, max_turns: int):
        """턴 구분선을 출력합니다."""
        self.console.print()
        self.console.print(
            Rule(
                f"[bold]턴 {turn}/{max_turns}[/bold]",
                style="bright_cyan",
            )
        )
        self.console.print()

    def stream_response(self, agent: DebateAgent, options: dict | None = None) -> tuple[str, str]:
        """에이전트 응답을 스트리밍으로 출력하고 완성된 텍스트를 반환합니다.

        Ollama의 thinking 필드를 별도로 수집하고, content만 실시간 표시합니다.
        think=False로 호출하여 num_predict 토큰을 응답에만 사용합니다.

        Args:
            agent: 발화할 에이전트
            options: Ollama 옵션

        Returns:
            (content_text, thinking_text) 튜플
        """
        color = COLORS[agent.role]
        label = LABELS[agent.role]
        content_text = ""
        thinking_text = ""

        with Live(console=self.console, refresh_per_second=8) as live:
            # think=False: thinking 비활성화 → num_predict 토큰 전부 응답에 사용
            stream = agent.generate_with_retry(options, think=False)
            for chunk in stream:
                msg = chunk["message"]

                # thinking 필드 수집 (think=True 일 때만 존재)
                thinking_token = msg.get("thinking", "") or ""
                if thinking_token:
                    thinking_text += thinking_token
                    panel = Panel(
                        Text("💭 사고 중...", style="dim italic"),
                        title=f"[bold {color}]{label}[/bold {color}]",
                        border_style=color,
                        padding=(0, 1),
                    )
                    live.update(panel)
                    continue

                # content 필드 수집
                content_token = msg.get("content", "") or ""
                if content_token:
                    content_text += content_token
                    panel = Panel(
                        Markdown(content_text),
                        title=f"[bold {color}]{label}[/bold {color}]",
                        border_style=color,
                        padding=(0, 1),
                    )
                    live.update(panel)

        # 최종 패널 출력 (Live 종료 후 깔끔하게 재출력)
        if content_text:
            final_panel = Panel(
                Markdown(content_text),
                title=f"[bold {color}]{label}[/bold {color}]",
                border_style=color,
                padding=(0, 1),
            )
            self.console.print(final_panel)

        return content_text, thinking_text

    def show_injection(self, text: str):
        """사용자 개입 메시지를 표시합니다."""
        panel = Panel(
            f"[italic]{text}[/italic]",
            title="[bold bright_green]💬 사용자 개입[/bold bright_green]",
            border_style="bright_green",
            padding=(0, 1),
        )
        self.console.print(panel)

    def show_judge_intervention(self, text: str, turn: int):
        """중재자(Judge) 개입 메시지를 표시합니다."""
        self.console.print()
        self.console.print(
            Rule(
                f"[bold]⚖️  중재자 개입 (턴 {turn} 후)[/bold]",
                style="bright_yellow",
            )
        )
        panel = Panel(
            Markdown(text),
            title="[bold bright_yellow]⚖️ 중재자 판정[/bold bright_yellow]",
            border_style="bright_yellow",
            padding=(0, 1),
        )
        self.console.print(panel)
        self.console.print()

    def show_topic_change(self, old_topic: str, new_topic: str):
        """주제 변경을 표시합니다."""
        self.console.print()
        panel = Panel(
            f"[strikethrough dim]{old_topic}[/strikethrough dim]\n"
            f"[bold bright_white]→ {new_topic}[/bold bright_white]",
            title="[bold bright_magenta]🔄 주제 변경[/bold bright_magenta]",
            border_style="bright_magenta",
            padding=(0, 1),
        )
        self.console.print(panel)
        self.console.print()

    def get_user_command(self) -> tuple[str, str]:
        """사용자 명령을 입력받습니다.

        Returns:
            (command, extra_text) 튜플
            command: "continue" | "inject" | "topic" | "quit"
            extra_text: inject/topic 시 추가 입력 텍스트
        """
        self.console.print()
        self.console.print(
            "[dim]──────────────────────────────────────────────[/dim]"
        )
        self.console.print(
            "[bold green]명령어:[/bold green] "
            "[dim][Enter][/dim] 계속  │  "
            "[dim][i][/dim] 개입  │  "
            "[dim][t][/dim] 주제 변경  │  "
            "[dim][q][/dim] 종료"
        )

        try:
            user_input = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return "quit", ""

        if not user_input:
            return "continue", ""
        elif user_input in ("q", "quit"):
            return "quit", ""
        elif user_input in ("i", "inject"):
            self.console.print(
                "[bold bright_green]개입할 내용을 입력하세요:[/bold bright_green]"
            )
            try:
                text = input(">> ").strip()
            except (EOFError, KeyboardInterrupt):
                return "continue", ""
            return "inject", text
        elif user_input in ("t", "topic"):
            self.console.print(
                "[bold bright_magenta]새 주제(또는 방향 수정)를 입력하세요:[/bold bright_magenta]"
            )
            try:
                text = input(">> ").strip()
            except (EOFError, KeyboardInterrupt):
                return "continue", ""
            return "topic", text
        else:
            self.console.print(f"[dim]알 수 없는 명령: '{user_input}' → 계속 진행합니다.[/dim]")
            return "continue", ""

    def show_ending(self, export_path: str | None = None):
        """토론 종료 메시지를 출력합니다."""
        self.console.print()
        self.console.print(Rule("[bold]토론 종료[/bold]", style="bright_yellow"))
        if export_path:
            self.console.print(
                f"\n[bold green]📄 토론 기록 저장 완료:[/bold green] {export_path}\n"
            )
        self.console.print()
