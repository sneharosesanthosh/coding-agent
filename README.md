# coding-agent

A small terminal coding agent built from scratch in Python on the Claude API.
Give it a task ("fix the bug in calc.py", "add a test for utils.py") and it
reads your code, edits files, runs commands, and checks its own work. It asks
your permission before changing anything.

No agent framework: the tool-calling loop is about 50 lines in `agent/agent.py`.

## Features

- **5 tools**: `list_files`, `read_file`, `write_file`, `edit_file`, `run_command`
- **Permission prompts**: file writes, edits and shell commands need your `y`
  first, with a preview of the change
- **Stays in your project**: file tools refuse any path outside the folder you
  started the agent in
- **Safety limits**: max 25 steps per task, 60s command timeout, long output is cut
- **Chat memory**: follow-up messages keep the context; `/clear` starts over

## Setup

```bash
uv venv
source .venv/bin/activate
uv pip install -e .

cp .env.example .env   # then put your key in .env: ANTHROPIC_API_KEY=sk-ant-...
```

## Run

Start it inside the project you want it to work on:

```bash
cd path/to/some/project
agent chat                               # interactive
agent ask "add docstrings to utils.py"   # one task, then exit
```

## How it works

```
you ──► agent.run(task)
          │
          ▼
   ┌─► send history + tool list to Claude
   │      │
   │   stop_reason == "tool_use"?
   │      ├─ no  ──► print Claude's answer, done
   │      └─ yes ──► ask permission (write/edit/run)
   │                 ► run the tool
   └──────────────── ► send the results back
```

## Project layout

```
agent/
├── cli.py         # terminal only: input, output, y/n prompts
├── agent.py       # the agent loop
├── tools.py       # tool functions + the schemas sent to Claude
└── llm_client.py  # thin wrapper around the Anthropic SDK
```

## Design choices

- **Own loop instead of LangChain or similar**: the loop is short, easy to debug,
  and nothing is hidden.
- **`edit_file` replaces exact text** instead of rewriting whole files: it uses
  fewer tokens, and if the text isn't found it fails loudly instead of silently
  dropping code.
- **`agent.py` doesn't print anything**: the CLI passes in `confirm` and
  `on_tool_call` functions, so the loop can be tested with a fake LLM and no API key.
- **`llm_client.py` wraps the SDK**: switching models or providers only touches one file.
