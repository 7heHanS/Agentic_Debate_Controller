"""컨텍스트 윈도우 관리

엄격한 슬라이딩 윈도우(기본) 또는 LLM 요약(옵션)으로
히스토리가 컨텍스트 윈도우를 초과하지 않도록 관리합니다.
"""

import logging

import ollama

from .config import SLIDING_WINDOW_KEEP, USE_SUMMARY, MODEL_NAME
from .prompts import SUMMARY_PROMPT

logger = logging.getLogger(__name__)


class ContextManager:
    """대화 히스토리의 컨텍스트 윈도우를 관리합니다."""

    def __init__(
        self,
        max_messages: int = SLIDING_WINDOW_KEEP,
        model: str = MODEL_NAME,
        use_summary: bool = USE_SUMMARY,
    ):
        """
        Args:
            max_messages: 유지할 최근 메시지 수
            model: 요약에 사용할 모델 (USE_SUMMARY=True 시)
            use_summary: True이면 잘라내기 전 요약, False면 단순 잘라내기
        """
        self.max_messages = max_messages
        self.model = model
        self.use_summary = use_summary

    def check_and_trim(self, agent) -> bool:
        """히스토리가 임계값을 초과하면 트리밍합니다.

        Args:
            agent: DebateAgent 인스턴스

        Returns:
            트리밍이 수행되었으면 True
        """
        # system 메시지를 제외한 대화 메시지
        conversation = agent.history[1:]

        if len(conversation) <= self.max_messages:
            return False

        trimmed_count = len(conversation) - self.max_messages
        logger.info(
            f"[{agent.name}] 컨텍스트 트리밍: {len(conversation)}개 → "
            f"{self.max_messages}개 (제거: {trimmed_count}개)"
        )

        if self.use_summary:
            # 요약 모드: 오래된 메시지를 LLM으로 요약 후 압축
            old_messages = conversation[:-self.max_messages]
            summary = self._summarize(old_messages)
            agent.history = (
                [agent.history[0]]  # system prompt 유지
                + [{"role": "user", "content": f"[이전 토론 요약]\n{summary}"}]
                + conversation[-self.max_messages:]
            )
            logger.info(f"[{agent.name}] 요약 생성 완료 (요약 길이: {len(summary)}자)")
        else:
            # 기본 모드: 단순 잘라내기 (가장 빠르고 VRAM 부담 없음)
            agent.history = (
                [agent.history[0]]  # system prompt 유지
                + conversation[-self.max_messages:]
            )

        return True

    def _summarize(self, messages: list[dict]) -> str:
        """메시지 리스트를 LLM으로 요약합니다 (USE_SUMMARY=True 시에만 호출).

        Args:
            messages: 요약할 메시지 리스트

        Returns:
            요약 텍스트
        """
        conversation_text = "\n".join(
            f"{'찬성측' if m['role'] == 'assistant' else '반대측'}: {m['content']}"
            for m in messages
        )
        try:
            response = ollama.chat(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": SUMMARY_PROMPT.format(conversation=conversation_text),
                }],
                options={"temperature": 0.0},  # 요약은 deterministic하게
            )
            return response["message"]["content"]
        except Exception as e:
            logger.error(f"요약 생성 실패: {e}. 요약 없이 잘라내기로 대체합니다.")
            return "(요약 생성 실패)"
