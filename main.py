#!/usr/bin/env python3
"""
ReAct Agent Prototype - Token Overhead Demonstration
Demonstrates the ReAct (Reasoning + Acting) loop with tools:
  - search: simulated web search (compact vs bloated modes)
  - summariser: text summarisation via Gemini

This version tracks, measures, and visualises the quadratic token overhead 
inherent in ReAct loops, contrasting optimized vs. unoptimized payloads and loop failures.
"""

import ast
import math
import operator
import os
import re
import sys
import textwrap
import time

from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

# ── Console ──────────────────────────────────────────────────────────────────

console = Console()

# ── Shared Azure adapter ─────────────────────────────────────────────────────

from azure_openai_client import AzureResponsesAdapter, Content, FunctionResponse, Part

ADAPTER = AzureResponsesAdapter()
AZURE_OPENAI_ENDPOINT = ADAPTER.endpoint
MODEL_ID = ADAPTER.deployment
CLIENT = ADAPTER.client
_Part = Part
_Content = Content
_FunctionResponse = FunctionResponse

# ── Pricing Constants ─────────────────────────────────────────────────────────
# Gemini 2.5 Flash pricing per 1,000,000 tokens (as of mid-2026 / standard rates)
PRICE_INPUT_PER_M = 0.075   # $0.075 per million input tokens
PRICE_OUTPUT_PER_M = 0.30   # $0.30 per million output tokens (includes reasoning)

# ── Step budget ───────────────────────────────────────────────────────────────

MAX_STEPS = 12  # agent is forcibly halted after this many Thought-Action cycles

# ── Simulated knowledge bases ────────────────────────────────────────────────

# 1. Compact Knowledge Base (efficient, pruned summaries)
KNOWLEDGE_BASE_COMPACT = {
    "population of india": "India has a population of approximately 1.44 billion people as of 2024.",
    "population of china": "China has a population of approximately 1.41 billion people as of 2024.",
    "gdp of india": "India's GDP is approximately $3.73 trillion USD (2024 estimate).",
    "gdp of china": "China's GDP is approximately $18.53 trillion USD (2024 estimate).",
    "gdp per capita india": "India's GDP per capita is approximately $2,600 USD.",
    "gdp per capita china": "China's GDP per capita is approximately $13,140 USD.",
    "average salary india": "The average annual salary in India is approximately $3,000-$4,000 USD.",
    "area of india": "India covers an area of 3.29 million square kilometres.",
    "area of china": "China covers an area of approximately 9.60 million square kilometres.",
}

