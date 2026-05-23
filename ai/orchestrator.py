from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv, find_dotenv
from openai import OpenAI, OpenAIError

from ai.prompts import SYSTEM_PROMPT
from ai.tools import TOOLS_DEFINITION, execute_tool
from core.logger import get_logger

log = get_logger("ai.orchestrator")


_dotenv_path = find_dotenv(usecwd=False, raise_error_if_not_found=False)
if _dotenv_path:
    load_dotenv(dotenv_path=_dotenv_path)
    log.info("[orchestrator] .env loaded from: %s", _dotenv_path)
else:
    log.warning("[orchestrator] No .env file found — OPENAI_API_KEY must be set in the environment")

MODEL = "gpt-4o"
MAX_TOOL_ITERATIONS = 6
MAX_HISTORY_MESSAGES = 20


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY not found. "
            "Add it to the .env file at the project root."
        )
    log.debug("[orchestrator] OpenAI client instantiated with key ...%s", api_key[-4:])
    return OpenAI(api_key=api_key)


def _serialize_message(msg) -> dict:
    serialized: dict = {"role": msg.role}

    if msg.content is not None:
        serialized["content"] = msg.content

    if msg.tool_calls:
        serialized["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in msg.tool_calls
        ]

    log.debug("[orchestrator] Serialized message: %s", json.dumps(serialized, ensure_ascii=False)[:300])
    return serialized


def _execute_tool_calls(msg, messages: list[dict]) -> None:
    for tool_call in msg.tool_calls:
        fn_name = tool_call.function.name
        raw_args = tool_call.function.arguments

        log.info("[orchestrator] Tool call received — id=%s name=%s", tool_call.id, fn_name)
        log.debug("[orchestrator] Raw arguments: %s", raw_args)

        try:
            arguments = json.loads(raw_args) if raw_args else {}
        except json.JSONDecodeError as exc:
            log.error(
                "[orchestrator] Invalid JSON in arguments for '%s': %s | raw='%s'",
                fn_name, exc, raw_args
            )
            arguments = {}

        log.debug("[orchestrator] Parsed arguments: %s", arguments)

        result = execute_tool(fn_name, arguments)

        log.debug("[orchestrator] Result for '%s': %s", fn_name, str(result)[:300])

        try:
            result_str = json.dumps(result, ensure_ascii=False, default=str)
        except (TypeError, ValueError) as exc:
            log.warning("[orchestrator] Could not serialize result for '%s': %s", fn_name, exc)
            result_str = str(result)

        tool_result_msg = {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": result_str,
        }
        messages.append(tool_result_msg)
        log.info("[orchestrator] Tool '%s' result added to context (%d chars)", fn_name, len(result_str))


def run(user_message: str, history: list[dict]) -> str:
    """
    Send a message to the assistant and return the final response as a string.

    Args:
        user_message: User text input.
        history:      Message history in OpenAI format (modified in-place).

    Returns:
        The final response text.
    """
    log.info("[orchestrator/run] Start — message: '%s'", user_message[:100])

    client = _get_client()
    history.append({"role": "user", "content": user_message})

    trimmed = history[-MAX_HISTORY_MESSAGES:]
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}, *trimmed]

    log.debug(
        "[orchestrator/run] Messages sent to OpenAI: %d (system + %d history)",
        len(messages), len(trimmed)
    )

    final_text = ""
    iterations = 0

    while iterations < MAX_TOOL_ITERATIONS:
        iterations += 1
        log.info(
            "[orchestrator/run] Iteration %d/%d — messages in context: %d",
            iterations, MAX_TOOL_ITERATIONS, len(messages)
        )

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS_DEFINITION,
                tool_choice="auto",
                temperature=0.2,
            )
        except OpenAIError as exc:
            log.error("[orchestrator/run] OpenAI call error (iter %d): %s", iterations, exc)
            raise

        choice = response.choices[0]
        finish_reason = choice.finish_reason
        msg = choice.message

        log.info(
            "[orchestrator/run] Response received — finish_reason='%s' content_len=%s tool_calls=%s",
            finish_reason,
            len(msg.content) if msg.content else 0,
            len(msg.tool_calls) if msg.tool_calls else 0
        )

        messages.append(_serialize_message(msg))

        if finish_reason == "stop":
            final_text = msg.content or ""
            log.info(
                "[orchestrator/run] Final response obtained (%d chars) after %d iteration(s)",
                len(final_text), iterations
            )
            break

        if finish_reason == "tool_calls" and msg.tool_calls:
            _execute_tool_calls(msg, messages)
        else:
            log.warning(
                "[orchestrator/run] Unexpected finish_reason: '%s' — aborting loop",
                finish_reason
            )
            final_text = msg.content or ""
            break

    else:
        log.error(
            "[orchestrator/run] Reached the limit of %d iterations without a final answer",
            MAX_TOOL_ITERATIONS
        )
        final_text = (
            "No pude completar la consulta en el número de pasos permitido. "
            "Por favor, reformula la pregunta de forma más específica."
        )

    history.append({"role": "assistant", "content": final_text})
    log.info("[orchestrator/run] End — total history: %d messages", len(history))
    return final_text


