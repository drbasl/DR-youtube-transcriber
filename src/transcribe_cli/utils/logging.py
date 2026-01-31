"""
Logging utilities for transcribe-cli
"""
import logging
import sys
from typing import Optional
from rich.console import Console
from rich.logging import RichHandler

console = Console()


def setup_logger(name: str, verbose: bool = False) -> logging.Logger:
    """Setup logger with appropriate level and handlers"""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, console=console)]
    )
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    return logger


def log_info(message: str, logger: Optional[logging.Logger] = None):
    """Log info message"""
    if logger:
        logger.info(message)
    else:
        console.print(f"[blue]ℹ[/blue] {message}")


def log_success(message: str, logger: Optional[logging.Logger] = None):
    """Log success message"""
    if logger:
        logger.info(message)
    else:
        console.print(f"[green]✓[/green] {message}")


def log_warning(message: str, logger: Optional[logging.Logger] = None):
    """Log warning message"""
    if logger:
        logger.warning(message)
    else:
        console.print(f"[yellow]⚠[/yellow] {message}")


def log_error(message: str, logger: Optional[logging.Logger] = None):
    """Log error message"""
    if logger:
        logger.error(message)
    else:
        console.print(f"[red]✗[/red] {message}", file=sys.stderr)
