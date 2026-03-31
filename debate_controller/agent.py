"""토론 에이전트 클래스

각 에이전트는 독립된 대화 히스토리를 관리하며,
Ollama API를 통해 스트리밍 응답을 생성합니다.

Qwen 3.5 + Ollama는 thinking 토큰을 별도의 'thinking' 필드로 분리합니다.
think=False로 호출하면 thinking을 비활성화하여 num_predict 토큰을
실제 응답에만 사용할 수 있습니다.
"""

import time
import logging

import ollama

from .config import MAX_RETRIES

logger = logging.getLogger(__name__)


class DebateAgent:
    """토론 에이전트. 독립적인 대화 히스토리를 관리합니다."""

    def __init__(self, name: str, role: str, system_prompt: str, model: str):
        """
        Args:
            name: 표시 이름 (예: "찬성측", "반대측")
            role: 역할 코드 ("pro" | "con")
            system_prompt: 이미 주제가 주입된 시스템 프롬프트
            model: Ollama 모델 이름
        """
        self.name = name
        self.role = role
        self.model = model
        self.history: list[dict] = [
            {"role": "system", "content": system_prompt}
        ]

    def add_message(self, role: str, content: str):
        """히스토리에 메시지 추가.

        Args:
            role: 'user' (상대방 발언) 또는 'assistant' (자신의 발언)
            content: 메시지 내용
        """
        self.history.append({"role": role, "content": content})

    def update_system_prompt(self, new_prompt: str):
        """시스템 프롬프트를 업데이트합니다 (주제 변경 시 사용)."""
        self.history[0] = {"role": "system", "content": new_prompt}

    def generate_stream(self, options: dict | None = None, think: bool = False):
        """Ollama 스트리밍 API 호출, chunk generator 반환.

        Args:
            options: Ollama 옵션 (temperature, num_predict 등)
            think: True이면 thinking 모드 활성화 (별도 디버그 로그용)
                   False이면 num_predict 토큰을 응답에만 사용

        Yields:
            각 스트리밍 chunk (dict)
        """
        return ollama.chat(
            model=self.model,
            messages=self.history,
            stream=True,
            options=options or {},
            think=think,
        )

    def generate_with_retry(self, options: dict | None = None, think: bool = False):
        """재시도 로직이 포함된 스트리밍 생성.

        Args:
            options: Ollama 옵션
            think: thinking 모드 활성화 여부

        Returns:
            스트리밍 generator

        Raises:
            마지막 시도까지 실패하면 원본 예외를 raise
        """
        for attempt in range(MAX_RETRIES):
            try:
                return self.generate_stream(options, think=think)
            except Exception as e:
                logger.warning(
                    f"[{self.name}] LLM 호출 실패 (시도 {attempt + 1}/{MAX_RETRIES}): {e}"
                )
                if attempt == MAX_RETRIES - 1:
                    raise
                wait = 2 ** attempt
                logger.info(f"  → {wait}초 후 재시도...")
                time.sleep(wait)

    def get_history_text(self) -> list[dict]:
        """히스토리를 반환합니다 (내보내기용).

        Returns:
            system 프롬프트를 제외한 대화 메시지 리스트
        """
        return self.history[1:]  # system 제외


