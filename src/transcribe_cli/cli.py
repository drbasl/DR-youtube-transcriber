"""
CLI interface for transcribe-cli using Typer
"""
import asyncio
import sys
from pathlib import Path
from typing import Optional
import logging

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from transcribe_cli.config import TranscribeConfig, load_settings
from transcribe_cli.core.pipeline import transcribe_file
from transcribe_cli.utils.logging import setup_logger, log_info, log_success, log_error, log_warning
from transcribe_cli.utils.fs import (
    is_valid_media_file,
    ensure_dir,
    safe_output_path
)
from transcribe_cli.utils.youtube import download_captions_text, download_audio, youtube_safe_name
from transcribe_cli.writers.text_writer import write_text
from transcribe_cli.writers.json_writer import write_json
from transcribe_cli.writers.srt_writer import write_srt
from transcribe_cli.writers.vtt_writer import write_vtt

# Validate settings on import
try:
    _settings = load_settings()
except ValueError as e:
    # load_settings will handle proper error output and exit
    pass

app = typer.Typer(
    name="transcribe",
    help="CLI tool for transcribing video/audio to text using OpenAI Speech-to-Text",
    add_completion=False
)

console = Console()


@app.command()
def main(
    input_path: Path = typer.Argument(
        ...,
        help="Path to input video/audio file",
        exists=True,
        dir_okay=False,
        resolve_path=True
    ),
    lang: str = typer.Option(
        "ar",
        "--lang",
        help="Language code (ar, en, fr, etc.)"
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        help="OpenAI model name (default: whisper-1)"
    ),
    format: str = typer.Option(
        "text",
        "--format",
        help="Output format: text, json, srt, vtt"
    ),
    out: Path = typer.Option(
        Path("./out"),
        "--out",
        help="Output directory"
    ),
    diarize: bool = typer.Option(
        False,
        "--diarize",
        help="Enable speaker diarization (if supported)"
    ),
    chunk_minutes: int = typer.Option(
        5,
        "--chunk-minutes",
        help="Chunk duration in minutes"
    ),
    max_bytes_per_chunk: int = typer.Option(
        20971520,
        "--max-bytes-per-chunk",
        help="Maximum chunk size in bytes (default 20MB)"
    ),
    glossary: Optional[Path] = typer.Option(
        None,
        "--glossary",
        help="Path to glossary file for term replacements"
    ),
    resume: bool = typer.Option(
        True,
        "--resume",
        help="Resume from checkpoint if available"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Enable verbose logging"
    )
):
    """
    Transcribe a single audio/video file to text
    
    Example:
        transcribe ./video.mp4 --lang ar --format text --out ./output
    """
    # Setup logging
    logger = setup_logger("transcribe_cli", verbose)
    
    try:
        # Validate input file
        if not is_valid_media_file(input_path):
            log_error(f"Unsupported file type: {input_path.suffix}")
            log_info("Supported formats: mp4, mov, mkv, avi, mp3, wav, m4a, aac, ogg, flac")
            sys.exit(1)
        
        # Validate format
        valid_formats = ['text', 'json', 'srt', 'vtt']
        if format not in valid_formats:
            log_error(f"Invalid format: {format}. Must be one of: {', '.join(valid_formats)}")
            sys.exit(1)
        
        # Ensure output directory exists
        ensure_dir(out)
        
        # Validate glossary if provided
        if glossary and not glossary.exists():
            log_warning(f"Glossary file not found: {glossary}")
            glossary = None
        
        # Create configuration
        config = TranscribeConfig(
            input_path=input_path,
            output_dir=out,
            language=lang,
            model=model,
            output_format=format,
            diarize=diarize,
            chunk_minutes=chunk_minutes,
            max_bytes_per_chunk=max_bytes_per_chunk,
            glossary_path=glossary,
            resume=resume,
            verbose=verbose
        )
        
        log_info(f"Transcribing: {input_path.name}")
        log_info(f"Language: {lang} | Format: {format} | Output: {out}")
        
        # Run transcription
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Processing...", total=None)
            
            try:
                result = asyncio.run(transcribe_file(config))
            finally:
                progress.remove_task(task)
        
        # Write output
        try:
            output_file = _write_output(result, config, out)
        except ValueError as e:
            log_error(f"Output format error: {e}")
            sys.exit(1)
        
        log_success(f"Transcription complete!")
        log_info(f"Output: {output_file}")
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        log_warning("\nTranscription cancelled by user")
        sys.exit(130)
    
    except Exception as e:
        log_error(f"Transcription failed: {e}")
        if verbose:
            logger.exception("Full error traceback:")
        sys.exit(1)


