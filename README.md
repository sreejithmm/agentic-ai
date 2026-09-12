# Agentic AI

A workspace for experimenting with multiple Azure OpenAI agents. Each agent is
kept in its own folder, while reusable Azure OpenAI functionality is shared from
`common/`.

## What You Will Find Here

The repository is organized around independent agent experiments:

```text
agentic-ai/
├── common/
│   └── azure_openai_client.py
├── react/
    ├── main.py
    └── README.md
└── chatbot/
    ├── main.py
    └── README.md
```

The `react` and `chatbot` agents exist today. Future agents can be added as
sibling folders, for example `planner/`, `researcher/`, or `critic/`, each with
the same entry point, README, and package structure.

The shared code in `common/` provides Azure OpenAI request and response handling
so agents can focus on their own orchestration, tools, prompts, and evaluation
logic.

## Requirements

- Python 3.10 or newer
- An Azure OpenAI resource with access to the Responses API
- An Azure OpenAI model deployment
- An Azure OpenAI API key

## Setup

Run these commands from the `agentic-ai` project root.

```bash
python3 -m venv .venv
```

Creates an isolated Python environment for this workspace.

```bash
source .venv/bin/activate
```

Activates that environment in the current terminal session. On Windows, use
`.venv\\Scripts\\activate` instead.

```bash
python -m pip install --upgrade pip
```

Updates the package installer inside the virtual environment.

```bash
python -m pip install -r requirements.txt
```

Installs the workspace dependencies currently needed by the `react` agent and
shared Azure code. Add dependencies used by multiple agents to this root file.
If an agent later needs a dependency that should not be installed for the rest
of the workspace, give that agent its own requirements file instead.

## Configuration

All agents use the same Azure OpenAI environment variables:

```bash
export AZURE_OPENAI_API_KEY="your-api-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
export AZURE_OPENAI_DEPLOYMENT="your-deployment-name"
```

Each `export` command places one setting in the current shell:

- `AZURE_OPENAI_API_KEY` authenticates requests.
- `AZURE_OPENAI_ENDPOINT` identifies the Azure OpenAI resource.
- `AZURE_OPENAI_DEPLOYMENT` selects the deployed model.

The values above are placeholders. Keep real credentials in environment
variables or a secret manager. Never commit them. `.env` files, virtual
environments, caches, and local OS files are ignored by Git; `.env.example`
contains only the required variable names.

## Running Agents

Run an agent as a Python module from the project root. The module form keeps the
root package layout available, including imports from `common/`.

```bash
python -m react.main
```

Runs the current ReAct agent. See [`react/README.md`](react/README.md) for its
task, tools, output, and agent-specific validation command.

```bash
python -m chatbot.main
```

Runs the current chatbot scaffold. See [`chatbot/README.md`](chatbot/README.md)
for its purpose and validation command.

When another agent is added, it should follow the same pattern:

```bash
python -m <agent-folder>.<entry-point>
```

For example, a future `planner/main.py` would run as:

```bash
python -m planner.main
```

## Shared Code

- `common/azure_openai_client.py` provides reusable Azure OpenAI client behavior.
- `common/` is intended for code shared by multiple agents, not agent-specific
  prompts or tools.
- Agent folders own their orchestration, tools, demo data, metrics, and output.

## Security

Do not place API keys in Python files, README files, `.env.example`, or commits.
If a credential is exposed, revoke it in Azure immediately and issue a
replacement.

## Deactivate the Environment

```bash
deactivate
```

Leaves the project's virtual environment and returns the terminal to its normal
Python environment.
