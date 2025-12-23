import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Generator, List

from openai import OpenAI
from ..tools import TOOL_SPECS, run_tool

logger = logging.getLogger("wonderful.agent.openai")

# Unified model configuration for OpenAI
_MODEL_VERSION = os.getenv("MODEL_VERSION") or os.getenv("OPENAI_MODEL") or "gpt-5"
_API_KEY = os.getenv("MODEL_API_KEY") or os.getenv("OPENAI_API_KEY")

if not _API_KEY:
    raise RuntimeError("MODEL_API_KEY (or OPENAI_API_KEY) is required when MODEL_PROVIDER=openai")

MODEL = _MODEL_VERSION
client = OpenAI(api_key=_API_KEY)

logger.info("Initialized OpenAI agent with model=%s", MODEL)

# Load system prompt from file
_PROMPT_FILE = Path(__file__).resolve().parents[1] / "system_prompt.txt"
SYSTEM_INSTRUCTIONS = _PROMPT_FILE.read_text(encoding="utf-8").strip()


def _to_openai_tools(tool_specs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert TOOL_SPECS into OpenAI's expected tool format."""
    openai_tools: List[Dict[str, Any]] = []

    for spec in tool_specs or []:
        if spec.get("type") != "function":
            continue

        openai_tools.append(
            {
                "type": "function",
                "function": {
                    "name": spec["name"],
                    "description": spec.get("description", ""),
                    "parameters": spec.get("parameters", {"type": "object", "properties": {}}),
                }
            }
        )

    return openai_tools


OPENAI_TOOLS = _to_openai_tools(TOOL_SPECS)


def stream(messages: List[Dict[str, str]], max_tool_rounds: int) -> Generator[Dict[str, Any], None, None]:
    chat_messages: List[Dict[str, Any]] = [{"role": m["role"], "content": m["content"]} for m in messages]

    for _round_idx in range(max_tool_rounds):
        logger.info("OpenAI round %d/%d - messages=%d", _round_idx + 1, max_tool_rounds, len(chat_messages))
        try:
            stream_resp = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "system", "content": SYSTEM_INSTRUCTIONS}] + chat_messages,
                tools=OPENAI_TOOLS if OPENAI_TOOLS else None,
                tool_choice="auto",
                stream=True,
            )

            assistant_message = {"role": "assistant", "content": "", "tool_calls": []}

            for chunk in stream_resp:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta

                # Handle text content streaming
                if delta.content:
                    yield {"type": "text_delta", "delta": delta.content}
                    assistant_message["content"] += delta.content

                # Handle tool calls
                if delta.tool_calls:
                    for tool_call_delta in delta.tool_calls:
                        if tool_call_delta.index is not None:
                            idx = tool_call_delta.index
                            # Ensure we have enough tool calls in the list
                            while len(assistant_message["tool_calls"]) <= idx:
                                assistant_message["tool_calls"].append({
                                    "id": "",
                                    "type": "function",
                                    "function": {"name": "", "arguments": ""}
                                })

                            if tool_call_delta.id:
                                assistant_message["tool_calls"][idx]["id"] = tool_call_delta.id

                            if tool_call_delta.function:
                                if tool_call_delta.function.name:
                                    assistant_message["tool_calls"][idx]["function"]["name"] = tool_call_delta.function.name

                                if tool_call_delta.function.arguments:
                                    assistant_message["tool_calls"][idx]["function"]["arguments"] += tool_call_delta.function.arguments
                                    # Stream tool argument deltas for UI display
                                    yield {"type": "tool_args_delta", "item_id": assistant_message["tool_calls"][idx]["id"], "delta": tool_call_delta.function.arguments}

            # Check if there are tool calls to execute
            if assistant_message.get("tool_calls"):
                chat_messages.append(assistant_message)

                for tool_call in assistant_message["tool_calls"]:
                    name = tool_call["function"]["name"]
                    call_id = tool_call["id"]
                    args_str = tool_call["function"]["arguments"]

                    try:
                        args = json.loads(args_str)
                    except json.JSONDecodeError:
                        args = {}

                    yield {"type": "tool_call", "name": name, "call_id": call_id, "arguments": args}

                    result = run_tool(name, args)
                    yield {"type": "tool_result", "name": name, "call_id": call_id, "result": result}

                    # Add tool result to messages
                    chat_messages.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": json.dumps(result, ensure_ascii=False)
                    })
            else:
                # No tool calls, we're done
                yield {"type": "done"}
                return

        except Exception as e:
            logger.exception("Error in OpenAI streaming round: %s", e)
            yield {"type": "error", "error": {"message": str(e)}}
            return

    yield {"type": "error", "error": {"message": f"Maximum tool call rounds ({max_tool_rounds}) reached. This likely indicates an infinite loop. Please try rephrasing your request or contact support."}}

