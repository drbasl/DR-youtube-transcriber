"""
Configuration management using pydantic-settings with dotenv support
"""
import os
import sys
from pathlib import Path
from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv


# Load .env file at startup
def _load_env():
    """Load environment variables from .env file"""
    env_path = Path.cwd() / '.env'
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Try to load from common locations
        for possible_env in [Path('.env'), Path(__file__).parent.parent.parent / '.env']:
            if possible_env.exists():
                load_dotenv(possible_env)
                break


# Load env immediately on import
_load_env()


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )
    
    # OpenAI Configuration
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key (required)"
    )
    
    openai_api_base: str = Field(
        default="https://api.openai.com/v1",
        description="OpenAI API base URL"
    )
    
    openai_model: str = Field(
        default="whisper-1",
        description="Default OpenAI model for transcription"
    )
    
    # Request settings
    request_timeout: int = Field(
        default=300,
        description="HTTP request timeout in seconds"
    )
    
    max_retries: int = Field(
        default=3,
        description="Maximum number of retries for failed requests"
    )
    
    retry_delay: float = Field(
        default=1.0,
        description="Initial delay between retries (exponential backoff)"
    )
    
    @field_validator('openai_api_key')
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate that API key is set and not placeholder"""
        v = v.strip() if v else ""
        
        if not v or v == "your-api-key-here":
            _print_api_key_error()
            sys.exit(1)
        
        return v


def _print_api_key_error():
    """Print helpful error message for missing API key"""
    from rich.console import Console
    console = Console()
    
    console.print("\n[red]✗ Error: OPENAI_API_KEY not set[/red]\n")
    console.print("Setup instructions:\n")
    console.print("[cyan]1. Copy .env.example to .env:[/cyan]")
    console.print("   Windows CMD:      copy .env.example .env")
    console.print("   Windows PowerShell: cp .env.example .env")
    console.print("   macOS/Linux:      cp .env.example .env\n")
    
    console.print("[cyan]2. Edit .env and add your API key:[/cyan]")
    console.print("   Windows CMD:      notepad .env")
    console.print("   Windows PowerShell: code .env  (or notepad .env)")
    console.print("   macOS/Linux:      nano .env\n")
    
    console.print("[cyan]3. Replace 'your-api-key-here' with your actual key:[/cyan]")
    console.print("   OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx\n")
    
    console.print("[yellow]Get your API key at:[/yellow]")
    console.print("   https://platform.openai.com/api-keys\n")


class TranscribeConfig:
    """Configuration for a transcription job"""
    
    def __init__(
        self,
        input_path: Path,
        output_dir: Path,
        language: str = "ar",
        model: Optional[str] = None,
        output_format: str = "text",
        diarize: bool = False,
        chunk_minutes: int = 5,
        max_bytes_per_chunk: int = 25 * 1024 * 1024,  # 25MB (OpenAI limit)
        glossary_path: Optional[Path] = None,
        resume: bool = True,
        verbose: bool = False
    ):
        self.input_path = input_path
        self.output_dir = output_dir
        self.language = language
        self.model = model
        self.output_format = output_format
        self.diarize = diarize
        self.chunk_minutes = chunk_minutes
        self.max_bytes_per_chunk = max_bytes_per_chunk
        self.glossary_path = glossary_path
        self.resume = resume
        self.verbose = verbose
        
        # Derived properties
        self.chunk_duration_seconds = chunk_minutes * 60
    
    def __repr__(self) -> str:
        return (
            f"TranscribeConfig(input={self.input_path.name}, "
            f"lang={self.language}, format={self.output_format})"
        )


def load_settings() -> Settings:
    """Load and validate application settings"""
    try:
        return Settings()
    except Exception as e:
        raise ValueError(f"Configuration error: {e}")


def load_glossary(glossary_path: Path) -> dict[str, str]:
    """
    Load glossary from file
    
    Format:
        term1 => replacement1
        term2 => replacement2
    or simple:
        term1
        term2
    """
    glossary = {}
    
    if not glossary_path.exists():
        return glossary
    
    with open(glossary_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if '=>' in line:
                parts = line.split('=>', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    glossary[key] = value
    
    return glossary
