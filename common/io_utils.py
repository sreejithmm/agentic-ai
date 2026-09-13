"""Reusable Rich terminal presentation helpers for agent prototypes."""

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


class RichIO:
    """Render consistent agent prompts, responses, and session summaries."""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()

    def ask(self, label: str = "You") -> str:
        """Prompt the user with a styled input label."""
        return Prompt.ask(f"[bold cyan]{label}[/bold cyan]")

    def emit(self, value: object) -> None:
        """Print a Rich renderable or plain value to the terminal."""
        self.console.print(value)

    def show_header(self, title: str, subtitle: str) -> None:
        """Display the agent title and a short description."""
        self.emit(
            Panel(
                subtitle,
                title=f"[bold cyan]{title}[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
            )
        )

    def show_response(self, response: str, label: str = "Agent") -> None:
        """Display an agent response in a bordered panel."""
        self.emit(
            Panel(
                response,
                title=f"[bold green]{label}[/bold green]",
                border_style="green",
                padding=(1, 2),
            )
        )

    def show_usage(
        self,
        input_tokens: int,
        output_tokens: int,
        estimated_cost: float,
    ) -> None:
        """Display token totals and estimated session cost."""
        total_tokens = input_tokens + output_tokens
        self.emit(
            Panel(
                f"Input tokens   {input_tokens:,}\n"
                f"Output tokens  {output_tokens:,}\n"
                f"Total tokens   {total_tokens:,}\n"
                f"Approx. cost   ${estimated_cost:.6f}",
                title="[bold yellow]Conversation Usage[/bold yellow]",
                border_style="yellow",
                padding=(1, 2),
            )
        )

    def show_empty_question(self) -> None:
        """Tell the user that a question is required."""
        self.emit("[dim]Please enter a question.[/dim]")

    def show_closed(self) -> None:
        """Display the end-of-session message."""
        self.emit("[dim]Session closed.[/dim]")
