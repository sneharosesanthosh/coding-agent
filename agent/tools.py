"""
Tools the agent can use.

Every tool is two things:
  1. A plain Python function that does the work.
  2. A schema that tells Claude the tool exists and how to call it.

Phase 2 scope: read-only. Nothing here can change your files yet.
"""


from __future__ import annotations
from pathlib import Path

def read_file(path: str) -> str:
    """Return the full text of a file."""
    return Path(path).read_text()


def list_files(path: str = ".") -> str:
    """List what's directly inside a directory. Folders get a trailing '/'."""
    entries = sorted(Path(path).iterdir())
    lines = [f"{p.name}/" if p.is_dir() else p.name for p in entries]
    return "\n".join(lines) or "(empty directory)"


TOOL_SCHEMAS = [
    {
        "name": "read_file",
        "description": (
            "Read a text file and return its full contents. "
            "Use this before answering questions about a file's code."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file, relative to the project root.",
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_files",
        "description": (
            "List the files and folders directly inside a directory (not recursive). "
            "Folder names end with '/'. Use this to explore the project."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory to list, relative to the project root. Defaults to '.'.",
                },
            },
            "required": [],
        },
    },
]

# ---------------------------------------------------------------------------
# 3. The dispatcher — turns Claude's request into a real function call
# ---------------------------------------------------------------------------

TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_files": list_files,
}


def execute_tool(name: str, tool_input: dict) -> tuple[str, bool]:
    """
    Run the tool Claude asked for.

    Returns (output, is_error). Errors are returned, never raised: Claude
    reads the error message and can try something else instead of the
    program crashing.
    """
    func = TOOL_FUNCTIONS.get(name)
    if func is None:
        return f"Error: unknown tool '{name}'", True

    try:
        return func(**tool_input), False
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}", True

