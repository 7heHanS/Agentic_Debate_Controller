"""토론 오케스트레이터

토론의 전체 흐름을 제어합니다:
1. 에이전트 초기화 (찬성/반대 페르소나)
2. 교차 주입 기반 핑퐁 루프
3. 주기적 중재자(Judge) 개입
4. 사용자 명령 처리 (계속/개입/주제변경/종료)
5. 컨텍스트 윈도우 관리
6. 토론 내역 내보내기
"""

import logging

import ollama

from .agent import DebateAgent
from .config import (
    CONTEXT_WINDOW_SIZE,
    JUDGE_INTERVAL,
    MAX_RESPONSE_TOKENS,
    MAX_TURNS,
    MODEL_NAME,
    SLIDING_WINDOW_KEEP,
    TEMPERATURE,
    USE_SUMMARY,
)
from .context_manager import ContextManager
from .exporter import export_debate, export_debug_log
from .prompts import (
    CON_SYSTEM_PROMPT,
    JUDGE_EVALUATION_PROMPT,
    JUDGE_SYSTEM_PROMPT,
    OPENING_CON_PROMPT,
    OPENING_PRO_PROMPT,
    PRO_SYSTEM_PROMPT,
)
from .ui import DebateUI

logger = logging.getLogger(__name__)