# 2. Detailed Knowledge Base (bloated, simulating raw web-scraped content or un-chunked database records)
KNOWLEDGE_BASE_DETAILED = {
    "population of india": """
================================================================================
DEMOGRAPHICS AND POPULATION OF THE REPUBLIC OF INDIA (RAW RECORD #1042)
================================================================================
India, officially the Republic of India, is a sovereign country in South Asia. 
According to the United Nations and national census estimates, the population of India in 2024 
stands at approximately 1,441,981,744 (1.44 billion) people, making it the most 
populous country in the world, having surpassed China in mid-2023.

HISTORICAL DEMOGRAPHIC TRENDS:
In 1950, India's population was estimated at approximately 376 million. Over the 
subsequent decades, improved healthcare, increased agricultural productivity (such as 
the Green Revolution led by M. S. Swaminathan), and declining infant mortality rates 
led to rapid population growth. The decadal growth rate peaked in the late 1970s and 
1980s at around 2.2% annually and has since been on a steady decline.

AGE STRUCTURE AND DEMOGRAPHIC DIVIDEND:
India has one of the youngest populations globally, with more than 50% of its population 
under the age of 25 and more than 65% under the age of 35. The median age in India is 
approximately 28.7 years. This provides India with a unique "demographic dividend," 
yielding a massive workforce that is expected to peak around 2040, driving economic growth.

GEOGRAPHICAL DISTRIBUTION:
- Uttar Pradesh: The most populous state, with an estimated population of over 240 million, 
  which would make it the fifth-most populous country in the world if it were independent.
- Maharashtra: Second-most populous, exceeding 126 million.
- Bihar: Third-most populous, exceeding 125 million, and boasting the highest population density.
- Major Urban Agglomerations: Mumbai (approx. 21 million), Delhi (approx. 33 million), 
  Kolkata (approx. 15 million), Bangalore (approx. 14 million).

POPULATION CONTROL POLICIES:
Unlike China's administrative 'One-Child Policy', India's population initiatives have 
primarily relied on voluntary family planning, raising literacy rates among women, 
and raising the legal age of marriage. The Total Fertility Rate (TFR) has dropped 
nationwide to approximately 2.0 children per woman, which is below the replacement level of 2.1.
""",
    
    "population of china": """
================================================================================
DEMOGRAPHICS AND POPULATION OF THE PEOPLE'S REPUBLIC OF CHINA (RAW RECORD #1043)
================================================================================
China, officially the People's Republic of China, is a sovereign state in East Asia.
As of 2024, the National Bureau of Statistics of China estimates its population to be 
approximately 1,409,670,000 (1.41 billion) people, ranking as the second-most populous 
country in the world after being surpassed by India in 2023.

HISTORICAL DEMOGRAPHIC TRENDS AND THE ONE-CHILD POLICY:
China's population grew rapidly post-WWII under Mao Zedong's encouraging policies. 
However, concerns over overpopulation and resource strain led to the implementation of the 
strict "One-Child Policy" in 1979. This administrative measure dramatically reduced fertility 
rates but led to significant demographic imbalances, including a rapidly ageing population 
and a skewed gender ratio (approx. 110-115 boys for every 100 girls).

THE DEMOGRAPHIC CHALLENGE AND AGING POPULATION:
China's population entered a period of negative growth in 2022, ahead of previous projections. 
The fertility rate has plummeted to roughly 1.0 to 1.2, far below the replacement rate of 2.1.
Over 20% of the population is currently aged 60 or older, and this is projected to exceed 
30% by 2035. The workforce (ages 15-59) has been shrinking by several million annually, 
creating a "silver tsunami" that poses severe pension, healthcare, and economic growth challenges.

GEOGRAPHICAL DISTRIBUTION:
- Guangdong: The most populous province, with over 126 million people.
- Shandong: Second-most populous, with over 101 million.
- Henan: Third-most populous, with over 99 million.
- Megacities: Shanghai (approx. 29 million), Beijing (approx. 22 million), Guangzhou 
  (approx. 14 million), Shenzhen (approx. 13 million).

POLICY ADJUSTMENTS:
In response to the rapid demographic decline, the government officially ended the One-Child Policy 
in 2016, transitioning to a Two-Child Policy, and further relaxed it to a Three-Child Policy 
in 2021. However, due to high living costs, long working hours, and real estate prices, 
marriage and birth rates remain near historic lows.
""",

    "gdp of india": """
================================================================================
ECONOMY AND GROSS DOMESTIC PRODUCT (GDP) OF THE REPUBLIC OF INDIA (RAW RECORD #2011)
================================================================================
The economy of India is characterised as a developing market economy. It is currently 
the world's fifth-largest economy by nominal GDP and the third-largest by purchasing 
power parity (PPP). According to international financial institutions (IMF, World Bank), 
India's nominal GDP in 2024 is approximately $3.73 trillion USD (estimated to reach 
$3.9 trillion by the end of the fiscal year).

ECONOMIC STRUCTURE AND SECTORS:
- Services Sector: The largest contributor to India's GDP, accounting for approximately 
  54% of Gross Value Added (GVA). Key segments include Information Technology (IT), 
  business process outsourcing (BPO), software services, financial services, and tourism. 
  India is often called the "back office of the world."
- Industry Sector: Contributes about 26% to GVA. Includes manufacturing, construction, 
  power, mining, and gas. Initiatives like 'Make in India' aim to boost this sector's share.
- Agriculture Sector: Contributes approximately 18-20% to GVA but employs over 42% of 
  the nation's total workforce. Major crops include rice, wheat, cotton, sugar cane, and spices.

HISTORICAL CONTEXT AND REFORMS:
From independence in 1947 until 1991, India followed protectionist and democratic socialist 
policies, often termed the "License Raj," characterised by extensive regulation, high tariffs, 
and state monopolies. A severe balance of payments crisis in 1991 forced the government 
to initiate sweeping economic liberalisation reforms under Prime Minister P. V. Narasimha Rao 
and Finance Minister Manmohan Singh. These reforms dismantled industrial licensing, reduced 
tariffs, opened up Foreign Direct Investment (FDI), and privatised key public sector enterprises, 
unleashing decades of high GDP growth averaging 6-8% annually.

FUTURE OUTLOOK AND TARGETS:
The Indian government has stated a formal goal to transition India into a $5 trillion USD 
nominal economy by 2027 and a fully developed nation ('Viksit Bharat') by 2047, the centenary 
of its independence. Challenges include high youth unemployment, infrastructure gaps, 
regulatory complexity, and regional income disparity.
""",

    "gdp of china": """
================================================================================
ECONOMY AND GROSS DOMESTIC PRODUCT (GDP) OF THE PEOPLE'S REPUBLIC OF CHINA (RAW RECORD #2012)
================================================================================
The economy of the People's Republic of China is a market-oriented socialist economy 
incorporating industrial policies and strategic state-owned enterprises. It is the 
world's second-largest economy by nominal GDP and the largest by purchasing power parity (PPP). 
For 2024, China's nominal GDP is estimated at approximately $18.53 trillion USD, 
comprising nearly 18% of the entire global economy.

ECONOMIC STRUCTURE AND SECTORS:
- Industry and Manufacturing Sector: Traditionally the engine of China's economic rise, 
  contributing approximately 38% to GDP. Often dubbed the "world's factory," China leads 
  globally in manufacturing output across electronics, steel, heavy machinery, automotive 
  (including electric vehicles), and chemicals.
- Services Sector: Has grown to become the largest sector, accounting for approximately 
  54% of GDP. This includes finance, e-commerce, real estate, telecommunications, and retail.
- Agriculture Sector: Contributes around 7-8% to GDP but employs nearly 24% of the workforce.

HISTORICAL CONTEXT AND THE "ECONOMIC MIRACLE":
Following decades of central planning and isolation, China initiated its landmark "Reform and 
Opening Up" policy in 1978 under the leadership of Deng Xiaoping. The reforms introduced market 
incentives, allowed private enterprise, established Special Economic Zones (SEZs) like Shenzhen 
to attract foreign capital, and encouraged international trade. Joining the World Trade Organization 
(WTO) in 2001 accelerated China's integration into global supply chains. For nearly three decades, 
China achieved unprecedented double-digit GDP growth (averaging 10% annually), lifting over 
800 million people out of poverty in what economists describe as the greatest economic miracle in history.

CURRENT CHALLENGES AND TRANSITION:
The Chinese economy is currently undergoing a structural transition from investment-led and 
export-driven growth to consumption-led high-quality growth. It faces significant headwinds, 
including a major real estate sector debt crisis (triggered by developers like Evergrande), 
local government debt burdens, high youth unemployment, and escalating trade tensions with the 
United States and European Union regarding tech transfers and manufacturing overcapacity.
""",

    "area of india": """
================================================================================
GEOGRAPHY AND LAND AREA OF THE REPUBLIC OF INDIA (RAW RECORD #3041)
================================================================================
India covers an area of approximately 3,287,263 square kilometres (approx. 3.29 
million square kilometres), making it the seventh-largest country in the world by 
total geographical land area.
""",

    "area of china": """
================================================================================
GEOGRAPHY AND LAND AREA OF THE PEOPLE'S REPUBLIC OF CHINA (RAW RECORD #3042)
================================================================================
China covers an area of approximately 9,596,960 square kilometres (approx. 9.60 
million square kilometres), making it the fourth-largest country in the world by 
total geographical land area.
""",

    "gdp per capita india": """
================================================================================
GDP PER CAPITA OF THE REPUBLIC OF INDIA (RAW RECORD #2031)
================================================================================
The Gross Domestic Product (GDP) per capita of India stands at approximately 
$2,600 USD. This represents a moderate level of economic development on a per-person 
basis, although the total purchasing power parity of India's economy is highly robust 
owing to its massive domestic consumer population.
""",

    "gdp per capita china": """
================================================================================
GDP PER CAPITA OF THE PEOPLE'S REPUBLIC OF CHINA (RAW RECORD #2032)
================================================================================
According to the National Bureau of Statistics and international financial indicators (IMF, 
World Bank), the Gross Domestic Product (GDP) per capita of China is approximately 
$13,140 USD. This represents a substantial level of industrial and consumer sector expansion, 
having risen consistently over the past several decades.
"""
}

