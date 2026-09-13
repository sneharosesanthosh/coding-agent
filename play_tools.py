from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()          # loads ANTHROPIC_API_KEY from .env
client = Anthropic()   # the SDK picks up the key from the environment

# ---- Part A: describe a tool to Claude ----
tools = [
    {
        "name": "read_file",
        "description": "Read a text file from the user's project and return its contents.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path relative to the project root."}
            },
            "required": ["path"],
        },
    }
]

question = "What is 2 + 2?"

# Call 1: Claude sees the question and the tool list
first = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    tools=tools,
    messages=[{"role": "user", "content": question}],
)

print("stop_reason:", first.stop_reason)   # expect: tool_use
for block in first.content:                 # content is a LIST of blocks
    print("  ", block)


if first.stop_reason == "end_turn":
    print("".join(b.text for b in first.content if b.type == "text"))
else:
    # ---- Part B: do what Claude asked, send the result back ----
    tool_call = next(b for b in first.content if b.type == "tool_use")
    with open(tool_call.input["path"]) as f:   # YOU run the tool, not Claude
        file_text = f.read()

    # Call 2: full history + the tool result
    second = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        tools=tools,
        messages=[
            {"role": "user", "content": question},
            {"role": "assistant", "content": first.content},   # the whole block list, not just text
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": tool_call.id, "content": file_text}
            ]},
        ],
    )

    print("\nstop_reason:", second.stop_reason)  # expect: end_turn
    print("".join(b.text for b in second.content if b.type == "text"))