@app.command()
def youtube(
    url: str = typer.Argument(
        ...,
        help="YouTube video URL"
    ),
    lang: str = typer.Option(
        "ar",
        "--lang",
        help="Language code"
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        help="OpenAI model name (default: whisper-1)"
    ),
    format: str = typer.Option(
        "text",
        "--format",
        help="Output format: text, json, srt, vtt"
    ),
    out: Path = typer.Option(
        Path("./out"),
        "--out",
        help="Output directory"
    ),
    chunk_minutes: int = typer.Option(
        5,
        "--chunk-minutes",
        help="Chunk duration in minutes"
    ),
    max_bytes_per_chunk: int = typer.Option(
        20971520,
        "--max-bytes-per-chunk",
        help="Maximum chunk size in bytes (default 20MB)"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Enable verbose logging"
    ),
    source: str = typer.Option(
        "captions",
        "--source",
        help="Source: captions or audio"
    )
):
    """
    Transcribe a YouTube video via captions or audio.
    """
    logger = setup_logger("transcribe_cli", verbose)

    try:
        valid_formats = ['text', 'json', 'srt', 'vtt']
        if format not in valid_formats:
            log_error(f"Invalid format: {format}. Must be one of: {', '.join(valid_formats)}")
            sys.exit(1)

        if source not in ["captions", "audio"]:
            log_error("Invalid source. Use 'captions' or 'audio'.")
            sys.exit(1)

        ensure_dir(out)
        temp_dir = ensure_dir(out / ".tmp")

        if source == "captions":
            try:
                text, segments, used_auto = download_captions_text(url, lang, temp_dir)
            except FileNotFoundError:
                log_error("No captions found for requested language.")
                sys.exit(1)

            if used_auto:
                log_warning("Auto captions were used (lower accuracy).")

            duration_seconds = 0.0
            if segments:
                duration_seconds = max(seg.get("end", 0) for seg in segments)

            result = {
                "transcript": text,
                "language": lang,
                "model": "youtube-captions",
                "chunks": 0,
                "input_file": url,
                "duration": duration_seconds,
                "segments": segments
            }

            config = TranscribeConfig(
                input_path=Path(f"{youtube_safe_name(url)}.mp4"),
                output_dir=out,
                language=lang,
                model="youtube-captions",
                output_format=format,
                chunk_minutes=chunk_minutes,
                max_bytes_per_chunk=max_bytes_per_chunk,
                resume=False,
                verbose=verbose
            )

            output_file = _write_output(result, config, out)
            log_success("YouTube captions transcript complete!")
            log_info(f"Output: {output_file}")

        else:
            # Download audio and use existing pipeline
            audio_path = download_audio(url, temp_dir)

            config = TranscribeConfig(
                input_path=audio_path,
                output_dir=out,
                language=lang,
                model=model,
                output_format=format,
                chunk_minutes=chunk_minutes,
                max_bytes_per_chunk=max_bytes_per_chunk,
                resume=True,
                verbose=verbose
            )

            result = asyncio.run(transcribe_file(config))
            output_file = _write_output(result, config, out)
            log_success("YouTube audio transcription complete!")
            log_info(f"Output: {output_file}")

        if not verbose:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

        sys.exit(0)

    except KeyboardInterrupt:
        log_warning("\nYouTube transcription cancelled by user")
        sys.exit(130)

    except Exception as e:
        log_error(f"YouTube transcription failed: {e}")
        if verbose:
            logger.exception("Full error traceback:")
        sys.exit(1)