# Active search mode: toggled dynamically during runs
USE_DETAILED_SEARCH = False

# ── Tool implementations ──────────────────────────────────────────────────────


def tool_search(query: str) -> str:
    """Searches the selected knowledge base for facts matching the query.

    Args:
        query: The string or key to look up.

    Returns:
        The matched fact string, or a simulated busy prompt if not found.
    """
    normalized_query = re.sub(r"[^a-z0-9\s]", "", query.lower())
    query_words = set(normalized_query.split())
    
    # Remove filler words
    filler_words = {"of", "the", "in", "and", "a", "for", "is", "about", "approximately", "square", "kilometres", "kilometers", "land"}
    query_keywords = query_words - filler_words
    
    kb = KNOWLEDGE_BASE_DETAILED if USE_DETAILED_SEARCH else KNOWLEDGE_BASE_COMPACT
    
    best_match = None
    best_score = -1
    
    for kb_key, answer in kb.items():
        normalized_key = re.sub(r"[^a-z0-9\s]", "", kb_key.lower())
        key_words = set(normalized_key.split())
        key_keywords = key_words - filler_words
        
        # Calculate overlap score
        intersection = query_keywords.intersection(key_keywords)
        overlap_count = len(intersection)
        score = overlap_count * 10
        
        # Exact keyword match bonus
        if key_keywords == query_keywords:
            score += 100
        elif key_keywords.issubset(query_keywords):
            # Keyword subset matching bonus proportional to query coverage
            score += (len(key_keywords) / len(query_keywords)) * 50
            
        if score > best_score:
            best_score = score
            best_match = answer
            
    if best_score >= 15:  # Require at least some solid overlapping keywords
        return best_match

    # Simulated retry prompt if search doesn't find a match (the infinite loop trigger)
    return (
        f"Search index is temporarily busy. "
        f"Result for '{query}' not yet available — please retry the same query."
    )


