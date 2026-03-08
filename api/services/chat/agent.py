"""
Chat agent orchestration — uses the OpenAI Responses API with GPT-4.1
to answer questions about UK trig points by routing to vector search
and/or Text-to-SQL tools.
"""

import json
import logging
from collections.abc import Generator
from typing import Any

from openai import OpenAI
from sqlalchemy.orm import Session

from api.core.config import settings
from api.services.chat.tools import (
    TOOL_DEFINITIONS,
    lookup_trig,
    query_database,
    vector_search,
)

logger = logging.getLogger(__name__)

MODEL = "gpt-4.1"

SYSTEM_PROMPT = """\
You are the TrigpointingUK assistant — a knowledgeable, friendly expert on UK \
triangulation pillars and the Ordnance Survey Retriangulation of Great Britain \
(1935-1962).

You have three tools:
1. **vector_search** — searches the scanned text of "The Retriangulation of \
Great Britain 1935-1962" (the official HMSO book) for historical and technical \
information about the retriangulation programme, observation methods, station \
construction, computation, and specific trig stations mentioned in the book.
2. **lookup_trig** — looks up a trig point by name, waypoint ID, or flush \
bracket number. Returns verified data directly from the database. This is the \
fastest and most reliable way to get details about a specific trig point.
3. **query_database** — queries the TrigpointingUK database for complex \
questions requiring SQL: aggregations, rankings, counts, recent activity, \
spatial queries, and joins across multiple tables.

## CRITICAL — factual accuracy rules

NEVER fabricate, guess, or infer any of the following. These MUST come from a \
tool result or you MUST NOT include them:
- Waypoint IDs (e.g. TP4250)
- Flush bracket numbers
- Grid references or coordinates
- Condition codes or visit counts
- Any other specific identifiers or numeric data about a trig point

If a user asks about a specific trig point by name, ALWAYS use lookup_trig \
to look it up before responding. If the tool returns no result, say you could \
not find it — do NOT fill in details from memory or assumption.

Only state facts that are directly supported by a tool result from the current \
conversation. If you are uncertain or the tools did not return the information, \
say so explicitly. Getting a fact wrong is far worse than admitting you do not \
know.

## General guidelines
- Use vector_search for historical/book questions, query_database for current \
data questions. Use both when a question spans history and current state.
- Cite your sources: mention page numbers from the book, or say "according to \
the database".
- Be concise but thorough. Use British English spelling.
- Format responses in Markdown for readability.
"""


def _get_client() -> OpenAI:
    return OpenAI(api_key=settings.OPENAI_API_KEY)


def _execute_tool(name: str, arguments: str, db: Session) -> str:
    """Execute a tool call and return the result as a string."""
    args = json.loads(arguments)
    if name == "vector_search":
        results = vector_search(query=args["query"], db=db, top_k=args.get("top_k", 5))
        return json.dumps(results, default=str)
    elif name == "lookup_trig":
        results = lookup_trig(query=args["query"], db=db)
        return json.dumps(results, default=str)
    elif name == "query_database":
        return query_database(question=args["question"], db=db)
    else:
        return json.dumps({"error": f"Unknown tool: {name}"})


def stream_response(
    messages: list[dict[str, str]], db: Session
) -> Generator[dict[str, Any], None, None]:
    """
    Run the agent loop and yield SSE-friendly event dicts.

    Events yielded:
      {"type": "text_delta", "text": "..."}
      {"type": "tool_use", "tool": "...", "input": {...}}
      {"type": "done"}
      {"type": "error", "message": "..."}
    """
    client = _get_client()

    # Build input messages for the Responses API
    input_messages: list[dict] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            input_messages.append({"role": "user", "content": content})
        elif role == "assistant":
            input_messages.append({"role": "assistant", "content": content})

    previous_response_id = None
    max_rounds = 10

    for _round in range(max_rounds):
        try:
            create_kwargs: dict[str, Any] = {
                "model": MODEL,
                "instructions": SYSTEM_PROMPT,
                "tools": TOOL_DEFINITIONS,
                "temperature": 0.3,
            }

            if previous_response_id is not None:
                # Continue the conversation with tool outputs
                create_kwargs["previous_response_id"] = previous_response_id
                create_kwargs["input"] = input_messages
            else:
                create_kwargs["input"] = input_messages

            pending_tool_calls: dict[str, dict] = {}

            with client.responses.stream(**create_kwargs) as stream:
                for event in stream:
                    event_type = event.type

                    if event_type == "response.output_item.added":
                        item = event.item  # type: ignore[union-attr]
                        if item.type == "function_call":
                            tool_call_id: str = item.id or item.call_id  # type: ignore[union-attr, assignment]
                            pending_tool_calls[tool_call_id] = {  # type: ignore[union-attr]
                                "name": item.name,  # type: ignore[union-attr]
                                "arguments": "",
                                "call_id": item.call_id,  # type: ignore[union-attr]
                            }

                    elif event_type == "response.function_call_arguments.delta":
                        item_id = event.item_id  # type: ignore[union-attr]
                        if item_id in pending_tool_calls:
                            pending_tool_calls[item_id]["arguments"] += event.delta  # type: ignore[union-attr]

                    elif event_type == "response.output_text.delta":
                        yield {"type": "text_delta", "text": event.delta}  # type: ignore[union-attr]

                    elif event_type == "response.completed":
                        pass

            # Get the completed response to access its ID
            completed = stream.get_final_response()
            current_response_id = completed.id

            if not pending_tool_calls:
                yield {"type": "done"}
                return

            # Execute tool calls and prepare outputs
            tool_outputs: list[dict] = []
            for item_id, tc in pending_tool_calls.items():
                yield {
                    "type": "tool_use",
                    "tool": tc["name"],
                    "input": json.loads(tc["arguments"]) if tc["arguments"] else {},
                }

                logger.info("Executing tool %s", tc["name"])
                result = _execute_tool(tc["name"], tc["arguments"], db)

                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": tc["call_id"],
                        "output": result,
                    }
                )

            # Send tool results back to continue the conversation
            previous_response_id = current_response_id
            input_messages = tool_outputs

        except Exception as exc:
            logger.exception("Agent error in round %d", _round)
            yield {"type": "error", "message": str(exc)}
            return

    yield {"type": "error", "message": "Maximum tool call rounds exceeded."}
