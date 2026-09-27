"""
The agent loop.

Send history + tools to Claude. If Claude answers with text, we're done. If
Claude asks for a tool, run it (after permission, for mutating tools) and
send the result back — repeat until Claude gives a final answer or the step
limit is hit.

This module doesn't print anything: the caller supplies `confirm` (asked
before any mutating tool runs) and `on_tool_call` (called right before any
tool runs, for progress output), so the loop can be tested with a fake LLM
and no terminal or API key.
"""

from __future__ import annotations

from typing import Callable

from agent.llm_client import LLMClient
from agent.tools import MUTATING_TOOLS, TOOL_SCHEMAS, execute_tool

MAX_STEPS = 25

ConfirmFn = Callable[[str, dict], bool]
OnToolCallFn = Callable[[str, dict], None]


def run(
    task: str,
    client: LLMClient,
    history: list[dict],
    system: str,
    confirm: ConfirmFn,
    on_tool_call: OnToolCallFn,
) -> str:
    """
    Run one task to completion inside an existing chat history.

    `history` is mutated in place (task, assistant turns, and tool results
    are all appended to it) so the caller can pass the same list back in on
    the next call and keep full context across turns.

    Returns the final assistant text.
    """
    history.append({"role": "user", "content": task})

    for _ in range(MAX_STEPS):
        response = client.send(messages=history, system=system, tools=TOOL_SCHEMAS)
        history.append({"role": "assistant", "content": response.raw.content})

        if response.stop_reason != "tool_use":
            return response.text

        tool_results = []
        for block in response.raw.content:
            if block.type != "tool_use":
                continue

            on_tool_call(block.name, block.input)

            if block.name in MUTATING_TOOLS and not confirm(block.name, block.input):
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": "The user declined to run this. Do not retry it; ask what they'd like instead.",
                        "is_error": True,
                    }
                )
                continue

            output, is_error = execute_tool(block.name, block.input)
            result = {
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": output,
            }
            if is_error:
                result["is_error"] = True
            tool_results.append(result)

        history.append({"role": "user", "content": tool_results})

    return f"Stopped after {MAX_STEPS} steps without finishing — try breaking the task into smaller pieces."
