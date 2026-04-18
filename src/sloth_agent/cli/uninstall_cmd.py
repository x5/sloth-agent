"""sloth uninstall CLI command — remove Sloth Agent from the system."""

import os
import shutil
import sys
from pathlib import Path

import typer
from rich.console import Console

console = Console(force_terminal=True, color_system="auto")

PATH_COMMENT = "# Sloth Agent"


def uninstall(
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview what would be removed without deleting"),
    full: bool = typer.Option(False, "--full", "-f", help="Also remove user configuration and API keys"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
):
    """Uninstall Sloth Agent from the system.

    Removes CLI shim, PATH modifications, and the installation directory.
    Use --full to also remove user configuration and API keys.
    """
    sloth_dir = Path.home() / ".sloth-agent"
    items = _collect_items(sloth_dir, full)

    console.print("[bold]Sloth Agent Uninstaller[/bold]")
    console.print()

    if dry_run:
        console.print("[bold yellow]Dry run — the following would be removed:[/bold yellow]")
    else:
        console.print("[bold red]The following will be removed:[/bold red]")

    for item in items:
        console.print(f"  [red]-[/red] {item}")

    # Show PATH cleanup targets
    shell_rcs = _find_shell_profiles()
    lines_to_remove = []
    for rc in shell_rcs:
        if rc.exists():
            for i, line in enumerate(rc.read_text().splitlines()):
                if PATH_COMMENT in line:
                    lines_to_remove.append((rc, i, line.strip()))

    if lines_to_remove:
        console.print()
        console.print("PATH lines to clean from shell profiles:")
        for rc, idx, line in lines_to_remove:
            console.print(f"  [red]-[/red] {rc.relative_to(Path.home())}: {line}")

    if dry_run:
        console.print()
        console.print("[dim]Run without --dry-run to actually uninstall.[/dim]")
        return

    # Confirm before destructive action
    if not yes:
        console.print()
        confirm = console.input("[bold red]Continue? (y/N): [/bold red]")
        if confirm.strip().lower() not in ("y", "yes"):
            console.print("Uninstall cancelled.")
            raise typer.Exit(0)

    # Remove shell profile lines
    _clean_shell_profiles(lines_to_remove)

    # Remove files and directories
    for item in items:
        p = Path(os.path.expandvars(item)) if "~" in item or "$" in item else Path(item)
        p = p.expanduser()
        if p.exists():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
            console.print(f"  [green]✓[/green] Removed {item}")

    console.print()
    console.print("[bold green]Uninstall complete.[/bold green]")
    console.print()
    console.print("[dim]Note: If your terminal session is still running from this shell, the PATH change will not take effect until you restart.[/dim]")


def _collect_items(sloth_dir: Path, full: bool) -> list[str]:
    """Collect all items that will be removed, as human-readable paths."""
    home = Path.home()
    items = []

    # CLI shim scripts
    local_bin = home / ".local" / "bin"
    for shim in [local_bin / "sloth", local_bin / "sloth.ps1", local_bin / "sloth.bat"]:
        if shim.exists():
            items.append(str(shim))

    # Always remove the main installation directory
    if sloth_dir.exists():
        items.append(str(sloth_dir))

    return items


def _find_shell_profiles() -> list[Path]:
    """Find shell profile files that may contain Sloth Agent PATH entries."""
    home = Path.home()
    profiles = []

    # Unix
    for name in [".zshrc", ".bashrc", ".profile"]:
        p = home / name
        if p.exists():
            profiles.append(p)

    # Windows PowerShell profile
    if sys.platform == "win32":
        import subprocess
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "$PROFILE"],
                capture_output=True, text=True, timeout=5,
            )
            profile_path = result.stdout.strip()
            if profile_path and Path(profile_path).exists():
                profiles.append(Path(profile_path))
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        # Also check bashrc on Windows (for Git Bash / WSL)
        bashrc = home / ".bashrc"
        if bashrc.exists() and bashrc not in profiles:
            profiles.append(bashrc)

    return profiles


def _clean_shell_profiles(lines_to_remove: list[tuple[Path, int, str]]) -> None:
    """Remove Sloth Agent PATH lines from shell profiles."""
    if not lines_to_remove:
        return

    # Group by file
    by_file: dict[Path, list[int]] = {}
    for rc, idx, _ in lines_to_remove:
        by_file.setdefault(rc, []).append(idx)

    for rc, indices in by_file.items():
        content = rc.read_text().splitlines()
        # Also remove adjacent empty lines around the removed lines
        remove_set = set(indices)
        for idx in indices:
            if idx + 1 < len(content) and content[idx + 1].strip() == "":
                remove_set.add(idx + 1)
            if idx - 1 >= 0 and content[idx - 1].strip() == "":
                remove_set.add(idx - 1)

        new_content = [line for i, line in enumerate(content) if i not in remove_set]
        rc.write_text("\n".join(new_content) + "\n" if new_content else "")
