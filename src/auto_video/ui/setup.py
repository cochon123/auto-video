"""Setup wizard UI for LLM configuration."""

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from auto_video.config.loader import get_default_config_path, save_config
from auto_video.config.schema import (
    AppConfig,
    ImageGenConfig,
    LLMProviderConfig,
    StorageConfig,
    TTSConfig,
    VisualsConfig,
    YouTubeConfig,
)

PrivacyType = Literal["public", "unlisted", "private"]


def _get_api_key(console: Console, provider: str) -> str | None:
    """Get API key from user.

    Args:
        console: Rich console for user interaction.
        provider: Provider name.

    Returns:
        API key or None if cancelled.
    """
    if not Confirm.ask(
        f"Do you want to enter an API key for {provider} now?",
        default=True,
        console=console,
    ):
        return None

    console.print("[yellow]API key will be stored in plain text in config file.[/yellow]")

    key = Prompt.ask(
        f"Enter {provider} API key",
        password=True,
        console=console,
    )

    if not key:
        console.print("[red]API key cannot be empty[/red]")
        return None

    return key


@dataclass
class LLMSetupResult:
    """Result of LLM setup wizard."""

    config: LLMProviderConfig | None
    success: bool
    message: str


@dataclass
class StorageSetupResult:
    """Result of storage setup wizard."""

    config: StorageConfig | None
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

        api_key = _get_api_key(self.console, provider)
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

        available_models = self._get_ollama_models(host)

        if available_models:
            self.console.print("[bold]Available models on Ollama:[/bold]")
            for idx, model in enumerate(available_models, 1):
                self.console.print(f"  {idx}. {model}")

            choices = [str(i) for i in range(1, len(available_models) + 1)]
            selection = Prompt.ask("Select model", choices=choices, default="1")
            model = available_models[int(selection) - 1]
        else:
            self.console.print("[yellow]Could not fetch models from Ollama.[/yellow]")
            model = Prompt.ask("Ollama model name", default="llama3.2")

        temperature = self._get_temperature()

        return LLMProviderConfig(provider="ollama", model=model, host=host, temperature=temperature)

    def _get_ollama_models(self, host: str) -> list[str]:
        """Get available models from Ollama.

        Args:
            host: Ollama host URL.

        Returns:
            List of available model names.
        """
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{host.rstrip('/')}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    result = []
                    for m in models:
                        name = m.get("name", "")
                        if name:
                            model_name = name.split(":")[0]
                            if "/" in model_name:
                                model_name = model_name.split("/")[-1]
                            result.append(model_name)
                    return result
        except Exception:
            pass
        return []

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

        available_models = self._get_ollama_models(local_host)

        if available_models:
            self.console.print("[bold]Available models on Ollama:[/bold]")
            for idx, model in enumerate(available_models, 1):
                self.console.print(f"  {idx}. {model}")

            choices = [str(i) for i in range(1, len(available_models) + 1)]
            selection = Prompt.ask("Select model", choices=choices, default="1")
            model = available_models[int(selection) - 1]
        else:
            self.console.print("[yellow]Could not fetch models from Ollama.[/yellow]")
            model = Prompt.ask("Ollama model name", default="llama3.2")

        return LLMProviderConfig(
            provider="ollama",
            model=model,
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
            ("zhipuai", "Zhipu AI (z.ai)"),
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
            "google": ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-pro"],
            "zhipuai": ["glm-4.5", "glm-4-flash", "glm-4-long", "glm-z1-air"],
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
            response = llm.provider.generate(test_prompt)

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


class StorageSetupWizard:
    """Wizard for setting up storage configuration."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize wizard.

        Args:
            console: Rich console instance. If None, creates a new one.
        """
        self.console = console or Console()

    def run(self) -> StorageSetupResult:
        """Run storage setup wizard.

        Returns:
            Setup result with configuration.
        """
        self._show_welcome()

        save_videos = self._ask_save_videos()

        if save_videos:
            videos_path = self._ask_videos_path()
        else:
            videos_path = None

        keep_temp = self._ask_keep_temp()
        temp_path = self._ask_temp_path()

        config = self._validate_and_create_config(videos_path, temp_path, keep_temp)

        if not config:
            return StorageSetupResult(config=None, success=False, message="Setup cancelled")

        self._show_summary(config)
        return StorageSetupResult(
            config=config,
            success=True,
            message="Storage configured successfully",
        )

    def _show_welcome(self) -> None:
        """Display welcome screen."""
        self.console.print(
            Panel.fit(
                "[bold blue]Storage Configuration Wizard[/bold blue]\n\n"
                "This wizard will help you configure where to store your "
                "generated videos and temporary files.",
                title="Auto-Video Setup",
            )
        )
        self.console.print()

    def _ask_save_videos(self) -> bool:
        """Ask whether to save generated videos.

        Returns:
            True if user wants to save videos, False otherwise.
        """
        return Confirm.ask(
            "Do you want to save generated videos to disk?",
            default=True,
        )

    def _ask_videos_path(self) -> Path:
        """Ask for videos storage path.

        Returns:
            Path for video storage.
        """
        default = Path.home() / "Videos" / "auto-videos"
        self.console.print(f"[dim]Default: {default}[/dim]")

        path_str = Prompt.ask(
            "Enter path for storing videos",
            default=str(default),
        )

        path = Path(path_str).expanduser()

        self._create_directory_if_needed(path, "Videos")

        return path

    def _ask_keep_temp(self) -> bool:
        """Ask whether to keep temporary files.

        Returns:
            True if user wants to keep temp files, False otherwise.
        """
        self.console.print(
            "[dim]Temporary files include audio, scripts, and intermediate video files.[/dim]"
        )
        return Confirm.ask(
            "Do you want to keep temporary files after generation?",
            default=False,
        )

    def _ask_temp_path(self) -> Path:
        """Ask for temporary files path.

        Returns:
            Path for temporary files.
        """
        default = Path.home() / ".cache" / "auto-video" / "temp"
        self.console.print(f"[dim]Default: {default}[/dim]")

        path_str = Prompt.ask(
            "Enter path for temporary files",
            default=str(default),
        )

        path = Path(path_str).expanduser()

        self._create_directory_if_needed(path, "Temporary files")

        return path

    def _create_directory_if_needed(self, path: Path, description: str) -> None:
        """Create directory if it doesn't exist.

        Args:
            path: Path to create.
            description: Description of the directory (for messages).
        """
        if path.exists():
            if path.is_dir():
                self.console.print(f"[green]✓ {description} directory already exists[/green]")
                return

            self.console.print(f"[red]✗ Path exists but is not a directory: {path}[/red]")
            raise ValueError(f"Path is not a directory: {path}")

        try:
            path.mkdir(parents=True, exist_ok=True)
            self.console.print(f"[green]✓ Created {description} directory[/green]")
        except Exception as e:
            self.console.print(f"[red]✗ Failed to create directory: {e}[/red]")
            raise

    def _validate_and_create_config(
        self, videos_path: Path | None, temp_path: Path, keep_temp: bool
    ) -> StorageConfig | None:
        """Validate and create storage configuration.

        Args:
            videos_path: Path for videos storage (optional).
            temp_path: Path for temporary files.
            keep_temp: Whether to keep temporary files.

        Returns:
            Storage configuration or None if validation fails.
        """
        if videos_path is None:
            videos_path = Path.home() / "Videos" / "auto-videos"

        try:
            return StorageConfig(videos_path=videos_path, temp_path=temp_path, keep_temp=keep_temp)
        except Exception as e:
            self.console.print(f"[red]✗ Configuration error: {e}[/red]")
            return None

    def _show_summary(self, config: StorageConfig) -> None:
        """Display configuration summary.

        Args:
            config: Storage configuration.
        """
        self.console.print()
        self.console.print(
            Panel(
                f"[bold]Videos Path:[/bold] {config.videos_path}\n"
                f"[bold]Temp Path:[/bold] {config.temp_path}\n"
                f"[bold]Keep Temp Files:[/bold] {config.keep_temp}",
                title="[green]Storage Configuration Summary[/green]",
            )
        )


@dataclass
class VisualsSetupResult:
    """Result of visuals setup wizard."""

    config: VisualsConfig | None
    success: bool
    message: str


@dataclass
class TTSImageSetupResult:
    """Result of TTS and Images setup wizard."""

    tts_config: TTSConfig | None
    image_config: ImageGenConfig | None
    success: bool
    message: str


class VisualsSetupWizard:
    """Wizard for setting up visuals configuration."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize wizard.

        Args:
            console: Rich console instance. If None, creates a new one.
        """
        self.console = console or Console()

    def run(self) -> VisualsSetupResult:
        """Run visuals setup wizard.

        Returns:
            Setup result with configuration.
        """
        self._show_welcome()

        mode = self._select_mode()

        if mode == "stock":
            config = self._setup_stock_api()
        elif mode == "local":
            config = self._setup_local()
        elif mode == "generated":
            self.console.print(
                "[yellow]Generated visuals will be configured in "
                "Step 1.7 (TTS + Images wizard)[/yellow]"
            )
            config = VisualsConfig(mode="generated")
        else:
            config = self._setup_hybrid()

        if not config:
            return VisualsSetupResult(config=None, success=False, message="Setup cancelled")

        self._show_summary(config)
        return VisualsSetupResult(
            config=config, success=True, message="Visuals configured successfully"
        )

    def _show_welcome(self) -> None:
        """Display welcome screen."""
        self.console.print(
            Panel.fit(
                "[bold blue]Visuals Configuration Wizard[/bold blue]\n\n"
                "This wizard will help you configure the source of "
                "visuals for your videos (stock footage, local assets, "
                "or AI-generated images).",
                title="Auto-Video Setup",
            )
        )
        self.console.print()

    def _select_mode(self) -> str:
        """Select visuals mode.

        Returns:
            Selected mode.
        """
        self.console.print("[bold]Select Visuals Mode:[/bold]")
        self.console.print()

        choices = [
            "1. Stock Footage API (Pexels, Pixabay)",
            "2. Local Assets (your video/image folders)",
            "3. AI Generated Images",
            "4. Hybrid (combine multiple sources)",
        ]

        for choice in choices:
            self.console.print(f"  {choice}")

        while True:
            self.console.print()
            selection = Prompt.ask(
                "Select mode",
                choices=["1", "2", "3", "4"],
                default="1",
            )

            if selection == "1":
                return "stock"
            elif selection == "2":
                return "local"
            elif selection == "3":
                return "generated"
            else:
                return "hybrid"

    def _setup_stock_api(self) -> VisualsConfig | None:
        """Setup stock footage API providers.

        Returns:
            Visuals configuration or None if cancelled.
        """
        self.console.print("[bold]Configure Stock Footage Providers[/bold]")
        self.console.print()

        providers = []

        pexels = self._setup_pexels()
        if pexels:
            providers.append(pexels)

        pixabay = self._setup_pixabay()
        if pixabay:
            providers.append(pixabay)

        if not providers:
            return None

        visual_llm = self._setup_visual_llm()

        return VisualsConfig(
            mode="stock",
            providers=providers,
            visual_llm=visual_llm,
            pexels_api_key=self._get_api_key("pexels"),
            pixabay_api_key=self._get_api_key("pixabay"),
        )

    def _setup_visual_llm(self) -> LLMProviderConfig | None:
        """Setup visual LLM for segment-based keyword extraction.

        Returns:
            LLM configuration for visual keyword extraction, or None if not configured.
        """
        self.console.print()
        if not Confirm.ask(
            "Use AI to generate specific keywords for each video segment?\n"
            "  (This improves clip-to-script matching but uses more API calls)",
            default=False,
        ):
            return None

        self.console.print("\n[bold]Configure Visual Keyword Extractor:[/bold]")
        self.console.print(
            "  You can use a different (smaller/faster) LLM for keyword extraction.\n"
            "  This is optional - if not set, global keywords will be used."
        )

        providers = [
            ("openai", "OpenAI (GPT-4o Mini - fast & cheap)"),
            ("anthropic", "Anthropic (Claude 3 Haiku)"),
            ("groq", "Groq (Very fast)"),
            ("google", "Google (Gemini 2.0 Flash)"),
            ("ollama", "Ollama (Local - no API cost)"),
            ("zhipuai", "Zhipu AI (z.ai - Chinese models)"),
        ]

        table = Table(title="Visual LLM Providers")
        table.add_column("ID", style="cyan")
        table.add_column("Provider", style="green")
        table.add_column("Notes", style="yellow")

        for idx, (name, desc) in enumerate(providers, 1):
            table.add_row(str(idx), name, desc)

        self.console.print(table)

        choices = [str(i) for i in range(1, len(providers) + 1)]
        selection = Prompt.ask(
            "Select provider for visual keywords",
            choices=choices,
            default="1",
        )

        provider_name = providers[int(selection) - 1][0]

        if provider_name == "ollama":
            host = Prompt.ask("Ollama host", default="http://localhost:11434")
            available_models = self._get_ollama_models(host)
            if available_models:
                self.console.print("[bold]Available models:[/bold]")
                for idx, model in enumerate(available_models, 1):
                    self.console.print(f"  {idx}. {model}")
                choices = [str(i) for i in range(1, len(available_models) + 1)]
                selection = Prompt.ask("Select model", choices=choices, default="1")
                model = available_models[int(selection) - 1]
            else:
                model = Prompt.ask("Ollama model name", default="llama3.2")

            return LLMProviderConfig(
                provider=provider_name,
                model=model,
                host=host,
                temperature=0.5,
            )

        api_key = Prompt.ask(
            f"Enter {provider_name} API key",
            password=True,
        )

        if not api_key:
            self.console.print("[yellow]No API key provided, skipping visual LLM[/yellow]")
            return None

        default_models = {
            "openai": "gpt-4o-mini",
            "anthropic": "claude-3-haiku-20240307",
            "groq": "llama-3.1-8b-instant",
            "google": "gemini-2.0-flash-exp",
            "zhipuai": "glm-4-flash",
        }
        model = Prompt.ask(
            "Model name",
            default=default_models.get(provider_name, "default"),
        )

        return LLMProviderConfig(
            provider=provider_name,
            model=model,
            api_key=api_key,
            temperature=0.5,
        )

    def _get_ollama_models(self, host: str) -> list[str]:
        """Get available models from Ollama.

        Args:
            host: Ollama host URL.

        Returns:
            List of available model names.
        """
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{host.rstrip('/')}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = data.get("models", [])
                    result = []
                    for m in models:
                        name = m.get("name", "")
                        if name:
                            model_name = name.split(":")[0]
                            if "/" in model_name:
                                model_name = model_name.split("/")[-1]
                            result.append(model_name)
                    return result
        except Exception:
            pass
        return []

    def _get_api_key(self, provider: str) -> str | None:
        """Get stored API key for a provider."""
        try:
            from auto_video.config.loader import get_default_config_path, load_config

            config = load_config(get_default_config_path())
            if provider == "pexels":
                return config.visuals.pexels_api_key
            elif provider == "pixabay":
                return config.visuals.pixabay_api_key
        except Exception:
            pass
        return None

    def _setup_pexels(self) -> str | None:
        """Setup Pexels provider.

        Returns:
            Provider name if enabled, None otherwise.
        """
        if not Confirm.ask(
            "Enable Pexels (free stock footage)?",
            default=True,
        ):
            return None

        api_key = Prompt.ask(
            "Enter Pexels API key",
            password=True,
        )

        if not api_key:
            self.console.print("[red]API key cannot be empty[/red]")
            return None

        return "pexels"

    def _setup_pixabay(self) -> str | None:
        """Setup Pixabay provider.

        Returns:
            Provider name if enabled, None otherwise.
        """
        if not Confirm.ask(
            "Enable Pixabay (free stock footage)?",
            default=True,
        ):
            return None

        api_key = Prompt.ask(
            "Enter Pixabay API key",
            password=True,
        )

        if not api_key:
            self.console.print("[red]API key cannot be empty[/red]")
            return None

        return "pixabay"

    def _setup_local(self) -> VisualsConfig | None:
        """Setup local assets.

        Returns:
            Visuals configuration or None if cancelled.
        """
        path_str = Prompt.ask(
            "Enter path to your local assets folder",
            default=str(Path.home() / "Videos" / "assets"),
        )

        path = Path(path_str).expanduser()

        if not path.exists():
            self.console.print(f"[red]✗ Path does not exist: {path}[/red]")
            if not Confirm.ask("Continue anyway?", default=False):
                return None

        if path.exists() and not path.is_dir():
            self.console.print(f"[red]✗ Path is not a directory: {path}[/red]")
            return None

        return VisualsConfig(mode="local", local_path=str(path))

    def _setup_hybrid(self) -> VisualsConfig | None:
        """Setup hybrid mode (combine sources).

        Returns:
            Visuals configuration or None if cancelled.
        """
        self.console.print(
            "[yellow]Hybrid mode: Combine stock footage, local assets, "
            "and generated images[/yellow]"
        )
        self.console.print()

        stock_config = self._setup_stock_api()
        local_config = self._setup_local()

        providers = []
        local_path = None
        visual_llm = None

        if stock_config:
            providers = stock_config.providers or []
            visual_llm = stock_config.visual_llm

        if local_config:
            local_path = local_config.local_path

        if not providers and not local_path:
            self.console.print("[red]✗ At least one source must be configured[/red]")
            return None

        return VisualsConfig(
            mode="hybrid",
            providers=providers,
            local_path=local_path,
            visual_llm=visual_llm,
            pexels_api_key=self._get_api_key("pexels"),
            pixabay_api_key=self._get_api_key("pixabay"),
        )

    def _show_summary(self, config: VisualsConfig) -> None:
        """Display configuration summary.

        Args:
            config: Visuals configuration.
        """
        self.console.print()
        providers_str = ", ".join(config.providers) if config.providers else "None"
        self.console.print(
            Panel(
                f"[bold]Mode:[/bold] {config.mode}\n"
                f"[bold]Providers:[/bold] {providers_str}\n"
                f"[bold]Local Path:[/bold] {config.local_path or 'N/A'}",
                title="[green]Visuals Configuration Summary[/green]",
            )
        )


class TTSImageSetupWizard:
    """Wizard for setting up TTS and Image generation."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize wizard.

        Args:
            console: Rich console instance. If None, creates a new one.
        """
        self.console = console or Console()

    def run(self) -> TTSImageSetupResult:
        """Run TTS and Image generation setup wizard.

        Returns:
            Setup result with configurations.
        """
        self._show_welcome()

        tts_config = self._setup_tts()
        if not tts_config:
            return TTSImageSetupResult(
                tts_config=None,
                image_config=None,
                success=False,
                message="Setup cancelled",
            )

        image_config = self._setup_image_gen()

        if image_config:
            self._test_image_generation(image_config)

        self._show_summary(tts_config, image_config)
        return TTSImageSetupResult(
            tts_config=tts_config,
            image_config=image_config,
            success=True,
            message="TTS and Images configured successfully",
        )

    def _show_welcome(self) -> None:
        """Display welcome screen."""
        self.console.print(
            Panel.fit(
                "[bold blue]TTS and Image Generation Wizard[/bold blue]\n\n"
                "This wizard will help you configure Text-to-Speech "
                "and AI image generation for your videos.",
                title="Auto-Video Setup",
            )
        )
        self.console.print()

    def _setup_tts(self) -> TTSConfig | None:
        """Setup TTS configuration.

        Returns:
            TTS configuration or None if cancelled.
        """
        self.console.print("[bold]Configure Text-to-Speech (TTS)[/bold]")
        self.console.print()

        mode = self._select_tts_mode()

        if mode == "local":
            return self._setup_tts_local()
        elif mode == "api":
            return self._setup_tts_api()
        else:
            return self._setup_tts_hybrid()

    def _select_tts_mode(self) -> str:
        """Select TTS mode.

        Returns:
            Selected mode.
        """
        self.console.print("[bold]Select TTS Mode:[/bold]")
        self.console.print()

        choices = ["1. Local (Kokoro)", "2. API", "3. Hybrid"]

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
                return "local"
            elif selection == "2":
                return "api"
            else:
                return "hybrid"

    def _setup_tts_local(self) -> TTSConfig | None:
        """Setup local TTS.

        Returns:
            TTS configuration or None if cancelled.
        """
        self.console.print("[yellow]Local mode uses Kokoro-82M for TTS.[/yellow]")
        self.console.print("[dim]Model will be downloaded on first use.[/dim]")
        self.console.print()

        voice = self._select_tts_voice()

        return TTSConfig(mode="local", voice=voice)

    def _setup_tts_api(self) -> TTSConfig | None:
        """Setup API TTS.

        Returns:
            TTS configuration or None if cancelled.
        """
        provider = self._select_tts_api_provider()
        if not provider:
            return None

        api_key = _get_api_key(self.console, provider)
        if not api_key:
            return None

        voice = self._select_tts_voice()

        return TTSConfig(mode="api", provider=provider, voice=voice, api_key=api_key)

    def _setup_tts_hybrid(self) -> TTSConfig | None:
        """Setup hybrid TTS.

        Returns:
            TTS configuration or None if cancelled.
        """
        self.console.print(
            "[yellow]Hybrid mode: Uses API by default, falls back to local Kokoro.[/yellow]"
        )
        self.console.print()

        api_config = self._setup_tts_api()
        if not api_config:
            return None

        return TTSConfig(
            mode="hybrid",
            provider=api_config.provider,
            voice=api_config.voice,
            api_key=api_config.api_key,
        )

    def _select_tts_api_provider(self) -> str | None:
        """Select TTS API provider.

        Returns:
            Provider name or None if cancelled.
        """
        self.console.print("[bold]Select TTS API Provider:[/bold]")
        self.console.print()

        providers = [("elevenlabs", "ElevenLabs"), ("openai", "OpenAI TTS")]

        table = Table(title="Available TTS Providers")
        table.add_column("ID", style="cyan")
        table.add_column("Provider", style="green")

        for idx, (name, desc) in enumerate(providers, 1):
            table.add_row(str(idx), desc)

        self.console.print(table)

        choices = [str(i) for i in range(1, len(providers) + 1)]
        selection = Prompt.ask("Select provider", choices=choices, default="1")

        idx = int(selection) - 1
        return providers[idx][0]

    def _select_tts_voice(self) -> str:
        """Select TTS voice.

        Returns:
            Voice identifier.
        """
        self.console.print("[bold]Select Voice:[/bold]")
        self.console.print("[dim]For Kokoro, use voice codes like 'a_f' or 'b_f'.[/dim]")
        self.console.print()

        voice = Prompt.ask("Enter voice identifier", default="default")

        return voice

    def _setup_image_gen(self) -> ImageGenConfig | None:
        """Setup image generation configuration.

        Returns:
            Image generation configuration or None if cancelled.
        """
        if not Confirm.ask(
            "Enable AI image generation?",
            default=False,
        ):
            return None

        mode = self._select_image_mode()

        if mode == "local":
            return self._setup_image_local()
        else:
            return self._setup_image_api()

    def _select_image_mode(self) -> str:
        """Select image generation mode.

        Returns:
            Selected mode.
        """
        self.console.print("[bold]Select Image Generation Mode:[/bold]")
        self.console.print()

        choices = ["1. Local (Z-Image)", "2. API"]

        for choice in choices:
            self.console.print(f"  {choice}")

        selection = Prompt.ask(
            "Select mode",
            choices=["1", "2"],
            default="1",
        )

        return "local" if selection == "1" else "api"

    def _setup_image_local(self) -> ImageGenConfig | None:
        """Setup local image generation.

        Returns:
            Image generation configuration or None if cancelled.
        """
        self.console.print("[yellow]Local mode uses Z-Image for AI generation.[/yellow]")
        self.console.print("[dim]Model will be downloaded on first use.[/dim]")
        self.console.print()

        return ImageGenConfig(
            enabled=True,
            mode="local",
            model="Z-Image/Z-Image-Turbo",
            steps=6,
        )

    def _setup_image_api(self) -> ImageGenConfig | None:
        """Setup API image generation.

        Returns:
            Image generation configuration or None if cancelled.
        """
        provider = self._select_image_api_provider()
        if not provider:
            return None

        api_key = _get_api_key(self.console, provider)
        if not api_key:
            return None

        return ImageGenConfig(
            enabled=True,
            mode="api",
            provider=provider,
            api_key=api_key,
        )

    def _select_image_api_provider(self) -> str | None:
        """Select image generation API provider.

        Returns:
            Provider name or None if cancelled.
        """
        self.console.print("[bold]Select Image Generation API Provider:[/bold]")
        self.console.print()

        providers = [
            ("openai", "OpenAI DALL-E"),
            ("stability", "Stability AI"),
        ]

        table = Table(title="Available Providers")
        table.add_column("ID", style="cyan")
        table.add_column("Provider", style="green")

        for idx, (name, desc) in enumerate(providers, 1):
            table.add_row(str(idx), desc)

        self.console.print(table)

        choices = [str(i) for i in range(1, len(providers) + 1)]
        selection = Prompt.ask("Select provider", choices=choices, default="1")

        idx = int(selection) - 1
        return providers[idx][0]

    def _test_image_generation(self, config: ImageGenConfig) -> None:
        """Test image generation.

        Args:
            config: Image generation configuration.
        """
        if not Confirm.ask(
            "Do you want to test image generation now?",
            default=False,
        ):
            return

        self.console.print()
        self.console.print("[cyan]Testing image generation...[/cyan]")

        try:
            # Create a minimal LLM config for testing
            from auto_video.config.schema import LLMProviderConfig
            from auto_video.core.thumbnail import ThumbnailGenerator

            llm_config = LLMProviderConfig(provider="openai", model="gpt-4")
            generator = ThumbnailGenerator(config, llm_config)

            with tempfile.TemporaryDirectory() as tmpdir:
                output_path = Path(tmpdir) / "test_image.png"
                generator.generate(
                    "A beautiful sunset over mountains",
                    output_path,
                    size=(512, 512),
                )

                if output_path.exists():
                    self.console.print("[green]✓ Test successful![/green]")
                    self.console.print(f"[dim]Image saved to: {output_path}[/dim]")
        except ImportError:
            self.console.print(
                "[yellow]Image generation module not available - skipping test[/yellow]"
            )
        except Exception as e:
            self.console.print(f"[red]✗ Test failed:[/red] {e}")

    def _show_summary(self, tts_config: TTSConfig, image_config: ImageGenConfig | None) -> None:
        """Display configuration summary.

        Args:
            tts_config: TTS configuration.
            image_config: Image generation configuration.
        """
        self.console.print()
        summary_parts = []

        summary_parts.append(f"[bold]TTS Mode:[/bold] {tts_config.mode}")
        summary_parts.append(f"[bold]TTS Voice:[/bold] {tts_config.voice}")

        if tts_config.provider:
            summary_parts.append(f"[bold]TTS Provider:[/bold] {tts_config.provider}")

        if image_config and image_config.enabled:
            summary_parts.append(f"[bold]Images:[/bold] {image_config.mode}")

            if image_config.provider:
                summary_parts.append(f"[bold]Image Provider:[/bold] {image_config.provider}")

        self.console.print(
            Panel(
                "\n".join(summary_parts),
                title="[green]TTS and Images Configuration Summary[/green]",
            )
        )


@dataclass
class PromptsSetupResult:
    """Result of prompts setup wizard."""

    general_prompt: str
    targeted_prompt: str
    image_prompt: str
    success: bool
    message: str


class PromptsSetupWizard:
    """Wizard for configuring prompts."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize wizard.

        Args:
            console: Rich console instance. If None, creates a new one.
        """
        self.console = console or Console()
        self.prompts_dir = Path(__file__).parent.parent.parent.parent / "prompts"

    def run(self) -> PromptsSetupResult:
        """Run prompts setup wizard.

        Returns:
            Setup result with prompt configurations.
        """
        self._show_welcome()

        while True:
            choice = self._show_menu()

            if choice == "1":
                self._edit_prompt("general")
            elif choice == "2":
                self._edit_prompt("targeted")
            elif choice == "3":
                self._edit_prompt("image")
            elif choice == "4":
                self._reset_all_prompts()
            elif choice == "5":
                break

        general_prompt = self._load_prompt("general")
        targeted_prompt = self._load_prompt("targeted")
        image_prompt = self._load_prompt("image")

        self._show_summary(general_prompt, targeted_prompt, image_prompt)
        return PromptsSetupResult(
            general_prompt=general_prompt,
            targeted_prompt=targeted_prompt,
            image_prompt=image_prompt,
            success=True,
            message="Prompts configured successfully",
        )

    def _show_welcome(self) -> None:
        """Display welcome screen."""
        self.console.print(
            Panel.fit(
                "[bold blue]Prompts Configuration Wizard[/bold blue]\n\n"
                "This wizard will help you view and customize the prompts "
                "used for script generation and image creation.",
                title="Auto-Video Setup",
            )
        )
        self.console.print()

    def _show_menu(self) -> str:
        """Display main menu.

        Returns:
            User's menu choice.
        """
        self.console.print("[bold]Prompts Configuration:[/bold]")
        self.console.print()

        choices = [
            "1. View/Edit General Prompt",
            "2. View/Edit Targeted Prompt",
            "3. View/Edit Image Generation Prompt",
            "4. Reset All to Defaults",
            "5. Finish",
        ]

        for choice in choices:
            self.console.print(f"  {choice}")

        self.console.print()
        selection = Prompt.ask(
            "Select option",
            choices=["1", "2", "3", "4", "5"],
            default="5",
        )

        return selection

    def _edit_prompt(self, prompt_name: str) -> None:
        """Edit a specific prompt.

        Args:
            prompt_name: Name of the prompt (general, targeted, or image).
        """
        prompt_file = self.prompts_dir / f"{prompt_name}.txt"
        current_prompt = self._load_prompt(prompt_name)

        self.console.print()
        self.console.print(
            Panel(
                f"[bold]Current {prompt_name.title()} Prompt:[/bold]\n\n{current_prompt}",
                title=f"{prompt_name.title()} Prompt",
            )
        )
        self.console.print()

        action = Prompt.ask(
            "Choose action",
            choices=["view", "edit", "reset", "back"],
            default="view",
        )

        if action == "edit":
            self._open_editor(prompt_file)
            self._load_prompt(prompt_name)
            self.console.print(f"[green]✓ {prompt_name.title()} prompt updated[/green]")
        elif action == "reset":
            self._reset_prompt(prompt_name)
            self.console.print(f"[green]✓ {prompt_name.title()} prompt reset to default[/green]")

    def _load_prompt(self, prompt_name: str) -> str:
        """Load a prompt from file.

        Args:
            prompt_name: Name of the prompt.

        Returns:
            Prompt content as string.
        """
        prompt_file = self.prompts_dir / f"{prompt_name}.txt"

        if not prompt_file.exists():
            return f"Default {prompt_name} prompt"

        return prompt_file.read_text().strip()

    def _open_editor(self, prompt_file: Path) -> None:
        """Open a file in the system's default editor.

        Args:
            prompt_file: Path to the file to edit.
        """
        import os
        import subprocess

        editor = os.environ.get("EDITOR", "nano")

        self.console.print(f"[dim]Opening {prompt_file} with {editor}...[/dim]")
        self.console.print()

        try:
            subprocess.call([editor, str(prompt_file)])
        except Exception as e:
            self.console.print(f"[red]✗ Failed to open editor: {e}[/red]")
            self.console.print("[yellow]You can manually edit the file at:[/yellow]")
            self.console.print(f"  {prompt_file}")

    def _reset_prompt(self, prompt_name: str) -> None:
        """Reset a prompt to its default value.

        Args:
            prompt_name: Name of the prompt.
        """
        default_prompts = {
            "general": "# General prompt for video script generation",
            "targeted": "# Targeted prompt for specific video topics",
            "image": "# Prompt for image generation",
        }

        prompt_file = self.prompts_dir / f"{prompt_name}.txt"
        prompt_file.write_text(default_prompts[prompt_name])

    def _reset_all_prompts(self) -> None:
        """Reset all prompts to their default values."""
        if not Confirm.ask(
            "Are you sure you want to reset all prompts to defaults?",
            default=False,
        ):
            return

        self._reset_prompt("general")
        self._reset_prompt("targeted")
        self._reset_prompt("image")

        self.console.print("[green]✓ All prompts reset to defaults[/green]")

    def _show_summary(self, general: str, targeted: str, image: str) -> None:
        """Display configuration summary.

        Args:
            general: General prompt content.
            targeted: Targeted prompt content.
            image: Image prompt content.
        """
        self.console.print()
        self.console.print(
            Panel(
                f"[bold]General Prompt:[/bold] {len(general)} chars\n"
                f"[bold]Targeted Prompt:[/bold] {len(targeted)} chars\n"
                f"[bold]Image Prompt:[/bold] {len(image)} chars",
                title="[green]Prompts Configuration Summary[/green]",
            )
        )


YOUTUBE_CATEGORIES = {
    "1": "Film & Animation",
    "2": "Autos & Vehicles",
    "10": "Music",
    "15": "Pets & Animals",
    "17": "Sports",
    "18": "Short Movies",
    "19": "Travel & Events",
    "20": "Gaming",
    "21": "Videoblogging",
    "22": "People & Blogs",
    "23": "Comedy",
    "24": "Entertainment",
    "25": "News & Politics",
    "26": "Howto & Style",
    "27": "Education",
    "28": "Science & Technology",
    "29": "Nonprofits & Activism",
}


@dataclass
class YouTubeSetupResult:
    """Result of YouTube setup wizard."""

    config: YouTubeConfig | None
    success: bool
    message: str


class YouTubeSetupWizard:
    """Wizard for setting up YouTube upload configuration."""

    def __init__(self, console: Console | None = None) -> None:
        """Initialize wizard.

        Args:
            console: Rich console instance. If None, creates a new one.
        """
        self.console = console or Console()

    def run(self) -> YouTubeSetupResult:
        """Run YouTube setup wizard.

        Returns:
            Setup result with configuration.
        """
        self._show_welcome()

        enabled = self._ask_enable_youtube()

        if not enabled:
            config = YouTubeConfig(enabled=False)
            self._show_summary(config)
            return YouTubeSetupResult(
                config=config,
                success=True,
                message="YouTube upload disabled",
            )

        credentials_path = self._ask_credentials_path()

        if not credentials_path:
            return YouTubeSetupResult(
                config=None,
                success=False,
                message="Setup cancelled - credentials required",
            )

        privacy = self._select_privacy()
        category = self._select_category()
        auto_tags = self._ask_auto_tags()

        config = YouTubeConfig(
            enabled=True,
            credentials_path=credentials_path,
            default_privacy=privacy,
            default_category=category,
            auto_tags=auto_tags,
        )

        self._show_summary(config)
        return YouTubeSetupResult(
            config=config,
            success=True,
            message="YouTube configured successfully",
        )

    def _show_welcome(self) -> None:
        """Display welcome screen."""
        self.console.print(
            Panel.fit(
                "[bold blue]YouTube Upload Configuration Wizard[/bold blue]\n\n"
                "This wizard will help you configure YouTube upload "
                "for your generated videos.\n\n"
                "[dim]You will need a Google Cloud OAuth2 credentials file "
                "(credentials.json).[/dim]",
                title="Auto-Video Setup",
            )
        )
        self.console.print()

    def _ask_enable_youtube(self) -> bool:
        """Ask whether to enable YouTube upload.

        Returns:
            True if user wants to enable YouTube, False otherwise.
        """
        return Confirm.ask(
            "Do you want to enable YouTube upload?",
            default=False,
        )

    def _ask_credentials_path(self) -> Path | None:
        """Ask for path to credentials.json.

        Returns:
            Path to credentials file or None if cancelled.
        """
        self.console.print()
        self.console.print(
            "[dim]You need a Google Cloud OAuth2 credentials file. "
            "Get it from: https://console.cloud.google.com/apis/credentials[/dim]"
        )
        self.console.print()

        while True:
            path_str = Prompt.ask(
                "Enter path to credentials.json",
                default=str(Path.home() / ".config" / "auto-video" / "credentials.json"),
            )

            path = Path(path_str).expanduser()

            if not path.exists():
                self.console.print(f"[red]✗ File does not exist: {path}[/red]")
                if not Confirm.ask("Try another path?", default=True):
                    return None
                continue

            if not path.is_file():
                self.console.print(f"[red]✗ Path is not a file: {path}[/red]")
                if not Confirm.ask("Try another path?", default=True):
                    return None
                continue

            validation_result = self._validate_credentials_file(path)

            if validation_result:
                self.console.print("[green]✓ Credentials file is valid JSON[/green]")
                return path

            if not Confirm.ask("Try another path?", default=True):
                return None

    def _validate_credentials_file(self, path: Path) -> bool:
        """Validate that credentials file is valid JSON.

        Args:
            path: Path to credentials file.

        Returns:
            True if valid JSON, False otherwise.
        """
        try:
            content = path.read_text()
            data = json.loads(content)

            if "installed" in data or "web" in data:
                return True

            self.console.print(
                "[yellow]⚠ File is valid JSON but may not be a valid "
                "OAuth2 credentials file[/yellow]"
            )
            self.console.print(
                "[dim]Expected 'installed' or 'web' key for OAuth2 credentials[/dim]"
            )
            return Confirm.ask("Continue anyway?", default=True)

        except json.JSONDecodeError as e:
            self.console.print(f"[red]✗ Invalid JSON: {e}[/red]")
            return False
        except Exception as e:
            self.console.print(f"[red]✗ Error reading file: {e}[/red]")
            return False

    def _select_privacy(self) -> PrivacyType:
        """Select default privacy setting.

        Returns:
            Privacy setting (public, unlisted, or private).
        """
        self.console.print()
        self.console.print("[bold]Select Default Privacy:[/bold]")
        self.console.print()

        choices = [
            ("1", "public", "Anyone can search for and view your video"),
            ("2", "unlisted", "Anyone with the link can view your video"),
            ("3", "private", "Only you and selected users can view"),
        ]

        for idx, name, desc in choices:
            self.console.print(f"  {idx}. [cyan]{name}[/cyan] - {desc}")

        self.console.print()
        selection = Prompt.ask(
            "Select privacy",
            choices=["1", "2", "3"],
            default="2",
        )

        privacy_map: dict[str, PrivacyType] = {
            "1": "public",
            "2": "unlisted",
            "3": "private",
        }
        return privacy_map[selection]

    def _select_category(self) -> str:
        """Select default YouTube category.

        Returns:
            Category ID.
        """
        self.console.print()
        table = Table(title="YouTube Video Categories")
        table.add_column("ID", style="cyan")
        table.add_column("Category", style="green")

        for cat_id, cat_name in YOUTUBE_CATEGORIES.items():
            table.add_row(cat_id, cat_name)

        self.console.print(table)
        self.console.print()

        valid_ids = list(YOUTUBE_CATEGORIES.keys())
        selection = Prompt.ask(
            "Select default category",
            choices=valid_ids,
            default="22",
        )

        return selection

    def _ask_auto_tags(self) -> bool:
        """Ask whether to auto-generate tags.

        Returns:
            True if auto-tags enabled, False otherwise.
        """
        self.console.print()
        self.console.print(
            "[dim]Auto-tags will extract keywords from the video script and add them as tags.[/dim]"
        )
        return Confirm.ask(
            "Enable automatic tag generation?",
            default=True,
        )

    def _show_summary(self, config: YouTubeConfig) -> None:
        """Display configuration summary.

        Args:
            config: YouTube configuration.
        """
        self.console.print()

        if not config.enabled:
            self.console.print(
                Panel(
                    "[bold]YouTube Upload:[/bold] Disabled",
                    title="[green]YouTube Configuration Summary[/green]",
                )
            )
            return

        category_name = YOUTUBE_CATEGORIES.get(config.default_category, "Unknown")
        credentials_display = str(config.credentials_path) if config.credentials_path else "Not set"

        self.console.print(
            Panel(
                f"[bold]Enabled:[/bold] Yes\n"
                f"[bold]Credentials:[/bold] {credentials_display}\n"
                f"[bold]Default Privacy:[/bold] {config.default_privacy}\n"
                f"[bold]Default Category:[/bold] {config.default_category} ({category_name})\n"
                f"[bold]Auto Tags:[/bold] {'Enabled' if config.auto_tags else 'Disabled'}",
                title="[green]YouTube Configuration Summary[/green]",
            )
        )


class SetupWizard:
    """Main setup wizard that orchestrates all individual wizards."""

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize the setup wizard.

        Args:
            config_path: Path to save configuration. If None, uses default path.
        """
        self.console = Console()
        self.config_path = config_path or get_default_config_path()

        self.llm_wizard = LLMSetupWizard(self.console)
        self.storage_wizard = StorageSetupWizard(self.console)
        self.visuals_wizard = VisualsSetupWizard(self.console)
        self.tts_image_wizard = TTSImageSetupWizard(self.console)
        self.prompts_wizard = PromptsSetupWizard(self.console)
        self.youtube_wizard = YouTubeSetupWizard(self.console)

        self.llm_config: LLMProviderConfig | None = None
        self.storage_config: StorageConfig | None = None
        self.visuals_config: VisualsConfig | None = None
        self.tts_config: TTSConfig | None = None
        self.image_config: ImageGenConfig | None = None
        self.youtube_config: YouTubeConfig | None = None
        self.general_prompt: str = ""
        self.targeted_prompt: str = ""
        self.image_prompt: str = ""

    def run(self) -> AppConfig | None:
        """Run the complete setup wizard.

        Returns:
            Complete AppConfig if successful, None if cancelled.
        """
        self._show_welcome()

        sections = [
            ("llm", "LLM Provider", self._run_llm_wizard),
            ("storage", "Storage", self._run_storage_wizard),
            ("visuals", "Visuals", self._run_visuals_wizard),
            ("tts_image", "TTS and Images", self._run_tts_image_wizard),
            ("prompts", "Prompts", self._run_prompts_wizard),
            ("youtube", "YouTube", self._run_youtube_wizard),
        ]

        current_section = 0

        while True:
            if current_section >= len(sections):
                config = self._build_config()
                if config is None:
                    self.console.print("[red]Failed to build configuration[/red]")
                    return None

                self._show_final_summary(config)
                action = self._ask_confirmation()

                if action == "confirm":
                    self._save_config(config)
                    return config
                elif action == "modify":
                    section_name = self._select_section_to_modify()
                    if section_name:
                        for idx, (key, _, _) in enumerate(sections):
                            if key == section_name:
                                current_section = idx
                                break
                    else:
                        current_section = len(sections)
                    continue
                else:
                    self.console.print("[yellow]Setup cancelled.[/yellow]")
                    return None
            else:
                key, name, runner = sections[current_section]
                result = runner()

                if result:
                    current_section += 1
                else:
                    if current_section == 0:
                        self.console.print("[yellow]Setup cancelled.[/yellow]")
                        return None
                    current_section = max(0, current_section - 1)

    def _show_welcome(self) -> None:
        """Display welcome screen."""
        self.console.print()
        self.console.print(
            Panel.fit(
                "[bold blue]Auto-Video Setup Wizard[/bold blue]\n\n"
                "This wizard will guide you through the complete setup process.\n"
                "You will configure:\n\n"
                "  • LLM Provider (OpenAI, Anthropic, Groq, Google, or Local)\n"
                "  • Storage paths for videos and temporary files\n"
                "  • Visuals source (Stock footage, Local, or AI-generated)\n"
                "  • TTS and Image generation\n"
                "  • Custom prompts for script generation\n"
                "  • YouTube upload settings\n\n"
                "[dim]Press Ctrl+C at any time to cancel.[/dim]",
                title="[cyan]Welcome[/cyan]",
            )
        )
        self.console.print()

        Confirm.ask("Ready to begin?", default=True, console=self.console)
        self.console.print()

    def _run_llm_wizard(self) -> bool:
        """Run LLM setup wizard.

        Returns:
            True if successful, False otherwise.
        """
        result = self.llm_wizard.run()
        if result.success and result.config:
            self.llm_config = result.config
            return True
        return False

    def _run_storage_wizard(self) -> bool:
        """Run storage setup wizard.

        Returns:
            True if successful, False otherwise.
        """
        result = self.storage_wizard.run()
        if result.success and result.config:
            self.storage_config = result.config
            return True
        return False

    def _run_visuals_wizard(self) -> bool:
        """Run visuals setup wizard.

        Returns:
            True if successful, False otherwise.
        """
        result = self.visuals_wizard.run()
        if result.success and result.config:
            self.visuals_config = result.config
            return True
        return False

    def _run_tts_image_wizard(self) -> bool:
        """Run TTS and Image setup wizard.

        Returns:
            True if successful, False otherwise.
        """
        result = self.tts_image_wizard.run()
        if result.success and result.tts_config:
            self.tts_config = result.tts_config
            self.image_config = result.image_config
            return True
        return False

    def _run_prompts_wizard(self) -> bool:
        """Run prompts setup wizard.

        Returns:
            True if successful, False otherwise.
        """
        result = self.prompts_wizard.run()
        if result.success:
            self.general_prompt = result.general_prompt
            self.targeted_prompt = result.targeted_prompt
            self.image_prompt = result.image_prompt
            return True
        return False

    def _run_youtube_wizard(self) -> bool:
        """Run YouTube setup wizard.

        Returns:
            True if successful, False otherwise.
        """
        result = self.youtube_wizard.run()
        if result.success and result.config:
            self.youtube_config = result.config
            return True
        return False

    def _build_config(self) -> AppConfig | None:
        """Build AppConfig from collected configurations.

        Returns:
            AppConfig if all required configs are present, None otherwise.
        """
        if not self.llm_config:
            self.console.print("[red]LLM configuration is missing[/red]")
            return None

        if not self.storage_config:
            self.console.print("[red]Storage configuration is missing[/red]")
            return None

        if not self.visuals_config:
            self.console.print("[red]Visuals configuration is missing[/red]")
            return None

        if not self.tts_config:
            self.console.print("[red]TTS configuration is missing[/red]")
            return None

        image_config = self.image_config or ImageGenConfig(enabled=False)
        youtube_config = self.youtube_config or YouTubeConfig(enabled=False)

        return AppConfig(
            llm=self.llm_config,
            tts=self.tts_config,
            visuals=self.visuals_config,
            image_gen=image_config,
            storage=self.storage_config,
            youtube=youtube_config,
        )

    def _show_final_summary(self, config: AppConfig) -> None:
        """Display complete configuration summary.

        Args:
            config: Complete application configuration.
        """
        self.console.print()
        self.console.print(
            "[bold]═══════════════════════════════════════════════════════════[/bold]"
        )
        self.console.print("[bold cyan]           FINAL CONFIGURATION SUMMARY[/bold cyan]")
        self.console.print(
            "[bold]═══════════════════════════════════════════════════════════[/bold]"
        )
        self.console.print()

        table = Table(show_header=True, header_style="bold magenta", box=None)
        table.add_column("Section", style="cyan", width=20)
        table.add_column("Configuration", style="white")

        table.add_row("LLM Provider", f"{config.llm.provider} / {config.llm.model}")
        table.add_row("LLM Temperature", f"{config.llm.temperature}")

        api_key_display = "***" if config.llm.api_key else "Not set"
        table.add_row("LLM API Key", api_key_display)

        if config.llm.host:
            table.add_row("LLM Host", config.llm.host)

        table.add_row("TTS Mode", config.tts.mode)
        table.add_row("TTS Voice", config.tts.voice)

        if config.tts.provider:
            table.add_row("TTS Provider", config.tts.provider)

        table.add_row("Visuals Mode", config.visuals.mode)

        if config.visuals.providers:
            table.add_row("Visuals Providers", ", ".join(config.visuals.providers))

        if config.visuals.local_path:
            table.add_row("Visuals Local Path", config.visuals.local_path)

        if config.image_gen.enabled:
            table.add_row("Image Generation", f"{config.image_gen.mode} ({config.image_gen.model})")
        else:
            table.add_row("Image Generation", "Disabled")

        table.add_row("Videos Path", str(config.storage.videos_path))
        table.add_row("Temp Path", str(config.storage.temp_path))
        table.add_row("Keep Temp Files", "Yes" if config.storage.keep_temp else "No")

        if config.youtube.enabled:
            table.add_row("YouTube Upload", "Enabled")
            table.add_row("YouTube Privacy", config.youtube.default_privacy)
            if config.youtube.credentials_path:
                table.add_row("YouTube Credentials", str(config.youtube.credentials_path))
        else:
            table.add_row("YouTube Upload", "Disabled")

        table.add_row("Default Format", config.default_format)
        table.add_row("Default Language", config.default_lang)

        self.console.print(table)
        self.console.print()

        self.console.print("[dim]Prompts:[/dim]")
        self.console.print(f"  General: {len(self.general_prompt)} chars")
        self.console.print(f"  Targeted: {len(self.targeted_prompt)} chars")
        self.console.print(f"  Image: {len(self.image_prompt)} chars")
        self.console.print()

        self.console.print(f"[dim]Configuration will be saved to: {self.config_path}[/dim]")
        self.console.print()

    def _ask_confirmation(self) -> str:
        """Ask user for confirmation.

        Returns:
            "confirm", "modify", or "cancel".
        """
        self.console.print("[bold]What would you like to do?[/bold]")
        self.console.print()

        choices = [
            "1. Confirm and save configuration",
            "2. Modify a section",
            "3. Cancel setup",
        ]

        for choice in choices:
            self.console.print(f"  {choice}")

        self.console.print()
        selection = Prompt.ask(
            "Select option",
            choices=["1", "2", "3"],
            default="1",
        )

        if selection == "1":
            return "confirm"
        elif selection == "2":
            return "modify"
        else:
            return "cancel"

    def _select_section_to_modify(self) -> str | None:
        """Let user select which section to modify.

        Returns:
            Section name or None if cancelled.
        """
        self.console.print()
        self.console.print("[bold]Which section would you like to modify?[/bold]")
        self.console.print()

        sections = [
            ("llm", "LLM Provider"),
            ("storage", "Storage"),
            ("visuals", "Visuals"),
            ("tts_image", "TTS and Images"),
            ("prompts", "Prompts"),
            ("youtube", "YouTube"),
        ]

        for idx, (_, name) in enumerate(sections, 1):
            self.console.print(f"  {idx}. {name}")

        self.console.print(f"  {len(sections) + 1}. Go back to summary")

        choices = [str(i) for i in range(1, len(sections) + 2)]
        self.console.print()
        selection = Prompt.ask(
            "Select section",
            choices=choices,
            default=str(len(sections) + 1),
        )

        idx = int(selection) - 1

        if idx < len(sections):
            return sections[idx][0]

        return None

    def _save_config(self, config: AppConfig) -> None:
        """Save configuration to file.

        Args:
            config: Configuration to save.
        """
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            save_config(config, self.config_path)

            self.console.print()
            self.console.print(
                Panel.fit(
                    f"[bold green]Configuration saved successfully![/bold green]\n\n"
                    f"Config file: {self.config_path}\n\n"
                    "[dim]You can now run 'auto-video create' to generate videos.[/dim]",
                    title="[green]Setup Complete[/green]",
                )
            )
            self.console.print()

        except Exception as e:
            self.console.print(f"[red]Failed to save configuration: {e}[/red]")
            self.console.print("[yellow]Please check file permissions and try again.[/yellow]")
