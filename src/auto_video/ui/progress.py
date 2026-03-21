"""Progress display UI for pipeline execution."""

from dataclasses import dataclass
from typing import Literal

from rich.console import Console
from rich.live import Live
from rich.markup import escape
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn, TimeRemainingColumn
from rich.table import Table
from rich.text import Text


@dataclass
class StepStatus:
    index: int
    status: Literal["pending", "running", "completed", "failed"]
    details: str = ""
    error: str | None = None
    artifact_path: str | None = None
    script_content: str | None = None


class PipelineProgressDisplay:
    """TUI for displaying pipeline progress with steps on left and details on right."""

    # Refresh only called in explicit state transition methods (start_step, complete_step,
    # fail_step) to prevent flooding Live with rapid updates that cause screen
    # duplication. State setter methods (update_*) only update data without refresh.

    def __init__(self, steps: list[str]) -> None:
        self.console = Console()
        self.steps = steps
        self.step_statuses: list[StepStatus] = [
            StepStatus(index=i, status="pending", details="") for i in range(len(steps))
        ]
        self.global_progress = 0.0
        self._live: Live | None = None
        self._current_step_index = -1

        self._progress_bar = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=None),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=self.console,
            transient=False,
        )
        self._global_task = self._progress_bar.add_task(
            "Génération de la vidéo en cours", total=100
        )

    def start(self) -> None:
        self._live = Live(self._render(), console=self.console, transient=False)
        self._live.start()

    def stop(self) -> None:
        if self._live is not None:
            # Use context manager to ensure proper cleanup
            self._live.stop()
            self._live = None

    def start_step(self, step_index: int, description: str = "") -> None:
        """Mark a step as running."""
        if 0 <= step_index < len(self.step_statuses):
            self._current_step_index = step_index
            self.step_statuses[step_index].status = "running"
            self.step_statuses[step_index].details = description
            self.step_statuses[step_index].error = None
            self._refresh()

    def complete_step(self, step_index: int, details: str = "") -> None:
        """Mark a step as completed."""
        if 0 <= step_index < len(self.step_statuses):
            self.step_statuses[step_index].status = "completed"
            self.step_statuses[step_index].details = details
            self._update_global_progress()
            self._refresh()

    def fail_step(self, step_index: int, error: str) -> None:
        """Mark a step as failed."""
        if 0 <= step_index < len(self.step_statuses):
            self.step_statuses[step_index].status = "failed"
            self.step_statuses[step_index].error = error
            self._refresh()

    def update_step_details(self, step_index: int, details: str) -> None:
        """Update the details of a running step."""
        if 0 <= step_index < len(self.step_statuses):
            self.step_statuses[step_index].details = details

    def update_artifact_path(self, step_index: int, path: str) -> None:
        """Update the artifact path for a step."""
        if 0 <= step_index < len(self.step_statuses):
            self.step_statuses[step_index].artifact_path = path

    def update_script_content(self, script: str) -> None:
        """Update the script content displayed in details."""
        if 0 <= len(self.step_statuses) > 0:
            self.step_statuses[0].script_content = script

    def update_global_progress(self, progress: float) -> None:
        """Update the global progress percentage."""
        self.global_progress = min(max(progress, 0.0), 100.0)
        self._progress_bar.update(self._global_task, completed=self.global_progress)
        self._refresh()

    def _update_global_progress(self) -> None:
        """Calculate and update global progress based on completed steps."""
        completed = sum(1 for s in self.step_statuses if s.status == "completed")
        total = len(self.steps)
        if total > 0:
            self.global_progress = (completed / total) * 100
            self._progress_bar.update(self._global_task, completed=self.global_progress)

    def _refresh(self) -> None:
        if self._live is not None:
            self._live.update(self._render())

    def _render(self) -> Panel:
        left_panel = self._build_steps_panel()
        right_panel = self._build_details_panel()

        main_content = Table.grid(expand=True)
        main_content.add_column(ratio=1)
        main_content.add_column(ratio=2)
        main_content.add_row(left_panel, right_panel)

        global_progress_panel = Panel(
            self._progress_bar,
            border_style="green",
            padding=(0, 1),
        )

        full_content = Table.grid(expand=True)
        full_content.add_column()
        full_content.add_row(main_content)
        full_content.add_row(global_progress_panel)

        return Panel(
            full_content,
            title="[bold blue]🎬 AUTO-VIDEO - Génération de vidéo[/bold blue]",
            border_style="blue",
            padding=(1, 2),
        )

    def _build_steps_panel(self) -> Panel:
        """Build the left panel showing all steps."""
        table = Table.grid(padding=(0, 1), expand=True)
        table.add_column()

        for idx, step in enumerate(self.steps):
            status_obj = self.step_statuses[idx]
            icon = self._get_status_icon(status_obj.status)
            style = self._get_status_style(status_obj.status)

            if status_obj.status == "running":
                row = f"[{style} bold]▶[/] [{style} bold]{step}[/] ◄"
            else:
                row = f"[{style}]{icon}[/] [{style}]{step}[/]"

            table.add_row(row)

        return Panel(
            table,
            title="[bold cyan]📋 Étapes[/bold cyan]",
            border_style="cyan",
            expand=True,
        )

    def _build_details_panel(self) -> Panel:
        """Build the right panel showing details of current step."""
        current_idx = self._current_step_index

        if current_idx >= 0 and current_idx < len(self.step_statuses):
            status_obj = self.step_statuses[current_idx]
            step_name = self.steps[current_idx]

            details_table = Table.grid(padding=(0, 1), expand=True)
            details_table.add_column()

            details_table.add_row("[bold yellow]■[/] [bold yellow]Étape actuelle:[/bold yellow]")
            details_table.add_row(f"[bold cyan]{step_name}[/bold cyan]")
            details_table.add_row("")

            if status_obj.details:
                details_table.add_row("[dim]Détails:[/dim]")
                details_table.add_row(f"[white]{status_obj.details}[/white]")
                details_table.add_row("")

            if status_obj.artifact_path:
                details_table.add_row("[dim]Chemin:[/dim]")
                details_table.add_row(f"[bright_blue]{status_obj.artifact_path}[/bright_blue]")
                details_table.add_row("")

            if status_obj.status == "failed" and status_obj.error:
                details_table.add_row("[bold red]✗ Erreur:[/bold red]")
                details_table.add_row(f"[red]{status_obj.error}[/red]")
            else:
                details_table.add_row("[dim]Statut:[/dim]")
                status_text = self._get_status_text(status_obj.status)
                status_style = self._get_status_style(status_obj.status)
                details_table.add_row(f"[{status_style}]{status_text}[/{status_style}]")

            script_shown = False
            for idx, step in enumerate(self.step_statuses):
                if idx != current_idx and step.status in ("completed", "failed"):
                    details_table.add_row("")
                    details_table.add_row(f"[dim]└ {self.steps[idx]}:[/dim]")
                    if step.status == "completed":
                        details_table.add_row(f"[green]  ✓ {step.details or 'Terminé'}[/green]")
                        if step.artifact_path:
                            path_short = step.artifact_path
                            if len(path_short) > 50:
                                path_short = "..." + path_short[-47:]
                            details_table.add_row(f"[dim]    📁 {path_short}[/dim]")
                    elif step.status == "failed" and step.error:
                        error_preview = (
                            step.error[:50] + "..." if len(step.error) > 50 else step.error
                        )
                        details_table.add_row(f"[red]  ✗ {error_preview}[/red]")

                if idx == 0 and step.script_content and not script_shown:
                    details_table.add_row("")
                    details_table.add_row("[dim]└ Script généré:[/dim]")
                    script_preview = step.script_content
                    if len(script_preview) > 300:
                        script_preview = script_preview[:300] + "..."
                    details_table.add_row(
                        f"[dim white italic]  {script_preview}[/dim white italic]"
                    )
                    script_shown = True

            renderable = details_table
        else:
            details_table = Table.grid(padding=(0, 1), expand=True)
            details_table.add_column()
            details_table.add_row(Text("[dim]En attente du démarrage...[/dim]", justify="center"))
            renderable = details_table

        return Panel(
            renderable,
            title="[bold yellow]🔍 Détails de l'étape[/bold yellow]",
            border_style="yellow",
            expand=True,
        )

    def _get_status_icon(self, status: str) -> str:
        icons = {
            "pending": "○",
            "running": "▶",
            "completed": "✓",
            "failed": "✗",
        }
        return icons.get(status, "○")

    def _get_status_style(self, status: str) -> str:
        styles = {
            "pending": "dim",
            "running": "yellow",
            "completed": "green",
            "failed": "red",
        }
        return styles.get(status, "dim")

    def _get_status_text(self, status: str) -> str:
        texts = {
            "pending": "En attente",
            "running": "En cours...",
            "completed": "Terminé",
            "failed": "Échoué",
        }
        return texts.get(status, "Inconnu")