class DebateOrchestrator:
    """토론 세션을 관리하는 오케스트레이터."""

    def __init__(
        self,
        topic: str,
        model: str = MODEL_NAME,
        max_turns: int = MAX_TURNS,
        temperature: float = TEMPERATURE,
    ):
        """
        Args:
            topic: 토론 주제
            model: Ollama 모델 이름
            max_turns: 최대 턴 수
            temperature: LLM 온도
        """
        self.topic = topic
        self.model = model
        self.max_turns = max_turns
        self.temperature = temperature
        self.turn = 0

        # 에이전트 초기화
        self.agent_pro = DebateAgent(
            name="찬성측",
            role="pro",
            system_prompt=PRO_SYSTEM_PROMPT.format(topic=topic),
            model=model,
        )
        self.agent_con = DebateAgent(
            name="반대측",
            role="con",
            system_prompt=CON_SYSTEM_PROMPT.format(topic=topic),
            model=model,
        )

        # 모듈 초기화
        self.ui = DebateUI()
        self.context_mgr = ContextManager(
            max_messages=SLIDING_WINDOW_KEEP,
            model=model,
            use_summary=USE_SUMMARY,
        )

        # 기록 저장
        self.turn_records: list[dict] = []
        self.thinking_log: list[dict] = []

    def run(self):
        """토론 메인 루프를 실행합니다."""
        self.ui.show_header(self.topic, self.model)

        # LLM 옵션
        llm_options = {
            "temperature": self.temperature,
            "num_predict": MAX_RESPONSE_TOKENS,
            "num_ctx": CONTEXT_WINDOW_SIZE,
        }

        while self.turn < self.max_turns:
            self.turn += 1
            self.ui.show_turn_header(self.turn, self.max_turns)

            turn_record = {
                "turn": self.turn,
                "pro": "",
                "con": "",
                "injection": None,
                "judge": None,
            }

            # ── 1) 찬성측 발언 ──────────────────────────────────
            if self.turn == 1:
                # 첫 턴: 오프닝 프롬프트 주입
                self.agent_pro.add_message("user", OPENING_PRO_PROMPT)
            # 이후 턴에서는 이미 상대 발언이 user로 주입되어 있음

            pro_response, pro_thinking = self.ui.stream_response(
                self.agent_pro, llm_options
            )

            # 찬성측 히스토리에 자신의 발언 기록
            self.agent_pro.add_message("assistant", pro_response)
            turn_record["pro"] = pro_response

            # thinking 로그
            if pro_thinking:
                self.thinking_log.append({
                    "turn": self.turn,
                    "agent": "pro",
                    "thinking": pro_thinking,
                })

            # ── 2) 반대측에 찬성 발언 교차 주입 ──────────────────
            if self.turn == 1:
                # 첫 턴: 찬성측 발언 + 반박 요청
                inject_text = (
                    f"{pro_response}\n\n"
                    f"위 찬성 입장에 대해 반박하며, 당신의 반대 입장을 개진해 주세요."
                )
                self.agent_con.add_message("user", inject_text)
            else:
                self.agent_con.add_message("user", pro_response)

            # ── 3) 반대측 발언 ──────────────────────────────────
            con_response, con_thinking = self.ui.stream_response(
                self.agent_con, llm_options
            )

            # 반대측 히스토리에 자신의 발언 기록
            self.agent_con.add_message("assistant", con_response)
            turn_record["con"] = con_response

            # thinking 로그
            if con_thinking:
                self.thinking_log.append({
                    "turn": self.turn,
                    "agent": "con",
                    "thinking": con_thinking,
                })

            # ── 4) 찬성측에 반대 발언 교차 주입 ──────────────────
            self.agent_pro.add_message("user", con_response)

            # ── 5) 중재자(Judge) 개입 ───────────────────────────
            if self.turn % JUDGE_INTERVAL == 0 and self.turn < self.max_turns:
                judge_feedback = self._call_judge(llm_options)
                if judge_feedback:
                    turn_record["judge"] = judge_feedback
                    self.ui.show_judge_intervention(judge_feedback, self.turn)

                    # 양측 에이전트에 Judge 지침 주입
                    judge_directive = f"[중재자 지침] {judge_feedback}"
                    self.agent_pro.add_message("user", judge_directive)
                    self.agent_con.add_message("user", judge_directive)

            # ── 6) 컨텍스트 윈도우 관리 ─────────────────────────
            self.context_mgr.check_and_trim(self.agent_pro)
            self.context_mgr.check_and_trim(self.agent_con)

            # ── 7) 턴 기록 저장 ─────────────────────────────────
            self.turn_records.append(turn_record)

            # ── 8) 마지막 턴이면 자동 종료 ──────────────────────
            if self.turn >= self.max_turns:
                self.ui.console.print(
                    "\n[bold bright_yellow]⚠️  최대 턴 수에 도달했습니다.[/bold bright_yellow]"
                )
                break

            # ── 9) 사용자 명령 대기 ─────────────────────────────
            command, extra = self.ui.get_user_command()

            if command == "quit":
                break

            elif command == "inject":
                if extra:
                    self.ui.show_injection(extra)
                    # 다음 화자(찬성측)의 히스토리에 사용자 개입 추가
                    self.agent_pro.add_message(
                        "user",
                        f"[사용자 개입] {extra}"
                    )
                    turn_record["injection"] = extra

            elif command == "topic":
                if extra:
                    old_topic = self.topic
                    self.topic = extra
                    self.ui.show_topic_change(old_topic, extra)

                    # 양측 시스템 프롬프트 업데이트
                    self.agent_pro.update_system_prompt(
                        PRO_SYSTEM_PROMPT.format(topic=extra)
                    )
                    self.agent_con.update_system_prompt(
                        CON_SYSTEM_PROMPT.format(topic=extra)
                    )

            # "continue"면 그냥 다음 턴으로

        # ── 토론 종료: 내보내기 ─────────────────────────────────
        self._finish()

    def _call_judge(self, llm_options: dict) -> str | None:
        """중재자(Judge) 에이전트를 호출하여 토론 방향성 지침을 생성합니다.

        최근 2턴의 토론 내용만 전달하여 Judge 호출을 가볍게 유지합니다.

        Args:
            llm_options: LLM 호출 옵션

        Returns:
            Judge 피드백 텍스트, 실패 시 None
        """
        # 최근 2턴의 토론 내용 수집
        recent_turns = self.turn_records[-2:] if len(self.turn_records) >= 2 else self.turn_records
        if not recent_turns:
            return None

        recent_debate = ""
        for tr in recent_turns:
            recent_debate += f"[턴 {tr['turn']}]\n"
            recent_debate += f"찬성측: {tr['pro']}\n\n"
            recent_debate += f"반대측: {tr['con']}\n\n"

        try:
            logger.info(f"[Judge] 중재자 호출 (턴 {self.turn} 후)")
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": JUDGE_EVALUATION_PROMPT.format(
                            topic=self.topic,
                            recent_debate=recent_debate,
                        ),
                    },
                ],
                options={
                    "temperature": 0.3,  # Judge는 객관적이어야 하므로 낮은 온도
                    "num_predict": MAX_RESPONSE_TOKENS,
                    "num_ctx": CONTEXT_WINDOW_SIZE,
                },
                think=False,
            )
            feedback = response["message"].get("content", "").strip()
            logger.info(f"[Judge] 피드백 생성 완료 ({len(feedback)}자)")
            return feedback if feedback else None
        except Exception as e:
            logger.warning(f"[Judge] 중재자 호출 실패: {e}")
            return None

    def _finish(self):
        """토론을 종료하고 결과를 내보냅니다."""
        # 마크다운 내보내기
        export_path = export_debate(
            topic=self.topic,
            model=self.model,
            turns=self.turn_records,
        )

        # thinking 디버그 로그 내보내기
        debug_path = export_debug_log(self.thinking_log)
        if debug_path:
            logger.info(f"Thinking 디버그 로그 저장: {debug_path}")

        self.ui.show_ending(export_path)
