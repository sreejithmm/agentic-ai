# Azure ReAct Agent

A standalone Azure OpenAI experiment that demonstrates how a tool-using ReAct
agent accumulates token and cost overhead as it reasons through multiple steps.
The program is a console application rather than a service or web API.

## What It Demonstrates

The program runs a fixed comparison task: calculate population density for India
and China, identify the lower-density country, and calculate a related value.
During the run it compares compact and detailed simulated knowledge-base results
and reports:

- ReAct steps and tools used
- Input and output tokens accumulated across model calls
- Final unique tokens versus total billed tokens
- Estimated input/output cost
- Repeated-action and maximum-step safeguards

The knowledge bases are embedded demo data. The `search` tool does not browse the
internet or query an external database.

## Requirements

- Python 3.10 or newer
- An Azure OpenAI resource with access to the Responses API
- An Azure OpenAI model deployment
- An Azure OpenAI API key

## Installation

Run these commands from the project directory:

```bash
python3 -m venv .venv
```

Creates an isolated Python environment in `.venv`, so this project's packages do
not alter your system Python installation or other projects.

```bash
source .venv/bin/activate
```

Activates the virtual environment for the current terminal session. On Windows,
use `.venv\\Scripts\\activate` instead.

```bash
python -m pip install --upgrade pip
```

Updates `pip` inside the virtual environment. This is optional, but helps avoid
installation issues with older package-manager versions.

```bash
python -m pip install -r react/requirements.txt
```

Installs the Azure OpenAI client, Rich terminal formatting, token-counting
support, and the formatting tool listed in `requirements.txt`.

## Configuration

The application reads these variables when it starts:

```bash
export AZURE_OPENAI_API_KEY="your-api-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
export AZURE_OPENAI_DEPLOYMENT="your-deployment-name"
```

Each command sets one variable in the current shell:

- `AZURE_OPENAI_API_KEY` authenticates requests to Azure OpenAI.
- `AZURE_OPENAI_ENDPOINT` identifies the Azure OpenAI resource endpoint.
- `AZURE_OPENAI_DEPLOYMENT` selects the model deployment to call.

The values above are placeholders. Replace them with your real values, and never
commit them. The repository ignores `.env` files and local virtual environments;
`.env.example` documents the required names without containing credentials.

## Run

```bash
python -m react.main
```

Starts the console demonstration. It creates the Azure client, runs the ReAct
loop, calls the configured deployment for reasoning and summarization, and then
prints the final answer, token metrics, estimated cost, and analysis table.

## Validate Without Calling Azure

```bash
python -m py_compile react/main.py common/azure_openai_client.py
```

Checks both Python files for syntax errors without making an Azure request. This
is useful after editing the code or before opening a pull request.

When you are finished, run:

```bash
deactivate
```

Leaves the project's virtual environment and returns the terminal to its normal
Python environment.

## Project Files

- `react/main.py` contains the ReAct loop, simulated tools, demo data, metrics,
  and terminal output.
- `common/azure_openai_client.py` contains reusable Azure OpenAI request and
  response handling for agents in this project.
- `react/requirements.txt` lists the React demo's Python dependencies.
- `.env.example` lists the required configuration variable names.
- `.gitignore` prevents local credentials, virtual environments, caches, and OS
	files from being committed.

## Security Notes

Keep API keys in environment variables or a local secret manager. Do not paste a
real key into `react/main.py`, `README.md`, `.env.example`, or a commit. If a key is
ever exposed, revoke it in Azure immediately and issue a replacement.