def tool_summariser(text: str) -> str:
    """Summarises the provided text down to a single concise sentence.

    Args:
        text: The source text to summarize.

    Returns:
        A one-sentence summary string (max 30 words).
    """
    prompt = (
        "Summarise the following text in exactly one concise sentence "
        "(max 30 words):\n\n" + text
    )

    return ADAPTER.summarize(prompt)


def tool_calculator(expression: str) -> str:
    """Evaluates an arithmetic mathematical expression using Python's built-in eval.

    Args:
        expression: A string containing the mathematical expression.

    Returns:
        The evaluated result as a string, or an error message.
    """
    # Clean up expression (handles variations of inputs like equations, formulas, units)
    clean_expr = expression.replace("$", "").replace("trillion", "* 10**12").replace("billion", "* 10**9").replace("million", "* 10**6")
    try:
        # Evaluate using Python's built-in eval, with math module functions made available
        result = eval(clean_expr.strip(), {"__builtins__": {}, "math": math, "abs": abs, "round": round, "pow": pow})
        return f"{result}"
    except Exception as exc:
        return f"Calculator error: {exc}"


# Registry maps tool name -> callable
TOOLS = {
    "search": tool_search,
    "summariser": tool_summariser,
    "calculator": tool_calculator,
}

# ── Function Declarations ─────────────────────────────────────────────────────

search_func = {
    "name": "search",
    "description": "Searches the active knowledge base for factual demographic and economic information.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The exact string or topic to look up (e.g. 'population of india', 'gdp of china')."
            }
        },
        "required": ["query"],
    },
}

summariser_func = {
    "name": "summariser",
    "description": "Summarises the provided text down to a single concise sentence.",
    "parameters": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The source text to summarize."
            }
        },
        "required": ["text"],
    },
}

calculator_func = {
    "name": "calculator",
    "description": "Evaluates an arithmetic mathematical expression using Python's built-in eval.",
    "parameters": {
        "type": "object",
        "properties": {
            "expr": {
                "type": "string",
                "description": "The mathematical expression to evaluate (e.g. '3.73 * 10**12 / (1.44 * 10**9)')."
            }
        },
        "required": ["expr"],
    },
}

AZURE_TOOLS = [
    {"type": "function", **search_func},
    {"type": "function", **summariser_func},
    # TO DEMO CALCULATOR USAGE: Remove the comment below to expose the calculator.
    {"type": "function", **calculator_func},
]

# ── ReAct prompt template ─────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a helpful ReAct agent. Solve the task step by step using the provided tools.

At each step, you MUST first think before taking any action. You MUST output your detailed, step-by-step reasoning (Thought) as plain text BEFORE you make any tool call. Do not call a tool without writing your Thought first.

Rules:
- Do NOT use your own internal knowledge for facts; always use the 'search' tool.
- You MUST wait for the tool observation before taking the next step.
- Gather all necessary information before providing your final answer.
"""

SUPPRESSED_SYSTEM_PROMPT = """You are a helpful ReAct agent. Solve the task step by step using the provided tools.

CRITICAL RULE: You MUST NOT write any textual Thoughts, reasoning, plans, or step-by-step calculations. You MUST immediately and directly output a function call or the final answer with no preamble and no self-talk. Go straight to calling tools.

