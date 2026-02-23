"""Main CLI entry point."""

import argparse
import sys
from collections.abc import Callable

from rich.console import Console

from auto_video.config.loader import (
    get_default_config_path,
    load_config,
    save_config,
)
from auto_video.core.pipeline import PipelineStep, VideoPipeline
from auto_video.ui.setup import SetupWizard

CommandHandler = Callable[[argparse.Namespace], int]


def cmd_setup() -> int:
    """Run the complete setup wizard (all wizards in sequence)."""
    wizard = SetupWizard()
    config = wizard.run()

    if config is None:
        console = Console()
        console.print("[yellow]Setup cancelled or failed.[/yellow]")
        return 1

    return 0


def cmd_setup_llm(args: argparse.Namespace) -> int:
    """Run only the LLM setup wizard."""
    from auto_video.ui.setup import LLMSetupWizard

    console = Console()
    wizard = LLMSetupWizard(console)

    result = wizard.run()

    if not result.success or result.config is None:
        console.print("[yellow]LLM setup cancelled or failed.[/yellow]")
        return 1

    # Load existing config and update LLM section
    config_path = args.config if args.config else get_default_config_path()
    try:
        config = load_config(config_path)
    except FileNotFoundError:
        console.print("[red]No existing configuration found. Run 'auto-video setup' first.[/red]")
        return 1

    config.llm = result.config

    try:
        save_config(config, config_path)
        console.print(f"[green]LLM configuration updated and saved to {config_path}[/green]")
        return 0
    except Exception as e:
        console.print(f"[red]Failed to save configuration: {e}[/red]")
        return 1


def cmd_setup_storage(args: argparse.Namespace) -> int:
    """Run only the Storage setup wizard."""
    from auto_video.ui.setup import StorageSetupWizard

    console = Console()
    wizard = StorageSetupWizard(console)

    result = wizard.run()

    if not result.success or result.config is None:
        console.print("[yellow]Storage setup cancelled or failed.[/yellow]")
        return 1

    # Load existing config and update Storage section
    config_path = args.config if args.config else get_default_config_path()
    try:
        config = load_config(config_path)
    except FileNotFoundError:
        console.print("[red]No existing configuration found. Run 'auto-video setup' first.[/red]")
        return 1

    config.storage = result.config

    try:
        save_config(config, config_path)
        console.print(f"[green]Storage configuration updated and saved to {config_path}[/green]")
        return 0
    except Exception as e:
        console.print(f"[red]Failed to save configuration: {e}[/red]")
        return 1


def cmd_setup_visuals(args: argparse.Namespace) -> int:
    """Run only the Visuals setup wizard."""
    from auto_video.ui.setup import VisualsSetupWizard

    console = Console()
    wizard = VisualsSetupWizard(console)

    result = wizard.run()

    if not result.success or result.config is None:
        console.print("[yellow]Visuals setup cancelled or failed.[/yellow]")
        return 1

    # Load existing config and update Visuals section
    config_path = args.config if args.config else get_default_config_path()
    try:
        config = load_config(config_path)
    except FileNotFoundError:
        console.print("[red]No existing configuration found. Run 'auto-video setup' first.[/red]")
        return 1

    config.visuals = result.config

    try:
        save_config(config, config_path)
        console.print(f"[green]Visuals configuration updated and saved to {config_path}[/green]")
        return 0
    except Exception as e:
        console.print(f"[red]Failed to save configuration: {e}[/red]")
        return 1


def cmd_setup_tts(args: argparse.Namespace) -> int:
    """Run only the TTS and Images setup wizard."""
    from auto_video.ui.setup import TTSImageSetupWizard

    console = Console()
    wizard = TTSImageSetupWizard(console)

    result = wizard.run()

    if not result.success or result.tts_config is None:
        console.print("[yellow]TTS/Images setup cancelled or failed.[/yellow]")
        return 1

    # Load existing config and update TTS/Image sections
    config_path = args.config if args.config else get_default_config_path()
    try:
        config = load_config(config_path)
    except FileNotFoundError:
        console.print("[red]No existing configuration found. Run 'auto-video setup' first.[/red]")
        return 1

    config.tts = result.tts_config
    if result.image_config:
        config.image_gen = result.image_config

    try:
        save_config(config, config_path)
        console.print(f"[green]TTS/Images configuration updated and saved to {config_path}[/green]")
        return 0
    except Exception as e:
        console.print(f"[red]Failed to save configuration: {e}[/red]")
        return 1


