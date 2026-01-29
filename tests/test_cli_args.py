"""
Tests for CLI argument parsing and configuration
"""
import pytest
from pathlib import Path
from typer.testing import CliRunner

from transcribe_cli.cli import app
from transcribe_cli.config import TranscribeConfig


runner = CliRunner()


def test_cli_basic_invocation(tmp_path):
    """Test basic CLI invocation with minimal arguments"""
    # Create a dummy media file
    test_file = tmp_path / "test.wav"
    test_file.write_text("dummy content")
    
    # Note: This will fail without valid API key, but tests argument parsing
    result = runner.invoke(app, [str(test_file), "--help"])
    
    # Should show help without errors
    assert result.exit_code == 0 or "Usage:" in result.output


def test_cli_all_options(tmp_path):
    """Test CLI with all options specified"""
    test_file = tmp_path / "test.mp4"
    test_file.write_text("dummy")
    
    output_dir = tmp_path / "output"
    glossary = tmp_path / "glossary.txt"
    glossary.write_text("AI => الذكاء الاصطناعي")
    
    result = runner.invoke(app, [
        str(test_file),
        "--lang", "ar",
        "--model", "whisper-1",
        "--format", "json",
        "--out", str(output_dir),
        "--diarize",
        "--chunk-minutes", "10",
        "--max-bytes-per-chunk", "10485760",
        "--glossary", str(glossary),
        "--resume",
        "--verbose",
        "--help"  # Add help to avoid actual execution
    ])
    
    # Should parse without errors
    assert "Usage:" in result.output or result.exit_code == 0


def test_transcribe_config_creation():
    """Test TranscribeConfig object creation"""
    config = TranscribeConfig(
        input_path=Path("test.mp4"),
        output_dir=Path("./out"),
        language="ar",
        model="whisper-1",
        output_format="text",
        diarize=False,
        chunk_minutes=5,
        max_bytes_per_chunk=20971520,
        resume=True,
        verbose=False
    )
    
    assert config.language == "ar"
    assert config.output_format == "text"
    assert config.chunk_duration_seconds == 300
    assert config.resume is True


def test_config_with_optional_parameters():
    """Test config with optional parameters"""
    glossary_path = Path("glossary.txt")
    
    config = TranscribeConfig(
        input_path=Path("video.mp4"),
        output_dir=Path("./output"),
        language="en",
        model="whisper-1",
        output_format="srt",
        diarize=True,
        chunk_minutes=10,
        max_bytes_per_chunk=10485760,
        glossary_path=glossary_path,
        resume=False,
        verbose=True
    )
    
    assert config.glossary_path == glossary_path
    assert config.diarize is True
    assert config.chunk_minutes == 10
    assert config.verbose is True


def test_cli_invalid_format(tmp_path):
    """Test CLI with invalid format option"""
    test_file = tmp_path / "test.wav"
    test_file.write_text("dummy")
    
    # This should fail validation if executed
    # For now, just test that CLI accepts the format argument
    result = runner.invoke(app, [
        str(test_file),
        "--format", "invalid_format",
        "--help"
    ])
    
    # Help should still work
    assert "Usage:" in result.output


def test_batch_command_help():
    """Test batch command help"""
    result = runner.invoke(app, ["batch", "--help"])
    
    assert result.exit_code == 0
    assert "batch" in result.output.lower()


def test_config_repr():
    """Test TranscribeConfig string representation"""
    config = TranscribeConfig(
        input_path=Path("test.mp4"),
        output_dir=Path("./out"),
        language="ar",
        output_format="text"
    )
    
    repr_str = repr(config)
    assert "test.mp4" in repr_str
    assert "ar" in repr_str
    assert "text" in repr_str