def stream(user_message: str, history: list[dict]) -> Generator[str, None, None]:
    """
    Streaming variant: resolves tool calls in a blocking phase, then streams the final text.

    Yields:
        Fragments of the final response text.
    """
    log.info("[orchestrator/stream] Start — message: '%s'", user_message[:100])

    client = _get_client()
    history.append({"role": "user", "content": user_message})

    trimmed = history[-MAX_HISTORY_MESSAGES:]
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}, *trimmed]

    log.debug("[orchestrator/stream] Messages sent to OpenAI: %d", len(messages))

    iterations = 0
    needs_final_call = False

    while iterations < MAX_TOOL_ITERATIONS:
        iterations += 1
        log.info(
            "[orchestrator/stream] Phase 1 — iteration %d/%d, messages: %d",
            iterations, MAX_TOOL_ITERATIONS, len(messages)
        )

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS_DEFINITION,
                tool_choice="auto",
                temperature=0.2,
            )
        except OpenAIError as exc:
            log.error("[orchestrator/stream] OpenAI call error (iter %d): %s", iterations, exc)
            raise

        choice = response.choices[0]
        finish_reason = choice.finish_reason
        msg = choice.message

        log.info(
            "[orchestrator/stream] Phase 1 response — finish_reason='%s' content_len=%s tool_calls=%s",
            finish_reason,
            len(msg.content) if msg.content else 0,
            len(msg.tool_calls) if msg.tool_calls else 0
        )

        messages.append(_serialize_message(msg))

        if finish_reason == "stop":
            final_text = msg.content or ""
            log.info("[orchestrator/stream] Direct response without tools (%d chars)", len(final_text))
            history.append({"role": "assistant", "content": final_text})
            yield final_text
            return

        if finish_reason == "tool_calls" and msg.tool_calls:
            _execute_tool_calls(msg, messages)
            needs_final_call = True
        else:
            log.warning(
                "[orchestrator/stream] Unexpected finish_reason in phase 1: '%s'",
                finish_reason
            )
            final_text = msg.content or ""
            history.append({"role": "assistant", "content": final_text})
            yield final_text
            return

    if not needs_final_call:
        fallback = (
            "No pude completar la consulta en el número de pasos permitido. "
            "Por favor, reformula la pregunta de forma más específica."
        )
        log.error("[orchestrator/stream] Iterations exhausted before reaching phase 2")
        history.append({"role": "assistant", "content": fallback})
        yield fallback
        return

    log.info(
        "[orchestrator/stream] Phase 2 — final streaming call with %d messages in context",
        len(messages)
    )
    log.debug(
        "[orchestrator/stream] Roles in phase 2 context: %s",
        [m["role"] for m in messages]
    )

    try:
        stream_response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS_DEFINITION,
            tool_choice="none",
            temperature=0.2,
            stream=True,
        )
    except OpenAIError as exc:
        log.error("[orchestrator/stream] Error in final streaming call: %s", exc)
        raise

    collected: list[str] = []
    chunk_count = 0

    for chunk in stream_response:
        if not chunk.choices:
            log.debug("[orchestrator/stream] Chunk without choices, ignored")
            continue
        delta = chunk.choices[0].delta
        if delta and delta.content:
            collected.append(delta.content)
            chunk_count += 1
            yield delta.content

    final_text = "".join(collected)
    log.info(
        "[orchestrator/stream] Streaming complete — %d chunks, %d total chars",
        chunk_count, len(final_text)
    )

    if not final_text:
        log.warning("[orchestrator/stream] Phase 2 returned empty text — check the context sent")

    history.append({"role": "assistant", "content": final_text})
    log.info("[orchestrator/stream] End — total history: %d messages", len(history))
