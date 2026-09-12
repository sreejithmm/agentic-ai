# Azure ReAct Agent

Standalone Azure OpenAI version of the ReAct token-overhead prototype.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set the Azure OpenAI configuration before running:

```bash
export AZURE_OPENAI_API_KEY="your-api-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
export AZURE_OPENAI_DEPLOYMENT="your-deployment-name"
```

Run the prototype:

```bash
python main.py
```

`main.py` contains the ReAct loop and demo knowledge bases. `gemini_azure_adapter.py`
translates the Gemini-style internal message representation to the Azure OpenAI
Responses API.