def cmd_setup_prompts(args: argparse.Namespace) -> int:
    """Run only the Prompts setup wizard."""
    from auto_video.ui.setup import PromptsSetupWizard

    console = Console()
    wizard = PromptsSetupWizard(console)

    result = wizard.run()

    if not result.success:
        console.print("[yellow]Prompts setup cancelled or failed.[/yellow]")
        return 1

    console.print("[green]Prompts configuration updated successfully.[/green]")
    return 0


def cmd_setup_youtube(args: argparse.Namespace) -> int:
    """Run only the YouTube setup wizard."""
    from auto_video.ui.setup import YouTubeSetupWizard

    console = Console()
    wizard = YouTubeSetupWizard(console)

    result = wizard.run()

    if not result.success or result.config is None:
        console.print("[yellow]YouTube setup cancelled or failed.[/yellow]")
        return 1

    # Load existing config and update YouTube section
    config_path = args.config if args.config else get_default_config_path()
    try:
        config = load_config(config_path)
    except FileNotFoundError:
        console.print("[red]No existing configuration found. Run 'auto-video setup' first.[/red]")
        return 1

    config.youtube = result.config

    try:
        save_config(config, config_path)
        console.print(f"[green]YouTube configuration updated and saved to {config_path}[/green]")
        return 0
    except Exception as e:
        console.print(f"[red]Failed to save configuration: {e}[/red]")
        return 1


def cmd_create(args: argparse.Namespace) -> int:
    from typing import Any

    from auto_video.ui.progress import DevProgressDisplay, PipelineProgressDisplay

    console = Console()
    progress_display: Any = None

    config_path = args.config if args.config else get_default_config_path()

    try:
        config = load_config(config_path)
    except FileNotFoundError:
        console.print(f"[red]Configuration file not found: {config_path}[/red]")
        console.print("[yellow]Run 'auto-video setup' to create a configuration.[/yellow]")
        return 1
    except Exception as e:
        console.print(f"[red]Failed to load configuration: {e}[/red]")
        return 1

    title = args.title if args.title else None

    if args.auto:
        from rich.prompt import Prompt

        if not title:
            title = Prompt.ask("Enter video title", default="AI Generated Video")

    video_format = args.format or config.default_format
    lang = args.lang or config.default_lang
    skip_upload = args.no_upload

    console.print("[cyan]Starting video generation...[/cyan]")
    console.print(f"  Title: {title or 'Auto-generated'}")
    console.print(f"  Format: {video_format}")
    console.print(f"  Language: {lang}")
    console.print(f"  Duration: {args.duration if args.duration else 'default'}")
    console.print(f"  Skip upload: {skip_upload}")
    if args.dev:
        console.print("  Mode: dev (detailed output)")
    console.print()

    steps = [
        "1. Script",
        "2. Audio",
        "3. Visuels",
        "4. Montage",
        "5. Sous-titres",
        "6. Miniature",
        "7. Upload",
    ]

    if args.dev:
        progress_display = DevProgressDisplay(steps)
    else:
        progress_display = PipelineProgressDisplay(steps)

    pipeline = VideoPipeline(config, progress_display)
    result = pipeline.run(
        title=title,
        format=video_format,
        lang=lang,
        duration=args.duration,
        skip_upload=skip_upload,
    )

    if result.status == "success":
        console.print("[green]✓ Video generated successfully![/green]")
        console.print(f"  Video ID: {result.video_id}")

        if result.output_path:
            console.print(f"  Output: {result.output_path}")

        if result.youtube_url:
            console.print(f"  YouTube: {result.youtube_url}")

        return 0
    elif result.status == "partial":
        console.print("[yellow]⚠ Video generation partially completed.[/yellow]")
        console.print(f"  Video ID: {result.video_id}")

        if result.output_path:
            console.print(f"  Output: {result.output_path}")

        if result.error:
            console.print(f"  Error: {result.error}")

        console.print(
            f"[cyan]Run 'auto-video resume --video-id {result.video_id}' to continue.[/cyan]"
        )
        return 2
    else:
        console.print("[red]✗ Video generation failed.[/red]")
        console.print(f"  Video ID: {result.video_id}")

        if result.error:
            console.print(f"  Error: {result.error}")

        if result.failed_step:
            console.print(f"  Failed step: {result.failed_step.name}")

        console.print(
            f"[cyan]Run 'auto-video resume --video-id {result.video_id}' to retry.[/cyan]"
        )
        return 1


