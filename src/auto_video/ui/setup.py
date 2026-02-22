"""Setup wizard UI for LLM configuration."""

from dataclasses import dataclass

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from auto_video.config.schema import LLMProviderConfig


@dataclass
class LLMSetupResult:
    """Result of LLM setup wizard."""

    config: LLMProviderConfig | None
    success: bool
    message: str


class LLMSetupWizard:
    """Wizard for setting up LLM provider."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize wizard.

        Args:
            console: Rich console instance. If None, creates a new one.
        """
        self.console = console or Console()

    def run(self) -> LLMSetupResult:
        """Run the LLM setup wizard.

        Returns:
            Setup result with configuration.
        """
        self._show_welcome()

        mode = self._select_mode()

        if mode == "api":
            config = self._setup_api_provider()
        elif mode == "local":
            config = self._setup_local_provider()
        else:
            config = self._setup_hybrid_provider()

        if not config:
            return LLMSetupResult(config=None, success=False, message="Setup cancelled")

        self._show_summary(config)

        if self._test_connection(config):
            return LLMSetupResult(
                config=config, success=True, message="LLM configured successfully"
            )

        return LLMSetupResult(
            config=config,
            success=False,
            message="Connection test failed. Configuration saved but verify settings.",
        )

    def _show_welcome(self) -> None:
        """Display welcome screen."""
        self.console.print(
            Panel.fit(
                "[bold blue]LLM Configuration Wizard[/bold blue]\n\n"
                "This wizard will help you configure the LLM provider for "
                "video script generation.",
                title="Auto-Video Setup",
            )
        )
        self.console.print()

    def _select_mode(self) -> str:
        """Select LLM mode (API/Local/Hybrid).

        Returns:
            Selected mode.
        """
        self.console.print("[bold]Select LLM Mode:[/bold]")
        self.console.print()

        choices = ["1. API (OpenAI, Anthropic, Groq, Google)", "2. Local (Ollama)", "3. Hybrid"]

        for choice in choices:
            self.console.print(f"  {choice}")

        while True:
            self.console.print()
            selection = Prompt.ask(
                "Select mode",
                choices=["1", "2", "3"],
                default="1",
            )

            if selection == "1":
                return "api"
            elif selection == "2":
                return "local"
            else:
                return "hybrid"

    def _setup_api_provider(self) -> LLMProviderConfig | None:
        """Setup API-based LLM provider.

        Returns:
            LLM provider configuration or None if cancelled.
        """
        provider = self._select_api_provider()
        if not provider:
            return None

        model = self._select_model(provider)
        if not model:
            return None

        api_key = self._get_api_key(provider)
        if not api_key:
            return None

        temperature = self._get_temperature()

        return LLMProviderConfig(
            provider=provider, model=model, api_key=api_key, temperature=temperature
        )

    def _setup_local_provider(self) -> LLMProviderConfig | None:
        """Setup local LLM provider.

        Returns:
            LLM provider configuration or None if cancelled.
        """
        host = Prompt.ask("Ollama host", default="http://localhost:11434")

        model = Prompt.ask("Ollama model name", default="llama3.2")

        temperature = self._get_temperature()

        return LLMProviderConfig(provider="ollama", model=model, host=host, temperature=temperature)

    def _setup_hybrid_provider(self) -> LLMProviderConfig | None:
        """Setup hybrid LLM provider.

        Returns:
            LLM provider configuration or None if cancelled.
        """
        self.console.print(
            "[yellow]Hybrid mode: Uses API by default, falls back to local.[/yellow]"
        )
        self.console.print()

        api_config = self._setup_api_provider()
        if not api_config:
            return None

        local_host = Prompt.ask("Local Ollama host", default="http://localhost:11434")

        return LLMProviderConfig(
            provider=api_config.provider,
            model=api_config.model,
            api_key=api_config.api_key,
            host=local_host,
            temperature=api_config.temperature,
        )

    def _select_api_provider(self) -> str | None:
        """Select API provider.

        Returns:
            Provider name or None if cancelled.
        """
        providers = [
            ("openai", "OpenAI (GPT-4, GPT-3.5)"),
            ("anthropic", "Anthropic (Claude 3)"),
            ("groq", "Groq (Fast Llama API)"),
            ("google", "Google (Gemini)"),
        ]

        table = Table(title="Available API Providers")
        table.add_column("ID", style="cyan")
        table.add_column("Provider", style="green")
        table.add_column("Models", style="yellow")

        for idx, (name, desc) in enumerate(providers, 1):
            table.add_row(str(idx), name, desc)

        self.console.print(table)

        choices = [str(i) for i in range(1, len(providers) + 1)]
        selection = Prompt.ask("Select provider", choices=choices, default="1")

        idx = int(selection) - 1
        return providers[idx][0]

    def _select_model(self, provider: str) -> str | None:
        """Select model for provider.

        Args:
            provider: Provider name.

        Returns:
            Model name or None if cancelled.
        """
        models = {
            "openai": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
            "anthropic": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
            "groq": ["llama3.1-70b", "mixtral-8x7b", "gemma-7b"],
            "google": ["gemini-1.5-pro", "gemini-1.5-flash"],
        }

        provider_models = models.get(provider, [])
        if not provider_models:
            return Prompt.ask("Enter model name")

        self.console.print(f"[bold]Available models for {provider}:[/bold]")
        for idx, model in enumerate(provider_models, 1):
            self.console.print(f"  {idx}. {model}")

        choices = [str(i) for i in range(1, len(provider_models) + 1)]
        selection = Prompt.ask("Select model", choices=choices, default="1")

        idx = int(selection) - 1
        return provider_models[idx]

    def _get_api_key(self, provider: str) -> str | None:
        """Get API key from user.

        Args:
            provider: Provider name.

        Returns:
            API key or None if cancelled.
        """
        if not Confirm.ask(
            f"Do you want to enter an API key for {provider} now?",
            default=True,
        ):
            return None

        self.console.print("[yellow]API key will be stored in plain text in config file.[/yellow]")

        key = Prompt.ask(
            f"Enter {provider} API key",
            password=True,
        )

        if not key:
            self.console.print("[red]API key cannot be empty[/red]")
            return None

        return key

    def _get_temperature(self) -> float:
        """Get temperature setting.

        Returns:
            Temperature value (0.0-2.0).
        """
        self.console.print(
            "[dim]Temperature controls randomness (0.0 = more focused, 2.0 = more creative)[/dim]"
        )

        while True:
            temp = Prompt.ask(
                "Temperature",
                default="0.7",
            )

            try:
                temp_val = float(temp)
                if 0.0 <= temp_val <= 2.0:
                    return temp_val
                self.console.print("[red]Temperature must be between 0.0 and 2.0[/red]")
            except ValueError:
                self.console.print("[red]Invalid number[/red]")

    def _show_summary(self, config: LLMProviderConfig) -> None:
        """Display configuration summary.

        Args:
            config: LLM provider configuration.
        """
        self.console.print()
        self.console.print(
            Panel(
                f"[bold]Provider:[/bold] {config.provider}\n"
                f"[bold]Model:[/bold] {config.model}\n"
                f"[bold]Temperature:[/bold] {config.temperature}\n"
                f"[bold]API Key:[/bold] {'***' if config.api_key else 'None'}\n"
                f"[bold]Host:[/bold] {config.host or 'N/A'}",
                title="[green]Configuration Summary[/green]",
            )
        )

    def _test_connection(self, config: LLMProviderConfig) -> bool:
        """Test LLM connection.

        Args:
            config: LLM provider configuration.

        Returns:
            True if connection successful, False otherwise.
        """
        if not Confirm.ask(
            "Do you want to test the connection now?",
            default=True,
        ):
            return True

        self.console.print()
        self.console.print("[cyan]Testing connection...[/cyan]")

        try:
            from auto_video.core.llm import LLM

            llm = LLM(config)
            test_prompt = "Say 'test'"
            response = llm.generate(test_prompt)

            if response:
                self.console.print("[green]✓ Connection successful![/green]")
                self.console.print(f"[dim]Response: {response[:100]}...[/dim]")
                return True
        except ImportError:
            self.console.print(
                "[yellow]LLM module not available - skipping connection test[/yellow]"
            )
            return Confirm.ask("Continue anyway?", default=True)
        except Exception as e:
            self.console.print(f"[red]✗ Connection failed:[/red] {e}")

        return Confirm.ask("Continue anyway?", default=False)
