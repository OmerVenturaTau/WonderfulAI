import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Generator, List

import google.generativeai as genai

from ..tools import TOOL_SPECS, run_tool

logger = logging.getLogger("wonderful.agent.gemini")

# Unified model configuration for Gemini
_MODEL_VERSION = os.getenv("MODEL_VERSION") or os.getenv("GEMINI_MODEL") or "gemini-1.5-flash"
_API_KEY = os.getenv("MODEL_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if not _API_KEY:
    raise RuntimeError("MODEL_API_KEY (or GEMINI_API_KEY / GOOGLE_API_KEY) is required when MODEL_PROVIDER=gemini")

genai.configure(api_key=_API_KEY)


def _to_gemini_tools(tool_specs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert OpenAI-style TOOL_SPECS into Gemini function_declarations."""
    function_declarations: List[Dict[str, Any]] = []

    for spec in tool_specs or []:
        if spec.get("type") != "function":
            continue

        function_declarations.append(
            {
                "name": spec["name"],
                "description": spec.get("description", ""),
                "parameters": spec.get("parameters", {"type": "object", "properties": {}}),
            }
        )

    if not function_declarations:
        return []

    # google-generativeai expects a list of tool groups; each group can hold multiple function_declarations
    return [{"function_declarations": function_declarations}]


GEMINI_TOOLS = _to_gemini_tools(TOOL_SPECS)

# Load system prompt from file (same as OpenAI agent)
_PROMPT_FILE = Path(__file__).resolve().parents[1] / "system_prompt.txt"
SYSTEM_INSTRUCTIONS = _PROMPT_FILE.read_text(encoding="utf-8").strip()

MODEL = genai.GenerativeModel(
    model_name=_MODEL_VERSION,
    tools=GEMINI_TOOLS if GEMINI_TOOLS else None,
    system_instruction=SYSTEM_INSTRUCTIONS,
)

logger.info("Initialized Gemini agent with model=%s", _MODEL_VERSION)


def _convert_messages_to_contents(messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Convert our simple chat message format into Gemini `contents`.

    Incoming messages are of the form:
        {"role": "user" | "assistant", "content": "..."}
    Gemini expects:
        {"role": "user" | "model", "parts": [{"text": "..."}]}
    """
    contents: List[Dict[str, Any]] = []

    for m in messages:
        role = m.get("role", "user")
        if role == "assistant":
            role = "model"
        elif role != "user":
            # Fallback: treat everything else as user content
            role = "user"

        contents.append(
            {
                "role": role,
                "parts": [
                    {
                        "text": m.get("content", ""),
                    }
                ],
            }
        )

    return contents


def stream(messages: List[Dict[str, str]], max_tool_rounds: int) -> Generator[Dict[str, Any], None, None]:
    """
    Streaming Gemini agent with tool support.

    Yields the same event schema as `openai_agent.stream`:
      - {"type": "text_delta", "delta": str}
      - {"type": "tool_args_delta", "item_id": str, "delta": str}
      - {"type": "tool_call", "name": str, "call_id": str, "arguments": dict}
      - {"type": "tool_result", "name": str, "call_id": str, "result": Any}
      - {"type": "done"}
      - {"type": "error", "error": {"message": str}}
    """
    chat_contents: List[Dict[str, Any]] = _convert_messages_to_contents(messages)

    for round_idx in range(max_tool_rounds):
        logger.info("Gemini round %d/%d - contents=%d", round_idx + 1, max_tool_rounds, len(chat_contents))

        try:
            stream_resp = MODEL.generate_content(
                contents=chat_contents,
                stream=True,
            )

            pending_calls: List[Dict[str, Any]] = []
            assistant_text = ""

            for chunk in stream_resp:
                # Stream text deltas
                text_delta = getattr(chunk, "text", None)
                if text_delta:
                    yield {"type": "text_delta", "delta": text_delta}
                    assistant_text += text_delta

                # Extract any function calls from this chunk
                candidates = getattr(chunk, "candidates", None) or []
                for cand in candidates:
                    content = getattr(cand, "content", None)
                    if not content:
                        continue

                    parts = getattr(content, "parts", None) or []
                    for part in parts:
                        function_call = getattr(part, "function_call", None)
                        if not function_call:
                            continue

                        name = getattr(function_call, "name", None)
                        if not name:
                            continue

                        # `args` is a Mapping[str, Any]; convert to plain dict
                        args: Dict[str, Any]
                        try:
                            raw_args = getattr(function_call, "args", None)
                            args = dict(raw_args) if raw_args is not None else {}
                        except Exception:
                            args = {}

                        call_id = f"gemini-{name}-{len(pending_calls)}-{round_idx}"
                        pending_calls.append({"id": call_id, "name": name, "args": args})

                        # For UI parity, emit a single tool_args_delta with the full argument JSON
                        yield {
                            "type": "tool_args_delta",
                            "item_id": call_id,
                            "delta": json.dumps(args, ensure_ascii=False),
                        }

            # If we saw any function calls, execute them and continue another round
            if pending_calls:
                # Add the assistant text (if any) to the chat history
                if assistant_text:
                    chat_contents.append(
                        {
                            "role": "model",
                            "parts": [{"text": assistant_text}],
                        }
                    )

                for call in pending_calls:
                    name = call["name"]
                    call_id = call["id"]
                    args = call["args"] or {}

                    # Emit tool_call event
                    yield {"type": "tool_call", "name": name, "call_id": call_id, "arguments": args}

                    # Execute the tool locally
                    result = run_tool(name, args)
                    yield {"type": "tool_result", "name": name, "call_id": call_id, "result": result}

                    # Add tool result to the chat as a functionResponse
                    chat_contents.append(
                        {
                            "role": "tool",
                            "parts": [
                                {
                                    "function_response": {
                                        "name": name,
                                        "response": result,
                                    }
                                }
                            ],
                        }
                    )
            else:
                # No tool calls; we are done with this conversation
                yield {"type": "done"}
                return

        except Exception as e:
            logger.exception("Error in Gemini streaming round: %s", e)
            yield {"type": "error", "error": {"message": str(e)}}
            return

    # Safety net if we somehow loop too many times
    yield {
        "type": "error",
        "error": {
            "message": f"Maximum tool call rounds ({max_tool_rounds}) reached. This likely indicates an infinite loop. Please try rephrasing your request or contact support.",
        },
    }


