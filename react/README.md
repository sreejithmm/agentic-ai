# ReAct Agent

The first agent in the `agentic-ai` workspace. This console experiment uses
Azure OpenAI to demonstrate how a tool-using ReAct loop accumulates token and
cost overhead across multiple reasoning steps.

## What It Demonstrates

The agent runs a fixed comparison task: calculate population density for India
and China, identify the lower-density country, and calculate a related value.
It compares compact and detailed simulated knowledge-base results and reports:

- ReAct steps and tools used
- Input and output tokens accumulated across model calls
- Final unique tokens versus total billed tokens
- Estimated input/output cost
- Repeated-action and maximum-step safeguards

The knowledge bases are embedded demo data. The `search` tool does not browse the
internet or query an external database.

## Run It

From the `agentic-ai` project root, create and activate the shared virtual
environment if you have not already done so:

```bash
python3 -m venv .venv
```

Creates an isolated environment in `.venv` for this workspace.

```bash
source .venv/bin/activate
```

Activates the environment in the current terminal session. On Windows, use
`.venv\\Scripts\\activate` instead.

```bash
python -m pip install -r requirements.txt
```

Installs the Azure OpenAI client, Rich terminal formatting, token-counting
support, and Black listed for the workspace.

Set the Azure OpenAI configuration before running:

```bash
export AZURE_OPENAI_API_KEY="your-api-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
export AZURE_OPENAI_DEPLOYMENT="your-deployment-name"
```

These commands configure authentication, the Azure resource endpoint, and the
model deployment. Replace the placeholders with real values, but never commit
those values.

Start the agent:

```bash
python -m react.main
```

Runs the ReAct loop and prints the final answer, token metrics, estimated cost,
and analysis table.

## Validate Without Calling Azure

```bash
python -m py_compile react/main.py common/azure_openai_client.py
```

Checks the agent and its shared Azure client for Python syntax errors without
making an Azure request.

## Files

- `main.py` contains the ReAct loop, simulated tools, demo data, metrics, and
  terminal output.
- `../common/azure_openai_client.py` contains reusable Azure OpenAI request and
  response handling.
- `../requirements.txt` lists the shared workspace dependencies.

## Security

Keep API keys in environment variables or a local secret manager. If a key is
ever exposed, revoke it in Azure immediately and issue a replacement.
