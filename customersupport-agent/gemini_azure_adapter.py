"""Shared Azure OpenAI Responses API adapter for Gemini-style prototypes."""

import json
import os

from openai import OpenAI
import tiktoken


class Part:
    """Small provider-neutral part used by the existing Gemini-style loop."""

    def __init__(self, text=None, function_call=None, function_response=None, thought=False):
        self.text = text
        self.function_call = function_call
        self.function_response = function_response
        self.thought = thought


class Content:
    """Small provider-neutral content message used by the existing loop."""

    def __init__(self, role, parts):
        self.role = role
        self.parts = parts


class FunctionCall:
    def __init__(self, name, args, call_id=""):
        self.name = name
        self.args = args
        self.call_id = call_id


class FunctionResponse:
    def __init__(self, name, result, call_id=""):
        self.name = name
        self.call_id = call_id
        self.response = {"result": result}


class AzureResponsesAdapter:
    """Translate a Gemini-style prototype history to Azure Responses API calls."""

    def __init__(self, api_key=None, endpoint=None, deployment=None):
        self.api_key = api_key or os.environ["AZURE_OPENAI_API_KEY"]
        endpoint = endpoint or os.environ["AZURE_OPENAI_ENDPOINT"]
        self.endpoint = self._normalize_endpoint(endpoint)
        self.deployment = deployment or os.environ["AZURE_OPENAI_DEPLOYMENT"]
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.endpoint + "/",
        )

    @staticmethod
    def _normalize_endpoint(endpoint):
        normalized = endpoint.rstrip("/")
        if normalized.endswith("/responses"):
            normalized = normalized[:-len("/responses")]
        if not normalized.endswith("/openai/v1"):
            normalized += "/openai/v1"
        return normalized

    @staticmethod
    def _content_to_input(content):
        text_parts = [part.text for part in content.parts if part.text]
        function_calls = [
            part.function_call for part in content.parts if part.function_call
        ]
        function_responses = [
            part.function_response
            for part in content.parts
            if part.function_response
        ]
        items = []
        if text_parts:
            role = "assistant" if content.role == "model" else content.role
            items.append({"role": role, "content": "\n".join(text_parts)})
        for call in function_calls:
            items.append({
                "type": "function_call",
                "call_id": call.call_id,
                "name": call.name,
                "arguments": json.dumps(call.args),
            })
        for response in function_responses:
            items.append({
                "type": "function_call_output",
                "call_id": response.call_id,
                "output": str(response.response["result"]),
            })
        return items

    def create_response(self, contents, instructions, tools):
        """Send the accumulated prototype history to the Azure deployment."""
        response = self.client.responses.create(
            model=self.deployment,
            instructions=instructions,
            input=[
                item
                for content in contents
                for item in self._content_to_input(content)
            ],
            tools=tools,
        )
        return self._response_to_compat(response)

    def summarize(self, prompt):
        """Run a standalone text-generation request for a local summarizer tool."""
        response = self.client.responses.create(
            model=self.deployment,
            input=prompt,
        )
        return response.output_text.strip()

    @staticmethod
    def _response_to_compat(response):
        parts = []
        for item in response.output:
            if getattr(item, "type", None) == "function_call":
                parts.append(Part(function_call=FunctionCall(
                    item.name,
                    json.loads(item.arguments or "{}"),
                    item.call_id,
                )))
            elif getattr(item, "type", None) == "message":
                for block in item.content:
                    if getattr(block, "type", None) == "output_text":
                        parts.append(Part(text=block.text))

        usage = getattr(response, "usage", None)
        usage_metadata = type("Usage", (), {
            "prompt_token_count": getattr(usage, "input_tokens", 0) if usage else 0,
            "candidates_token_count": getattr(usage, "output_tokens", 0) if usage else 0,
            "thoughts_token_count": 0,
        })()
        candidate = type("Candidate", (), {
            "content": Content("model", parts),
            "finish_reason": getattr(response, "status", "completed"),
        })()
        return type("CompatResponse", (), {
            "candidates": [candidate],
            "usage_metadata": usage_metadata,
        })()

    def count_context_tokens(self, contents):
        """Estimate serialized context tokens when the provider count API is absent."""
        try:
            encoding = tiktoken.encoding_for_model(self.deployment)
        except KeyError:
            encoding = tiktoken.get_encoding("o200k_base")
        serialized = json.dumps(
            [
                item
                for content in contents
                for item in self._content_to_input(content)
            ],
            ensure_ascii=False,
        )
        return len(encoding.encode(serialized))