def cmd_resume(args: argparse.Namespace) -> int:
    console = Console()

    config_path = args.config if args.config else get_default_config_path()

    try:
        config = load_config(config_path)
    except FileNotFoundError:
        console.print(f"[red]Configuration file not found: {config_path}[/red]")
        console.print("[yellow]Run 'auto-video setup' to create a configuration.[/yellow]")
        return 1
    except Exception as e:
        console.print(f"[red]Failed to load configuration: {e}[/red]")
        return 1

    from_step = None
    if args.step is not None:
        try:
            from_step = PipelineStep(args.step)
        except ValueError:
            console.print(f"[red]Invalid step: {args.step}[/red]")
            console.print("[cyan]Valid steps: 1-7[/cyan]")
            console.print("  1: SCRIPT")
            console.print("  2: AUDIO")
            console.print("  3: VISUALS")
            console.print("  4: MONTAGE")
            console.print("  5: SUBTITLES")
            console.print("  6: THUMBNAIL")
            console.print("  7: UPLOAD")
            return 1

    console.print("[cyan]Resuming video generation...[/cyan]")
    console.print(f"  Video ID: {args.video_id}")

    if from_step:
        console.print(f"  From step: {from_step.name}")

    console.print()

    pipeline = VideoPipeline(config)

    result = pipeline.resume(args.video_id, from_step or PipelineStep.SCRIPT)

    if result.status == "success":
        console.print("[green]✓ Video generation completed successfully![/green]")
        console.print(f"  Video ID: {result.video_id}")

        if result.output_path:
            console.print(f"  Output: {result.output_path}")

        if result.youtube_url:
            console.print(f"  YouTube: {result.youtube_url}")

        return 0
    elif result.status == "partial":
        console.print("[yellow]⚠ Video generation partially completed.[/yellow]")
        console.print(f"  Video ID: {result.video_id}")

        if result.output_path:
            console.print(f"  Output: {result.output_path}")

        if result.error:
            console.print(f"  Error: {result.error}")

        return 2
    else:
        console.print("[red]✗ Video generation failed.[/red]")
        console.print(f"  Video ID: {result.video_id}")

        if result.error:
            console.print(f"  Error: {result.error}")

        if result.failed_step:
            console.print(f"  Failed step: {result.failed_step.name}")

        return 1


def cmd_config(args: argparse.Namespace) -> int:
    console = Console()

    config_path = args.config if args.config else get_default_config_path()

    if args.section:
        return cmd_config_edit_section(args)

    if args.show:
        try:
            config = load_config(config_path)
        except FileNotFoundError:
            console.print(f"[red]Configuration file not found: {config_path}[/red]")
            return 1
        except Exception as e:
            console.print(f"[red]Failed to load configuration: {e}[/red]")
            return 1

        from rich.panel import Panel
        from rich.table import Table

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Setting", style="cyan", width=25)
        table.add_column("Value", style="white")

        table.add_row("LLM Provider", config.llm.provider)
        table.add_row("LLM Model", config.llm.model)
        table.add_row("LLM Temperature", str(config.llm.temperature))

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

        console.print(Panel(table, title=f"[bold green]Configuration: {config_path}[/bold green]"))

        return 0

    if args.edit:
        import os
        import subprocess

        editor = os.environ.get("EDITOR", "nano")

        console.print(f"[dim]Opening {config_path} with {editor}...[/dim]")

        try:
            subprocess.call([editor, str(config_path)])
            console.print("[green]✓ Configuration file closed.[/green]")
            return 0
        except Exception as e:
            console.print(f"[red]Failed to open editor: {e}[/red]")
            return 1

    console.print("[yellow]Use --show to view configuration or --edit to edit it.[/yellow]")
    return 0


