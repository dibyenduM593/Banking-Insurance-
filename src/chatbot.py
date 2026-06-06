from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Generator

import ollama
import yaml
from dotenv import load_dotenv

from src.guardrails import check_guardrails
from src.schemas import (
    ChatResponse,
    ChatSession,
    GuardrailResult,
    GuardrailStatus,
    IntentCategory,
    LoanEligibilityData,
)

load_dotenv()

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "prompts.yaml"


def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _build_system_prompt(config: dict) -> str:
    base = config["system_prompt"]
    cot = config.get("chain_of_thought_template", "")

    examples_block = "\n\nFEW-SHOT EXAMPLES (follow this exact JSON format):\n"
    for category, examples in config.get("few_shot_examples", {}).items():
        examples_block += f"\n--- {category.upper()} ---\n"
        for ex in examples:
            examples_block += f'User: {ex["user"]}\nAssistant: {ex["assistant"].strip()}\n\n'

    return base + cot + examples_block


def _extract_json(text: str) -> dict | None:
    """Extract the first valid JSON object from a possibly-dirty model response."""
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    start = text.find("{")
    if start != -1:
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break
    return None


def _build_blocked_response(guardrail: GuardrailResult) -> ChatResponse:
    intent_map = {
        GuardrailStatus.PII_DETECTED: IntentCategory.BLOCKED,
        GuardrailStatus.OFF_TOPIC: IntentCategory.OFF_TOPIC,
        GuardrailStatus.INJECTION_ATTEMPT: IntentCategory.BLOCKED,
    }
    return ChatResponse(
        answer=guardrail.reason or "Request blocked by safety filters.",
        intent=intent_map.get(guardrail.status, IntentCategory.BLOCKED),
        confidence=1.0,
        requires_human_agent=guardrail.is_injection_attempt,
        guardrail_result=guardrail,
        follow_up_questions=(
            ["How can I help you with a banking or insurance query?"]
            if guardrail.is_off_topic
            else []
        ),
    )


def _build_messages(
    system_prompt: str,
    history: list[dict[str, str]],
    user_message: str,
) -> list[dict[str, str]]:
    """Build Ollama message list with system prompt, history, and new message."""
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})
    return messages


class BankingChatbot:
    def __init__(self) -> None:
        self._model = os.getenv("OLLAMA_MODEL", "llama3.2")
        self._host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self._temperature = float(os.getenv("TEMPERATURE", "0.3"))
        self._max_tokens = int(os.getenv("MAX_TOKENS", "2048"))
        self._config = _load_config()
        self._system_prompt = _build_system_prompt(self._config)

        self._client = ollama.Client(host=self._host)
        self._options = {"temperature": self._temperature, "num_predict": self._max_tokens}

        # Verify Ollama is reachable and the model exists
        self._verify_connection()

    def _verify_connection(self) -> None:
        try:
            response = self._client.list()
            available = [m.model for m in response.models]
            model_base = self._model.split(":")[0]
            if not any(model_base in m for m in available):
                names = ", ".join(available) if available else "none pulled yet"
                raise ValueError(
                    f"Model '{self._model}' not found in Ollama. "
                    f"Available models: {names}. "
                    f"Run: ollama pull {self._model}"
                )
        except Exception as e:
            if "Connection refused" in str(e) or "ConnectError" in str(e):
                raise ValueError(
                    "Cannot connect to Ollama at http://localhost:11434. "
                    "Make sure Ollama is running (open the Ollama app or run 'ollama serve')."
                )
            raise

    def _call_ollama(
        self,
        user_message: str,
        history: list[dict[str, str]],
    ) -> str:
        messages = _build_messages(self._system_prompt, history, user_message)
        try:
            response = self._client.chat(
                model=self._model,
                messages=messages,
                options=self._options,
            )
            return response.message.content
        except Exception as e:
            raise RuntimeError(f"Ollama error: {e}")

    def _call_ollama_stream(
        self,
        user_message: str,
        history: list[dict[str, str]],
    ) -> Generator[str, None, None]:
        messages = _build_messages(self._system_prompt, history, user_message)
        try:
            stream = self._client.chat(
                model=self._model,
                messages=messages,
                options=self._options,
                stream=True,
            )
            for chunk in stream:
                content = chunk.message.content
                if content:
                    yield content
        except Exception as e:
            raise RuntimeError(f"Ollama stream error: {e}")

    def _parse_response(self, raw: str, guardrail: GuardrailResult) -> ChatResponse:
        data = _extract_json(raw)
        if not data:
            # Local models sometimes respond in plain text — wrap it gracefully
            return ChatResponse(
                answer=raw,
                intent=IntentCategory.GENERAL,
                confidence=0.5,
                guardrail_result=guardrail,
            )

        loan_data: LoanEligibilityData | None = None
        if data.get("loan_eligibility"):
            try:
                loan_data = LoanEligibilityData(**data["loan_eligibility"])
            except Exception:
                loan_data = None

        return ChatResponse(
            answer=data.get("answer", raw),
            intent=IntentCategory(data.get("intent", "general")),
            confidence=float(data.get("confidence", 0.8)),
            follow_up_questions=data.get("follow_up_questions", []),
            requires_human_agent=bool(data.get("requires_human_agent", False)),
            structured_data=data.get("structured_data"),
            loan_eligibility=loan_data,
            disclaimer=data.get("disclaimer"),
            guardrail_result=guardrail,
        )

    def chat(
        self,
        user_message: str,
        session: ChatSession,
    ) -> ChatResponse:
        """Process a user message and return a structured ChatResponse."""
        guardrail = check_guardrails(user_message)

        if not guardrail.passed:
            return _build_blocked_response(guardrail)

        history = session.get_history()
        raw = self._call_ollama(user_message, history)
        response = self._parse_response(raw, guardrail)

        session.add_message("user", user_message)
        session.add_message("assistant", raw)

        return response

    def chat_stream(
        self,
        user_message: str,
        session: ChatSession,
    ) -> tuple[Generator[str, None, None], GuardrailResult]:
        """Stream response tokens."""
        guardrail = check_guardrails(user_message)
        if not guardrail.passed:
            def _blocked_gen():
                yield _build_blocked_response(guardrail).answer
            return _blocked_gen(), guardrail

        history = session.get_history()
        return self._call_ollama_stream(user_message, history), guardrail

    def finalize_stream(
        self,
        full_response: str,
        user_message: str,
        session: ChatSession,
        guardrail: GuardrailResult,
    ) -> ChatResponse:
        session.add_message("user", user_message)
        session.add_message("assistant", full_response)
        return self._parse_response(full_response, guardrail)
