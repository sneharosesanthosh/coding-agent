"""
CLI entrypoint.

Phase 1 goal: prove the plumbing works end to end —
    user types something -> Claude responds -> printed nicely.

No tools, no file access, no memory yet. That comes in later phases; this
file is intentionally small so it's easy to see the whole flow at once.
"""

from __future__ import annotations

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown

from agent.llm_client import LLMClient

load_dotenv()  # pulls ANTHROPIC_API_KEY from a local .env if present

app = typer.Typer(help="A minimal coding agent, built from scratch.")
console = Console()

SYSTEM_PROMPT = (
    "You are a helpful coding assistant running in a terminal. "
    "Keep answers concise and use code blocks for code."
)


@app.command()
def ask(prompt: str) -> None:
    """One-shot: send a single prompt and print the response."""
    client = LLMClient()
    response = client.send(
        messages=[{"role": "user", "content": prompt}],
        system=SYSTEM_PROMPT,
    )
    console.print(Markdown(response.text))


@app.command()
def chat() -> None:
    """Interactive loop: keep chatting until the user quits."""
    client = LLMClient()
    history: list[dict] = []

    console.print("[bold cyan]Coding agent[/bold cyan] — type 'exit' to quit.\n")

    while True:
        user_input = console.input("[bold green]you>[/bold green] ")
        if user_input.strip().lower() in {"exit", "quit"}:
            break

        history.append({"role": "user", "content": user_input})

        response = client.send(messages=history, system=SYSTEM_PROMPT)
        history.append({"role": "assistant", "content": response.text})

        console.print("[bold magenta]agent>[/bold magenta]")
        console.print(Markdown(response.text))
        console.print()


if __name__ == "__main__":
    app()