@app.command()
def batch(
    folder: Path = typer.Argument(
        ...,
        help="Path to folder containing media files",
        exists=True,
        file_okay=False,
        resolve_path=True
    ),
    lang: str = typer.Option(
        "ar",
        "--lang",
        help="Language code"
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        help="OpenAI model name"
    ),
    format: str = typer.Option(
        "text",
        "--format",
        help="Output format: text, json, srt, vtt"
    ),
    out: Path = typer.Option(
        Path("./out"),
        "--out",
        help="Output directory"
    ),
    diarize: bool = typer.Option(
        False,
        "--diarize",
        help="Enable speaker diarization"
    ),
    chunk_minutes: int = typer.Option(
        5,
        "--chunk-minutes",
        help="Chunk duration in minutes"
    ),
    max_bytes_per_chunk: int = typer.Option(
        20971520,
        "--max-bytes-per-chunk",
        help="Maximum chunk size in bytes"
    ),
    glossary: Optional[Path] = typer.Option(
        None,
        "--glossary",
        help="Path to glossary file"
    ),
    resume: bool = typer.Option(
        True,
        "--resume",
        help="Resume from checkpoint"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Enable verbose logging"
    )
):
    """
    Transcribe multiple files from a folder
    
    Example:
        transcribe batch ./media_folder --lang ar --format text --out ./output
    """
    logger = setup_logger("transcribe_cli", verbose)
    
    try:
        # Find all media files
        media_files = []
        for file_path in folder.iterdir():
            if file_path.is_file() and is_valid_media_file(file_path):
                media_files.append(file_path)
        
        if not media_files:
            log_warning(f"No media files found in: {folder}")
            sys.exit(0)
        
        log_info(f"Found {len(media_files)} media files")
        
        ensure_dir(out)
        
        # Process each file
        success_count = 0
        failed_files = []
        
        for i, file_path in enumerate(media_files, 1):
            log_info(f"\n[{i}/{len(media_files)}] Processing: {file_path.name}")
            
            try:
                config = TranscribeConfig(
                    input_path=file_path,
                    output_dir=out,
                    language=lang,
                    model=model,
                    output_format=format,
                    diarize=diarize,
                    chunk_minutes=chunk_minutes,
                    max_bytes_per_chunk=max_bytes_per_chunk,
                    glossary_path=glossary,
                    resume=resume,
                    verbose=verbose
                )
                
                result = asyncio.run(transcribe_file(config))
                output_file = _write_output(result, config, out)
                
                log_success(f"✓ {file_path.name} -> {output_file.name}")
                success_count += 1
                
            except Exception as e:
                log_error(f"✗ Failed: {file_path.name} - {e}")
                failed_files.append(file_path.name)
                if verbose:
                    logger.exception("Error details:")
        
        # Summary
        console.print("\n" + "=" * 50)
        log_info(f"Batch processing complete")
        log_info(f"Success: {success_count}/{len(media_files)}")
        
        if failed_files:
            log_warning(f"Failed files: {', '.join(failed_files)}")
            sys.exit(1)
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        log_warning("\nBatch processing cancelled")
        sys.exit(130)
    
    except Exception as e:
        log_error(f"Batch processing failed: {e}")
        if verbose:
            logger.exception("Full error traceback:")
        sys.exit(1)


def _write_output(result: dict, config: TranscribeConfig, output_dir: Path) -> Path:
    """
    Write transcription result to file in specified format
    
    Args:
        result: Transcription result dictionary
        config: Transcription configuration
        output_dir: Output directory
        
    Returns:
        Path to written file
    """
    # Generate output filename
    base_name = config.input_path.stem
    
    # Map format to extension and writer
    format_map = {
        'text': ('txt', write_text),
        'json': ('json', write_json),
        'srt': ('srt', write_srt),
        'vtt': ('vtt', write_vtt)
    }
    
    extension, writer_func = format_map[config.output_format]
    output_filename = f"{base_name}_transcript.{extension}"
    
    # Create safe output path
    output_path = safe_output_path(output_dir, output_filename)
    
    # Write using appropriate writer
    return writer_func(result, output_path)


if __name__ == "__main__":
    app()
