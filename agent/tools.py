"""
Tools the agent can use.

Every tool is two things:
  1. A plain Python function that does the work.
  2. A schema that tells Claude the tool exists and how to call it.

Read tools (read_file, list_files, search_files) and mutating tools
(write_file, edit_file, run_command) all share the same path safety check,
so the agent can never touch anything outside the folder it was started in.
"""


from __future__ import annotations
from pathlib import Path
import subprocess

PROJECT_ROOT = Path.cwd().resolve()

COMMAND_TIMEOUT = 60
MAX_OUTPUT_CHARS = 4000


def _safe_path(path: str) -> Path:
    """Resolve `path` and refuse it if it falls outside PROJECT_ROOT."""
    resolved = (PROJECT_ROOT / path).resolve()
    if resolved != PROJECT_ROOT and PROJECT_ROOT not in resolved.parents:
        raise ValueError(f"'{path}' is outside the project folder ({PROJECT_ROOT})")
    return resolved


def read_file(path: str) -> str:
    """Return the full text of a file."""
    return _safe_path(path).read_text()


def list_files(path: str = ".") -> str:
    """List what's directly inside a directory. Folders get a trailing '/'."""
    entries = sorted(_safe_path(path).iterdir())
    lines = [f"{p.name}/" if p.is_dir() else p.name for p in entries]
    return "\n".join(lines) or "(empty directory)"


def search_files(query: str, path: str = ".") -> str:
    """Search for a text string across files under path, recursively."""
    SKIP_NAMES = {".git", "__pycache__", ".venv", ".env"}
    MAX_MATCHES = 50
    query_lower = query.lower()
    matches = []

    for file_path in sorted(_safe_path(path).rglob("*")):
        if not file_path.is_file():
            continue
        if any(part in SKIP_NAMES for part in file_path.parts):
            continue

        try:
            lines = file_path.read_text().splitlines()
        except (UnicodeDecodeError, PermissionError):
            continue  # binary or unreadable file — skip it, don't crash the whole search

        for line_number, line in enumerate(lines, start=1):
            if query_lower in line.lower():
                matches.append(f"{file_path}:{line_number}: {line.strip()}")
                if len(matches) >= MAX_MATCHES:
                    matches.append(f"...stopped after {MAX_MATCHES} matches")
                    return "\n".join(matches)

    return "\n".join(matches) or f"No matches for '{query}'"


def write_file(path: str, content: str) -> str:
    """Create a file (or overwrite it completely) with new content."""
    resolved = _safe_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content)
    return f"Wrote {len(content)} chars to {path}"


def edit_file(path: str, old_text: str, new_text: str) -> str:
    """Replace one exact, unique occurrence of old_text with new_text in a file."""
    resolved = _safe_path(path)
    original = resolved.read_text()
    count = original.count(old_text)

    if count == 0:
        raise ValueError(f"Text not found in {path}. Nothing was changed.")
    if count > 1:
        raise ValueError(
            f"Text found {count} times in {path}; old_text must be unique. "
            "Include more surrounding context."
        )

    resolved.write_text(original.replace(old_text, new_text, 1))
    return f"Edited {path}"


def run_command(command: str) -> str:
    """Run a shell command inside the project folder and return its output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {COMMAND_TIMEOUT}s"

    output = (result.stdout + result.stderr).strip() or "(no output)"
    if len(output) > MAX_OUTPUT_CHARS:
        output = output[:MAX_OUTPUT_CHARS] + f"\n...output truncated after {MAX_OUTPUT_CHARS} chars"

    return f"exit code: {result.returncode}\n{output}"



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
    {
        "name": "search_files",
        "description": (
            "Search for a text string across all files under a directory, recursively. "
            "Use this to find where a function, variable, or string is defined or used."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The text to search for.",
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search under, relative to the project root. Defaults to '.'.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "write_file",
        "description": (
            "Create a file or overwrite it completely with new content. "
            "Use for new files, or when rewriting a file's full contents."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file, relative to the project root.",
                },
                "content": {
                    "type": "string",
                    "description": "The full text the file should contain.",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": (
            "Replace one exact, unique block of text in a file with new text. "
            "Prefer this over write_file for small changes to existing files. "
            "old_text must match the file exactly, including whitespace, and "
            "must occur exactly once — include enough surrounding context to "
            "make it unique."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file, relative to the project root.",
                },
                "old_text": {
                    "type": "string",
                    "description": "The exact text to find and replace.",
                },
                "new_text": {
                    "type": "string",
                    "description": "The text to replace it with.",
                },
            },
            "required": ["path", "old_text", "new_text"],
        },
    },
    {
        "name": "run_command",
        "description": (
            "Run a shell command in the project folder and return its output. "
            f"Times out after {COMMAND_TIMEOUT}s. Use for running tests, "
            "linters, or other project commands."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to run.",
                },
            },
            "required": ["command"],
        },
    },
]

# ---------------------------------------------------------------------------
# 3. The dispatcher — turns Claude's request into a real function call
# ---------------------------------------------------------------------------

TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_files": list_files,
    "search_files": search_files,
    "write_file": write_file,
    "edit_file": edit_file,
    "run_command": run_command,
}

# Tools that change files or run commands — the CLI asks permission before
# executing any of these. Read-only tools run without a prompt.
MUTATING_TOOLS = {"write_file", "edit_file", "run_command"}


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

