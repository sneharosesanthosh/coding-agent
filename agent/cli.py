"""
CLI entrypoint.

Terminal-only concerns live here: reading input, printing output, and asking
permission before a mutating tool runs. The agent loop itself (agent.py)
doesn't know a terminal exists.
"""

from __future__ import annotations

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown

from agent import agent
from agent.llm_client import LLMClient

load_dotenv()  # pulls ANTHROPIC_API_KEY from a local .env if present

app = typer.Typer(help="A minimal coding agent, built from scratch.")
console = Console()

SYSTEM_PROMPT = (
    "You are a coding agent running in a terminal, working inside the user's "
    "current project folder. You can read, search, write, and edit files, "
    "and run shell commands, using the tools available to you. File tools "
    "only work inside the project folder. Explain what you're about to do "
    "before mutating tool calls; keep other answers concise and use code "
    "blocks for code."
)


def confirm(name: str, tool_input: dict) -> bool:
    """Ask the user before a mutating tool runs. Returns True to proceed."""
    if name == "write_file":
        preview = f"write {tool_input.get('path')} ({len(tool_input.get('content', ''))} chars)"
    elif name == "edit_file":
        preview = (
            f"edit {tool_input.get('path')}:\n"
            f"  [red]- {tool_input.get('old_text', '')}[/red]\n"
            f"  [green]+ {tool_input.get('new_text', '')}[/green]"
        )
    elif name == "run_command":
        preview = f"run: {tool_input.get('command')}"
    else:
        preview = str(tool_input)

    console.print(f"\n[bold yellow]permission needed[/bold yellow] — {name}")
    console.print(preview)
    answer = console.input("[bold yellow]proceed? [y/N] [/bold yellow]").strip().lower()
    return answer == "y"


def on_tool_call(name: str, tool_input: dict) -> None:
    """Print a one-line note right before any tool (read-only or mutating) runs."""
    console.print(f"[dim]→ {name}({tool_input})[/dim]")


def _run_task(client: LLMClient, history: list[dict], task: str) -> str:
    return agent.run(
        task=task,
        client=client,
        history=history,
        system=SYSTEM_PROMPT,
        confirm=confirm,
        on_tool_call=on_tool_call,
    )


@app.command()
def ask(prompt: str) -> None:
    """One-shot: run a single task, then exit."""
    client = LLMClient()
    history: list[dict] = []
    result = _run_task(client, history, prompt)
    console.print(Markdown(result))


@app.command()
def chat() -> None:
    """Interactive loop: keep chatting until the user quits."""
    client = LLMClient()
    history: list[dict] = []

    console.print("[bold cyan]Coding agent[/bold cyan] — type 'exit' to quit, '/clear' to reset context.\n")

    while True:
        user_input = console.input("[bold green]you>[/bold green] ")
        if user_input.strip().lower() in {"exit", "quit"}:
            break
        if user_input.strip() == "/clear":
            history.clear()
            console.print("[dim](context cleared)[/dim]\n")
            continue
        if not user_input.strip():
            continue

        result = _run_task(client, history, user_input)

        console.print("[bold magenta]agent>[/bold magenta]")
        console.print(Markdown(result))
        console.print()


if __name__ == "__main__":
    app()
