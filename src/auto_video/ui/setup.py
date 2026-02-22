"""Setup wizard UI for LLM configuration."""

import tempfile
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from auto_video.config.schema import (
    ImageGenConfig,
    LLMProviderConfig,
    StorageConfig,
    TTSConfig,
    VisualsConfig,
)


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
            from auto_video.core.llm import LLM  # type: ignore

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

        return VisualsConfig(mode="stock", providers=providers)

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

        if stock_config:
            providers = stock_config.providers or []

        if local_config:
            local_path = local_config.local_path

        if not providers and not local_path:
            self.console.print("[red]✗ At least one source must be configured[/red]")
            return None

        return VisualsConfig(mode="hybrid", providers=providers, local_path=local_path)

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
            from auto_video.core.thumbnail import ThumbnailGenerator  # type: ignore

            generator = ThumbnailGenerator(config)

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