class DevProgressDisplay:
    """Simple linear progress display for development mode."""

    def __init__(self, steps: list[str]) -> None:
        self.console = Console()
        self.steps = steps
        self._current_step_index = -1
        self._commands: list[dict[str, str]] = []
        # Force flush of any pending logs before printing step headers
        import logging
        import sys

        self._sys_stdout = sys.stdout
        self._logging_handlers = logging.getLogger().handlers

    def _flush_logs(self) -> None:
        """Flush any pending log output before printing."""
        self._sys_stdout.flush()
        # Also flush any logging handlers
        for handler in self._logging_handlers:
            if hasattr(handler, "stream"):
                handler.stream.flush()

    def start(self) -> None:
        self._flush_logs()
        self.console.print("[bold cyan]🔧 MODE DÉVELOPPEMENT - Exécution du pipeline[/bold cyan]")
        self.console.print(
            "[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]"
        )
        self.console.print()

    def stop(self) -> None:
        self._flush_logs()
        self.console.print()
        self.console.print(
            "[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]"
        )
        self.console.print("[bold green]✓ Pipeline terminé[/bold green]")

    def start_step(self, step_index: int, description: str = "") -> None:
        """Mark a step as running."""
        if 0 <= step_index < len(self.steps):
            self._flush_logs()  # Flush logs before printing step header
            self._current_step_index = step_index
            self.console.print(
                f"\n[bold yellow]▶ Étape {step_index + 1}/{len(self.steps)}: "
                f"{self.steps[step_index]}[/bold yellow]"
            )
            if description:
                self.console.print(f"[dim]  {description}[/dim]")
            self.console.print(
                "[dim]  ─────────────────────────────────────────────────────────────[/dim]"
            )

    def complete_step(self, step_index: int, details: str = "") -> None:
        """Mark a step as completed."""
        if 0 <= step_index < len(self.steps):
            self.console.print(f"[green]  ✓ {self.steps[step_index]} terminé[/green]")
            if details:
                self.console.print(f"[dim]  {details}[/dim]")

    def fail_step(self, step_index: int, error: str) -> None:
        """Mark a step as failed."""
        if 0 <= step_index < len(self.steps):
            self.console.print(f"[bold red]  ✗ {self.steps[step_index]} échoué[/bold red]")
            self.console.print(f"[red]  Erreur: {escape(error)}[/red]")

    def update_step_details(self, step_index: int, details: str) -> None:
        """Update the details of a running step."""
        if 0 <= step_index < len(self.steps):
            self.console.print(f"[dim]  → {escape(details)}[/dim]")

    def update_global_progress(self, progress: float) -> None:
        """Update the global progress percentage."""
        pass

    def update_artifact_path(self, step_index: int, path: str) -> None:
        """Update the artifact path for a step."""
        if 0 <= step_index < len(self.steps):
            self.console.print(f"[dim]  📁 Fichier: {escape(path)}[/dim]")

    def update_script_content(self, script: str) -> None:
        """Update the script content displayed in details."""
        self.console.print(f"[dim]  📝 Script généré ({len(script)} caractères)[/dim]")
        self.console.print(f"[dim]  {escape(script[:200])}...[/dim]")

    def log_command(self, command: str) -> None:
        """Log a command being executed."""
        self.console.print(f"[cyan]  $ {escape(command)}[/cyan]")

    def log_command_output(self, output: str) -> None:
        """Log command output."""
        for line in output.strip().split("\n"):
            if line:
                self.console.print(f"[dim]  {escape(line)}[/dim]")

    def log_command_error(self, error: str) -> None:
        """Log command error."""
        self.console.print(f"[red]  ✗ Erreur: {escape(error)}[/red]")
