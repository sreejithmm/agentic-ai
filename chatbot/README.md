# Chatbot Agent

The chatbot agent is a starting point for a conversational Azure OpenAI agent in
the `agentic-ai` workspace. Its implementation currently contains only a
runnable entry point; conversation behavior, tools, and state management can be
added here without changing the other agents.

## Run It

Run these commands from the `agentic-ai` project root:

```bash
source .venv/bin/activate
```

Activates the workspace virtual environment.

```bash
python -m chatbot.main
```

Starts the chatbot agent entry point. The current scaffold confirms that the
agent is ready for implementation.

## Validate Without Calling Azure

```bash
python -m py_compile chatbot/main.py
```

Checks this agent for Python syntax errors without making an Azure request.

## Files

- `main.py` is the chatbot agent entry point.
- `README.md` documents this agent's purpose and commands.
- `__init__.py` marks the folder as a Python package.

Shared Azure configuration, dependency installation, security guidance, and
workspace conventions are documented in the root [`README.md`](../README.md).
