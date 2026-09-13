"""A small, knowledge-base-grounded customer support chatbot."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from common.azure_openai_client import AzureResponsesAdapter
from common.io_utils import RichIO


KNOWLEDGE_BASE = """
Drishyam (Malayalam, 2013) is a crime thriller directed by Jeethu Joseph.
The film stars Mohanlal as Georgekutty, Meena as Rani, Ansiba Hassan as Anju,
and Esther Anil as Anu. Georgekutty is a self-educated cable-TV operator and
film enthusiast who lives with Rani and their two daughters in a small town in
Kerala.

The central conflict begins when Varun, the son of the Inspector General of
Police, visits the family home and dies during a confrontation with Anju.
Fearing that the family will be blamed, Georgekutty creates a false timeline
and coaches his family to follow it. He uses details learned from films and
careful planning to make the family appear to have been away from home.

The police investigation is led by Geetha Prabhakar, Varun's mother, and her
husband Prabhakar. The investigation puts pressure on Georgekutty's family,
but his plan and the family's discipline make it difficult for the police to
prove what happened. The film focuses on family, fear, deception, and the
limits of circumstantial evidence. It is a fictional story; this summary does
not include every scene or detail from the film.
""".strip()

EXIT_COMMANDS = {"exit", "quit", "q"}
WEB_SEARCH_TOOLS = [{"type": "web_search_preview"}]
PRICE_INPUT_PER_M = 0.075
PRICE_OUTPUT_PER_M = 0.30


@dataclass
class Usage:
    """Token totals for the current chatbot conversation."""

    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    @property
    def estimated_cost(self) -> float:
        return (
            self.input_tokens * PRICE_INPUT_PER_M
            + self.output_tokens * PRICE_OUTPUT_PER_M
        ) / 1_000_000


def build_prompt(
    question: str,
    conversation: Sequence[tuple[str, str]] = (),
) -> str:
    """Create a grounded prompt containing the earlier conversation turns."""
    history = "\n\n".join(
        f"CUSTOMER: {past_question}\nAGENT: {past_answer}"
        for past_question, past_answer in conversation
    )
    conversation_section = (
        f"\nCONVERSATION HISTORY:\n{history}\n" if history else ""
    )
    return f"""You are a customer support agent for a Drishyam movie information service.
Use the knowledge base below as your baseline source.
Decide whether web search is needed for the customer's question.
Use the web search tool only when the local knowledge base does not contain
the answer or when the question asks for current information. For questions
fully answered by the local knowledge base, answer directly without searching.
When you search, prefer reliable sources and do not invent details.
Do not answer or search any questions other than about movie drishyam.
If the answer is not in the knowledge base, say: "I don't have that information
in my knowledge base."
Keep the answer concise and mention when the question is outside this summary.

KNOWLEDGE BASE:
{KNOWLEDGE_BASE}
{conversation_section}

CUSTOMER QUESTION:
{question}
"""


def answer_question(
    question: str,
    adapter: AzureResponsesAdapter,
    conversation: Sequence[tuple[str, str]] = (),
) -> tuple[str, int, int]:
    """Answer one question and return its input and output token counts."""
    return adapter.summarize_with_usage(
        build_prompt(question, conversation),
        tools=WEB_SEARCH_TOOLS,
    )


def run_chat(
    adapter: AzureResponsesAdapter,
    input_fn: Callable[[str], str] | None = None,
    output_fn: Callable[[object], None] | None = None,
    display: RichIO | None = None,
) -> None:
    """Read customer questions until the customer asks to exit."""
    conversation: list[tuple[str, str]] = []
    usage = Usage()
    rich_display = display is not None
    ask = input_fn or (
        display.ask
        if rich_display
        else input
    )
    emit = output_fn or (display.emit if display else print)

    if rich_display:
        display.show_header(
            "Film Support Agent",
            "Ask about the Malayalam film [bold]Drishyam[/bold].\n"
            "The agent uses its local knowledge base and decides when web "
            "search is needed.",
        )
    else:
        emit("Film support agent ready. Ask a question, or type 'exit'.")

    while True:
        question = ask("You: ").strip()
        if question.lower() in EXIT_COMMANDS:
            if rich_display:
                display.show_usage(
                    usage.input_tokens,
                    usage.output_tokens,
                    usage.estimated_cost,
                )
                display.show_closed()
            else:
                emit(
                    "Conversation usage: "
                    f"{usage.input_tokens:,} input + "
                    f"{usage.output_tokens:,} output = "
                    f"{usage.total_tokens:,} total tokens; "
                    f"approx. ${usage.estimated_cost:.6f}"
                )
                emit("Goodbye!")
            return
        if not question:
            display.show_empty_question() if rich_display else emit(
                "Please enter a question."
            )
            continue

        answer, input_tokens, output_tokens = answer_question(
            question, adapter, conversation
        )
        usage.input_tokens += input_tokens
        usage.output_tokens += output_tokens
        conversation.append((question, answer))
        if rich_display:
            display.show_response(answer)
        else:
            emit(f"Agent: {answer}")


def main() -> None:
    """Configure Azure OpenAI and run the support conversation."""
    adapter = AzureResponsesAdapter()
    run_chat(adapter, display=RichIO())


if __name__ == "__main__":
    main()