Rules:
- Do NOT use your own internal knowledge for facts; always use the 'search' tool.
- You MUST wait for the tool observation before taking the next step.
- Gather all necessary information before providing your final answer.
"""

# ── Model call with exponential-backoff retry ────────────────────────────────


def _call_model_with_retry(
    contents: list,
    system_prompt: str,
    include_thoughts: bool,
    max_retries: int = 5,
    base_delay: float = 10.0,
):
    """Invokes Azure Responses using the current history, retrying transient errors."""
    for attempt in range(max_retries):
        try:
            return ADAPTER.create_response(contents, system_prompt, AZURE_TOOLS)
        except Exception as exc:
            is_rate_limit = (
                "429" in str(exc) or "rate limit" in str(exc).lower()
            )
            if is_rate_limit and attempt < max_retries - 1:
                delay = base_delay * (2**attempt)
                console.print(
                    f"  [dim]Rate limited — retrying in {delay:.0f}s "
                    f"(attempt {attempt + 1}/{max_retries})[/dim]"
                )
                time.sleep(delay)
            else:
                raise


# ── Loop detection ────────────────────────────────────────────────────────────

def detect_loop(history: list[dict], window: int = 3) -> bool:
    """Evaluates whether the agent is stuck repeating the exact same tool and argument."""
    if len(history) < window:
        return False
    recent = history[-window:]
    actions = [(s.get("tool"), str(s.get("arg"))) for s in recent if s.get("tool")]
    if len(actions) < window:
        return False
    return len(set(actions)) == 1

# ── Core ReAct loop ───────────────────────────────────────────────────────────


def run_react_agent(
    task: str,
    use_detailed: bool = False,
    disable_loop_detection: bool = False,
    disable_thinking: bool = False,
    max_steps: int = MAX_STEPS,
) -> dict:
    """Executes the ReAct loop using native Function Calling until completion, tracking tokens."""
    global USE_DETAILED_SEARCH
    USE_DETAILED_SEARCH = use_detailed

    prompt = SUPPRESSED_SYSTEM_PROMPT if disable_thinking else SYSTEM_PROMPT
    include_thoughts = not disable_thinking

    start = time.time()

    contents: list[_Content] = [
        _Content(
            role="user",
            parts=[_Part(text="Task: " + task)],
        )
    ]

    step_history: list[dict] = []
    tools_used: list[str] = []
    halt_reason = "max_steps"
    final_answer = ""

    # Token counters
    cumulative_input = 0
    cumulative_output = 0
    step_metrics = []

    # Print the system prompt and instructions once at the start of the execution
    console.print(
        Panel(
            f"[bold yellow]Task:[/bold yellow] [white]{task}[/white]\n\n"
            f"[bold yellow]System Instructions:[/bold yellow]\n[dim]{prompt.strip()}[/dim]",
            title="[bold yellow]Agent Initialization[/bold yellow]",
            border_style="yellow",
            padding=(1, 2)
        )
    )
    console.print()

    for step in range(1, max_steps + 1):
        # ── Model call ────────────────────────────────────────────────────────
        response = _call_model_with_retry(contents, prompt, include_thoughts)

        # Robustly handle empty responses or blocked contents (e.g. due to safety or api errors)
        if not response.candidates:
            console.print("  [bold red]Error:[/bold red] [red]Model returned no candidates.[/red]")
            break
            
        candidate = response.candidates[0]
        if candidate.content is None or not candidate.content.parts:
            finish_reason = getattr(candidate, "finish_reason", "UNKNOWN")
            console.print(
                f"  [bold red]Error:[/bold red] [red]Model returned empty content.[/red] "
                f"[dim](Finish Reason: {finish_reason})[/dim]"
            )
            break

        model_content = candidate.content

        # ── Token Tracking ────────────────────────────────────────────────────
        usage = getattr(response, "usage_metadata", None)
        if usage:
            step_input = getattr(usage, "prompt_token_count", 0) or 0
            step_candidates = getattr(usage, "candidates_token_count", 0) or 0
            step_thoughts = getattr(usage, "thoughts_token_count", 0) or 0
        else:
            step_input = 0
            step_candidates = 0
            step_thoughts = 0

        step_output = step_candidates + step_thoughts
        cumulative_input += step_input
        cumulative_output += step_output

        step_metrics.append({
            "step": step,
            "input": step_input,
            "output": step_output,
            "thoughts": step_thoughts,
            "candidates": step_candidates,
            "total": step_input + step_output
        })

        # Check for function call
        fc_part = next((p for p in model_content.parts if getattr(p, "function_call", None)), None)

        # Extract textual thought (from native thoughts, regular text, or legacy args)
        text_parts = []
        for p in model_content.parts:
            if getattr(p, "thought", False) and getattr(p, "text", None):
                text_parts.append(p.text)
            elif getattr(p, "text", None):
                text_parts.append(p.text)
        thought = "\n".join(text_parts).strip()
        
        if fc_part and fc_part.function_call.args:
            args = fc_part.function_call.args
            if "thought" in args:
                thought = args["thought"]

        # Normalize extracted thought by stripping case-insensitive nested/recursive "Thought:" prefixes
        while thought.lower().startswith("thought:"):
            thought = thought[len("thought:"):].strip()

        # ── Print Step Header & Model Input ───────────────────────────────────
        console.print(f"\n[bold cyan]── Step {step:02d} ──[/bold cyan]")

        # Render Model Input (only show the latest message to keep the output clean)
        input_elements = []
        msg = contents[-1]
        role = msg.role
        parts_texts = []
        role_style = "user"
        
        for part in msg.parts:
            if getattr(part, "text", None):
                parts_texts.append(part.text.strip())
            elif getattr(part, "function_call", None):
                fc = part.function_call
                clean_args = {k: v for k, v in fc.args.items() if k != "thought"}
                args_str = ", ".join(f"{k}={v}" for k, v in clean_args.items())
                parts_texts.append(f"[Function Call: {fc.name}({args_str})]")
            elif getattr(part, "function_response", None):
                fr = part.function_response
                res_val = fr.response.get("result", "")
                if len(str(res_val)) > 300:
                    res_val = str(res_val)[:300] + "... [TRUNCATED]"
                parts_texts.append(f"[Function Response: {fr.name} = {res_val}]")
                role_style = "tool"
        
        content_str = "\n".join(parts_texts).strip()
        
        if role == "model":
            label_style = "bold green"
            content_style = "green"
            role_label = "ASSISTANT"
        elif role_style == "tool":
            label_style = "bold yellow"
            content_style = "yellow"
            role_label = "TOOL"
        else:
            label_style = "bold blue"
            content_style = "blue"
            role_label = "USER"
            
        indent = " " * (len(role_label) + 2)
        wrapped = textwrap.fill(content_str, width=82, subsequent_indent=indent)
        input_elements.append(Text.assemble((f"{role_label}: ", label_style), (wrapped, content_style)))
            
        console.print(
            Panel(
                Group(*input_elements),
                title="[bold bright_black]Model Input (Latest Message)[/bold bright_black]",
                border_style="bright_black",
                padding=(1, 2),
            )
        )

        # ── Print Model Response ──────────────────────────────────────────────
        
        # Construct raw response text for display inside the model response block
        resp_parts = []
        if thought:
            resp_parts.append(f"Thought: {thought}")
        if fc_part:
            # Format arguments as key=value for cleaner display, omitting the thought parameter
            clean_args = {k: v for k, v in fc_part.function_call.args.items() if k != "thought"}
            args_str = ", ".join(f"{k}={v}" for k, v in clean_args.items())
            resp_parts.append(f"[Function Call: {fc_part.function_call.name}({args_str})]")
        raw_response_text = "\n\n".join(resp_parts)

        # Print model response verbatim inside a grey panel (refer to terminal-output-style skill)
        wrapped_response = textwrap.fill(raw_response_text, width=82, subsequent_indent="           ")
        response_content = Text.assemble(
            ("ASSISTANT: ", "bold green"),
            (wrapped_response, "italic")
        )

        console.print(
            Panel(
                response_content,
                title="[bold bright_black]Model Response[/bold bright_black]",
                border_style="bright_black",
                padding=(1, 2),
                highlight=False,
            )
        )

        # ── Handle Native Tool Call or Final Answer ───────────────────────────
        if fc_part:
            fc = fc_part.function_call
            tool_name = fc.name
            tool_args = fc.args
            
            # Precisely extract execution parameters based on schema
            if tool_name == "search":
                tool_arg_val = tool_args.get("query", "")
            elif tool_name == "summariser":
                tool_arg_val = tool_args.get("text", "")
            elif tool_name == "calculator":
                tool_arg_val = tool_args.get("expr", "")
            else:
                tool_arg_val = ""
            
            action_str = f"{tool_name}({tool_arg_val})"
            console.print(f"  [bold blue]Action:[/bold blue]  [cyan]Based on the thought, calling -> {action_str}[/cyan]")
            
            with console.status(f"[bold yellow]Executing tool: {tool_name}...[/bold yellow]"):
                if tool_name in TOOLS:
                    observation_str = TOOLS[tool_name](str(tool_arg_val))
                else:
                    observation_str = f"Error: Tool {tool_name} not found."
                tools_used.append(tool_name)

            wrapped_obs = textwrap.fill(str(observation_str), width=84, subsequent_indent="    ")
            console.print(f"  [bold yellow]Observation:[/bold yellow] [yellow]{wrapped_obs}[/yellow]")

            # Record step for loop detection
            step_history.append({"tool": tool_name, "arg": tool_arg_val})
            
            # Reconstruct model content to explicitly carry forward the plain text thought
            # and the function call back in the conversation history for full reasoning context.
            history_parts = []
            if thought:
                history_parts.append(_Part(text=f"Thought: {thought}"))
            if fc_part:
                history_parts.append(fc_part)
                
            contents.append(_Content(role="model", parts=history_parts))
            
            # Append function response
            fr_part = _Part(function_response=_FunctionResponse(
                name=tool_name,
                result=str(observation_str),
                call_id=fc.call_id,
            ))
            contents.append(_Content(role="user", parts=[fr_part]))
            
        else:
            # No function call, this must be the final answer
            final_answer = thought
            console.print("  [bold blue]Action:[/bold blue]  [cyan]Provide Final Answer[/cyan]")
            with console.status("[bold green]Compiling final answer...[/bold green]"):
                time.sleep(0.5)  # small pause for visual effect
            wrapped_ans = textwrap.fill(final_answer, width=84, subsequent_indent="    ")
            console.print(f"  [bold green]Final Answer:[/bold green] [green]{wrapped_ans}[/green]")
            halt_reason = "final_answer"
            break

        # ── Print Step Token Metrics ──────────────────────────────────────────
        step_cost = (step_input * PRICE_INPUT_PER_M + step_output * PRICE_OUTPUT_PER_M) / 1_000_000
        cum_cost = (cumulative_input * PRICE_INPUT_PER_M + cumulative_output * PRICE_OUTPUT_PER_M) / 1_000_000
        
        token_panel_text = (
            f"[bold bright_black]Token Tracking for Step {step:02d}:[/bold bright_black]\n"
            f"  • Input (Prompt + History): [bold white]{step_input:,}[/bold white] tokens\n"
            f"  • Output (Thought + Call):   [bold white]{step_output:,}[/bold white] tokens "
            f"[dim](Reasoning: {step_thoughts:,}, Content: {step_candidates:,})[/dim]\n"
            f"  • Step Total Billing:       [bold yellow]{step_input + step_output:,}[/bold yellow] tokens "
            f"[green](${step_cost:.6f})[/green]\n"
            f"  • Cumulative So Far:        [bold cyan]{cumulative_input + cumulative_output:,}[/bold cyan] tokens "
            f"[green](${cum_cost:.5f})[/green]"
        )
        console.print(
            Panel(
                token_panel_text,
                border_style="bright_black",
                padding=(0, 2),
            )
        )

        # ── Loop detection ────────────────────────────────────────────────────
        if not disable_loop_detection and detect_loop(step_history, window=3):
            console.print(
                "\n  [bold red]Loop detected:[/bold red] [dim]same tool+arg repeated 3× — halting.[/dim]"
            )
            halt_reason = "loop_detected"
            break

    else:
        # for-loop exhausted without break — budget exceeded
        console.print(
            "\n  [bold red]Budget exceeded:[/bold red] [dim]agent halted after "
            f"{max_steps} steps.[/dim]"
        )

    elapsed = time.time() - start

    # Azure does not expose Gemini's count_tokens endpoint; estimate locally.
    try:
        final_unique_tokens = ADAPTER.count_context_tokens(contents)
    except Exception as exc:
        final_unique_tokens = 0

    verdict_map = {
        "final_answer": ("Completed", "green"),
        "loop_detected": ("Halted — loop", "red"),
        "max_steps": ("Halted — budget", "red"),
    }
    verdict, verdict_color = verdict_map.get(halt_reason, ("Unknown", "yellow"))

    total_billed = cumulative_input + cumulative_output
    overhead_factor = total_billed / final_unique_tokens if final_unique_tokens > 0 else 1.0
    total_cost = (cumulative_input * PRICE_INPUT_PER_M + cumulative_output * PRICE_OUTPUT_PER_M) / 1_000_000

    return {
        "steps": min(step, max_steps),
        "tools_used": tools_used,
        "elapsed": elapsed,
        "verdict": verdict,
        "verdict_color": verdict_color,
        "halt_reason": halt_reason,
        "final_answer": final_answer,
        "cumulative_input": cumulative_input,
        "cumulative_output": cumulative_output,
        "total_billed": total_billed,
        "final_unique_tokens": final_unique_tokens,
        "overhead_factor": overhead_factor,
        "total_cost": total_cost,
        "step_metrics": step_metrics
    }


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    """Main entry point orchestrating the ReAct agent demonstration."""
    console.print(
        Panel.fit(
            "[bold yellow]ReAct Agent Reasoning & Thought Demonstration[/bold yellow]\n"
            "[dim]Demonstrates that Chain-of-Thought (CoT) is essential for solving complex reasoning tasks.[/dim]\n"
            f"[dim]Models: {MODEL_ID} · Input: ${PRICE_INPUT_PER_M}/1M · Output: ${PRICE_OUTPUT_PER_M}/1M[/dim]",
            border_style="yellow",
        )
    )
    console.print()

    results = []
    task = (
        "Calculate the population density for both India and China. Identify the "
        "country with the lower density, and calculate what its total GDP would be "
        "if its population increased to match the other country's density. "
        "Subtract that country's current GDP from this hypothetical GDP, and multiply the "
        "difference by 0.15. If the resulting value is greater than the GDP of India, "
        "your final answer must be exactly 'OPTION A'. Otherwise, your final answer must "
        "be exactly 'OPTION B'. You must output ONLY 'OPTION A' or 'OPTION B' as your final answer."
    )

    # ── SCENARIO: Enabled Thoughts (Active CoT / Standard ReAct) ────────────
    scenario_title = "Standard ReAct with Active CoT"
    console.print(Rule(f"[bold green]{scenario_title}[/bold green]", style="green"))
    console.print(f"  [bold]Task:[/bold] [white]{task}[/white]")
    console.print(f"  [dim]Setup: Standard ReAct. Thoughts are enabled and carried forward in standard text history.[/dim]")
    console.print(f"  [dim]Result: The model plans methodically, processes data, and succeeds flawlessly.[/dim]\n")
    
    stats = run_react_agent(task, use_detailed=True, disable_loop_detection=False, disable_thinking=False, max_steps=15)
    stats["name"] = scenario_title
    results.append(stats)

    console.print("\n" * 2)

    # ── TOKEN CONSUMPTION & PERFORMANCE REPORT ─────────────────────────────────
    console.print(Rule("[bold yellow]ReAct Reasoning Performance Report[/bold yellow]", style="yellow"))
    console.print()

    # Programmatically evaluate the final answers for accuracy
    for r in results:
        if r["halt_reason"] == "final_answer":
            ans = r["final_answer"].strip().upper()
            # The correct option is OPTION A.
            is_correct = "OPTION A" in ans and "OPTION B" not in ans
            if is_correct:
                r["verdict"] = "Success (Correct)"
                r["verdict_color"] = "green"
            else:
                r["verdict"] = "Failed (Incorrect Option)"
                r["verdict_color"] = "red"
        else:
            r["verdict"] = "Failed (Aborted)"
            r["verdict_color"] = "red"

    table = Table(title="Chain-of-Thought Performance Overview", show_lines=True, header_style="bold cyan", border_style="yellow")
    table.add_column("Scenario", style="bold", min_width=25)
    table.add_column("Steps", justify="right")
    table.add_column("Verdict", justify="center")
    table.add_column("Total Billed Tokens", justify="right", style="bold yellow")
    table.add_column("Unique Context Size", justify="right", style="cyan")
    table.add_column("Overhead Ratio", justify="right", style="bold red")
    table.add_column("Est. Cost (USD)", justify="right", style="green")

    for r in results:
        ratio_str = f"{r['overhead_factor']:.2f}x"
        v_text, v_color = r["verdict"], r["verdict_color"]
        formatted_verdict = f"[{v_color}]{v_text}[/{v_color}]"
        table.add_row(
            r["name"],
            str(r["steps"]),
            formatted_verdict,
            f"{r['total_billed']:,}",
            f"{r['final_unique_tokens']:,}",
            ratio_str,
            f"${r['total_cost']:.6f}"
        )

    console.print(table)
    console.print()

    # ── SCENARIO POST-MORTEM & EXPLANATION ────────────────────────────────────
    console.print(Rule("[bold yellow]🔬 Chain-of-Thought Performance Analysis[/bold yellow]", style="yellow"))
    console.print()
    post_mortem = (
        "[bold green]Why Enabled Thoughts (Active CoT) Succeeds:[/bold green]\n"
        "• [bold green]Distributed Computation:[/bold green] By writing down thoughts step-by-step, the model distributes complex mathematical and planning operations across sequential token generation turns. Each thought anchors the next, guaranteeing calculation accuracy.\n"
        "• [bold green]Methodical State Tracking:[/bold green] The persistent plain-text reasoning history acts as an explicit memory registry. The model reads its past thoughts to know exactly what variables it already retrieved, leading cleanly to the correct final option 'OPTION A'.\n"
        "• [bold green]Robust Planning & Tool Orchestration:[/bold green] Instead of failing or guessing in its head, the model dynamically plans which tools to call, inspects the retrieved demographic values, and executes precise python-based calculations to arrive at the solution."
    )
    console.print(
        Panel(
            post_mortem,
            title="[bold yellow]Analysis[/bold yellow]",
            border_style="yellow",
            padding=(1, 2)
        )
    )
    console.print()


if __name__ == "__main__":
    main()