def cmd_config_edit_section(args: argparse.Namespace) -> int:
    """Edit a specific configuration section using wizard.

    Args:
        args: Command line arguments.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    console = Console()
    config_path = args.config if args.config else get_default_config_path()

    try:
        config = load_config(config_path)
    except FileNotFoundError:
        console.print(f"[red]Configuration file not found: {config_path}[/red]")
        console.print("[yellow]Run 'auto-video setup' to create a configuration.[/yellow]")
        return 1
    except Exception as e:
        console.print(f"[red]Failed to load configuration: {e}[/red]")
        return 1

    section = args.section

    if section == "llm":
        from auto_video.ui.setup import LLMSetupWizard

        wizard = LLMSetupWizard(console)
        result = wizard.run()

        if not result.success or result.config is None:
            console.print("[yellow]LLM configuration cancelled.[/yellow]")
            return 1

        config.llm = result.config
        message = "LLM configuration updated"

    elif section == "storage":
        from auto_video.ui.setup import StorageSetupWizard

        wizard = StorageSetupWizard(console)
        result = wizard.run()

        if not result.success or result.config is None:
            console.print("[yellow]Storage configuration cancelled.[/yellow]")
            return 1

        config.storage = result.config
        message = "Storage configuration updated"

    elif section == "visuals":
        from auto_video.ui.setup import VisualsSetupWizard

        wizard = VisualsSetupWizard(console)
        result = wizard.run()

        if not result.success or result.config is None:
            console.print("[yellow]Visuals configuration cancelled.[/yellow]")
            return 1

        config.visuals = result.config
        message = "Visuals configuration updated"

    elif section == "tts":
        from auto_video.ui.setup import TTSImageSetupWizard

        wizard = TTSImageSetupWizard(console)
        result = wizard.run()

        if not result.success or result.tts_config is None:
            console.print("[yellow]TTS configuration cancelled.[/yellow]")
            return 1

        config.tts = result.tts_config
        if result.image_config:
            config.image_gen = result.image_config
        message = "TTS configuration updated"

    elif section == "image":
        from auto_video.ui.setup import TTSImageSetupWizard

        wizard = TTSImageSetupWizard(console)
        result = wizard.run()

        if not result.success or result.image_config is None:
            console.print("[yellow]Image generation configuration cancelled.[/yellow]")
            return 1

        if result.tts_config:
            config.tts = result.tts_config
        config.image_gen = result.image_config
        message = "Image generation configuration updated"

    elif section == "youtube":
        from auto_video.ui.setup import YouTubeSetupWizard

        wizard = YouTubeSetupWizard(console)
        result = wizard.run()

        if not result.success or result.config is None:
            console.print("[yellow]YouTube configuration cancelled.[/yellow]")
            return 1

        config.youtube = result.config
        message = "YouTube configuration updated"

    elif section == "prompts":
        from auto_video.ui.setup import PromptsSetupWizard

        wizard = PromptsSetupWizard(console)
        result = wizard.run()

        if not result.success:
            console.print("[yellow]Prompts configuration cancelled.[/yellow]")
            return 1

        prompts_path = config_path.parent / "prompts"
        prompts_path.mkdir(parents=True, exist_ok=True)

        if result.general_prompt:
            (prompts_path / "general.txt").write_text(result.general_prompt)
        if result.targeted_prompt:
            (prompts_path / "targeted.txt").write_text(result.targeted_prompt)
        if result.image_prompt:
            (prompts_path / "image.txt").write_text(result.image_prompt)

        message = "Prompts configuration updated"

    else:
        console.print(f"[red]Unknown section: {section}[/red]")
        return 1

    try:
        save_config(config, config_path)
        console.print(f"[green]✓ {message} and saved to {config_path}[/green]")
        return 0
    except Exception as e:
        console.print(f"[red]Failed to save configuration: {e}[/red]")
        return 1


def cmd_models(args: argparse.Namespace) -> int:
    console = Console()

    if args.list:
        from rich.table import Table

        console.print("[cyan]Available Models:[/cyan]")
        console.print()

        llm_table = Table(title="LLM Models")
        llm_table.add_column("Provider", style="cyan")
        llm_table.add_column("Models", style="white")

        llm_table.add_row("OpenAI", "gpt-4o, gpt-4-turbo, gpt-3.5-turbo")
        llm_table.add_row("Anthropic", "claude-3-opus, claude-3-sonnet, claude-3-haiku")
        llm_table.add_row("Groq", "llama3.1-70b, mixtral-8x7b, gemma-7b")
        llm_table.add_row("Google", "gemini-2.5-flash, gemini-2.0-flash, gemini-2.5-pro")
        llm_table.add_row("Zhipu AI (z.ai)", "glm-4.5, glm-4-flash, glm-4-long, glm-z1-air")
        llm_table.add_row("Ollama (Local)", "Any model available in Ollama")

        console.print(llm_table)
        console.print()

        tts_table = Table(title="TTS Models")
        tts_table.add_column("Provider", style="cyan")
        tts_table.add_column("Models/Voices", style="white")

        tts_table.add_row("Kokoro (Local)", "Multiple voices (a_f, b_f, etc.)")
        tts_table.add_row("ElevenLabs", "Available voices in your account")
        tts_table.add_row("OpenAI TTS", "alloy, echo, fable, onyx, nova, shimmer")

        console.print(tts_table)
        console.print()

        image_table = Table(title="Image Generation Models")
        image_table.add_column("Provider", style="cyan")
        image_table.add_column("Models", style="white")

        image_table.add_row("Z-Image (Local)", "Z-Image/Z-Image-Turbo")
        image_table.add_row("OpenAI", "dall-e-3, dall-e-2")
        image_table.add_row("Stability AI", "stable-diffusion-xl, stable-diffusion-3")

        console.print(image_table)
        console.print()

        console.print("[dim]Use 'auto-video setup' to configure models.[/dim]")

        return 0

    if args.download:
        console.print("[yellow]Model download feature is not yet implemented.[/yellow]")
        console.print("[dim]Models will be downloaded automatically on first use.[/dim]")
        return 0

    console.print("[yellow]Use --list to see available models or --download to download.[/yellow]")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="auto-video",
        description="Automated video creation with AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version and exit",
    )

    parser.add_argument(
        "-c",
        "--config",
        type=str,
        help="Path to configuration file",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Setup command with subcommands
    setup_parser = subparsers.add_parser("setup", help="Run setup wizard")
    setup_subparsers = setup_parser.add_subparsers(
        dest="setup_subcommand", help="Setup subcommands"
    )

    # Run all wizards (default when no subcommand specified)
    setup_subparsers.add_parser("all", help="Run all setup wizards")

    # Individual wizard subcommands
    setup_subparsers.add_parser("llm", help="Run only LLM provider setup")
    setup_subparsers.add_parser("storage", help="Run only storage setup")
    setup_subparsers.add_parser("visuals", help="Run only visuals setup")
    setup_subparsers.add_parser("tts", help="Run only TTS and Images setup")
    setup_subparsers.add_parser("prompts", help="Run only prompts setup")
    setup_subparsers.add_parser("youtube", help="Run only YouTube setup")

    create_parser = subparsers.add_parser("create", help="Create a new video")
    create_parser.add_argument("--title", "-t", type=str, help="Video title")
    create_parser.add_argument("--auto", action="store_true", help="Auto-generate title")
    create_parser.add_argument(
        "--format", "-f", choices=["short", "long"], help="Video format (short or long)"
    )
    create_parser.add_argument(
        "--lang", "-l", type=str, default="fr", help="Video language (default: fr)"
    )
    create_parser.add_argument("--duration", "-d", type=int, help="Duration in seconds")
    create_parser.add_argument("--no-upload", action="store_true", help="Skip upload to YouTube")
    create_parser.add_argument("--keep-temp", action="store_true", help="Keep temporary files")
    create_parser.add_argument(
        "--dev", action="store_true", help="Development mode with detailed output"
    )

    resume_parser = subparsers.add_parser("resume", help="Resume video generation")
    resume_parser.add_argument("--video-id", type=str, required=True, help="Video ID to resume")
    resume_parser.add_argument("--step", type=int, help="Step number to resume from (1-7)")

    config_parser = subparsers.add_parser(
        "config",
        help="Manage configuration",
        description=(
            "Manage auto-video configuration.\n\n"
            "Examples:\n"
            "  auto-video config --show              View current configuration\n"
            "  auto-video config --edit              Open config file in editor\n"
            "  auto-video config --section llm       Edit LLM settings using wizard\n"
            "  auto-video config --section storage    Edit storage paths using wizard\n"
            "  auto-video config --section visuals    Edit visuals settings using wizard\n"
            "  auto-video config --section tts         Edit TTS settings using wizard\n"
            "  auto-video config --section image       Edit image generation settings using wizard\n"
            "  auto-video config --section youtube    Edit YouTube settings using wizard\n"
            "  auto-video config --section prompts    Edit prompt templates using wizard\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    config_parser.add_argument(
        "--show", action="store_true", help="Show current configuration in table format"
    )
    config_parser.add_argument(
        "--edit", action="store_true", help="Edit configuration file in default text editor"
    )
    config_parser.add_argument(
        "--section",
        type=str,
        choices=["llm", "storage", "visuals", "tts", "image", "youtube", "prompts"],
        help="Edit specific configuration section using interactive wizard (faster than full setup)",
    )

    models_parser = subparsers.add_parser("models", help="Manage AI models")
    models_parser.add_argument("--list", action="store_true", help="List available models")
    models_parser.add_argument("--download", action="store_true", help="Download models")

    args = parser.parse_args()

    if args.version:
        from auto_video import __version__

        print(f"auto-video {__version__}")
        return 0

    if not args.command:
        parser.print_help()
        return 0

    # Handle setup command with subcommands
    if args.command == "setup":
        # If no subcommand or subcommand is "all", run all wizards
        if not hasattr(args, "setup_subcommand") or args.setup_subcommand in (None, "all"):
            return cmd_setup()

        # Handle individual setup subcommands
        setup_subcommand_map = {
            "llm": cmd_setup_llm,
            "storage": cmd_setup_storage,
            "visuals": cmd_setup_visuals,
            "tts": cmd_setup_tts,
            "prompts": cmd_setup_prompts,
            "youtube": cmd_setup_youtube,
        }

        handler = setup_subcommand_map.get(args.setup_subcommand)
        if handler is None:
            console = Console()
            console.print(f"[red]Unknown setup subcommand: {args.setup_subcommand}[/red]")
            return 1

        try:
            return handler(args)
        except KeyboardInterrupt:
            console = Console()
            console.print("\n[yellow]Operation cancelled by user.[/yellow]")
            return 130
        except Exception as e:
            console = Console()
            console.print(f"\n[red]Error: {e}[/red]")
            return 1

    command_map: dict[str, CommandHandler] = {
        "setup": lambda _: cmd_setup(),
        "create": cmd_create,
        "resume": cmd_resume,
        "config": cmd_config,
        "models": cmd_models,
    }

    handler = command_map.get(args.command)

    if handler is None:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1

    try:
        return handler(args)
    except KeyboardInterrupt:
        console = Console()
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        return 130
    except Exception as e:
        console = Console()
        console.print(f"\n[red]Error: {e}[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
