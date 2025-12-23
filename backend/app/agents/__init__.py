import logging
import os
from typing import Any, Dict, Generator, List

from . import gemini_agent, openai_agent

logger = logging.getLogger("wonderful.agent")


def stream_agent(messages: List[Dict[str, str]]) -> Generator[Dict[str, Any], None, None]:
    """
    Dispatch to the configured provider. Default: OpenAI.
    """
    # Basic logging configuration (no-op if already configured by app)
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        )

    provider = os.getenv("MODEL_PROVIDER", "openai").lower()
    max_tool_rounds = int(os.getenv("MAX_TOOL_ROUNDS", "10"))

    logger.info("Starting stream_agent with provider=%s, max_tool_rounds=%d", provider, max_tool_rounds)

    if provider == "gemini":
        logger.info("Dispatching to Gemini agent")
        yield from gemini_agent.stream(messages, max_tool_rounds)
    else:
        logger.info("Dispatching to OpenAI agent")
        yield from openai_agent.stream(messages, max_tool_rounds)

