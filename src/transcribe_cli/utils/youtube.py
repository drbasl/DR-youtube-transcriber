"""
Utilities for YouTube transcription via yt-dlp (captions or audio)
"""
from __future__ import annotations

import hashlib
import logging
import re
import subprocess
from pathlib import Path
from typing import Optional, Tuple, List

from transcribe_cli.core.postprocess import normalize_whitespace
from transcribe_cli.utils.ffmpeg import convert_audio_format

logger = logging.getLogger(__name__)


def build_ytdlp_captions_command(url: str, lang: str, output_dir: Path, auto: bool = False) -> List[str]:
    """Build yt-dlp command for downloading captions (manual or auto)."""
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--skip-download",
        "--sub-format",
        "vtt",
        "--sub-langs",
        lang,
        "-o",
        str(output_dir / "%(id)s.%(ext)s")
    ]

    if auto:
        cmd.insert(2, "--write-auto-subs")
    else:
        cmd.insert(2, "--write-subs")

    cmd.append(url)
    return cmd


def build_ytdlp_audio_command(url: str, output_dir: Path) -> List[str]:
    """
    Build yt-dlp command for downloading audio-only (best quality, any format).
    We will convert to WAV separately using ffmpeg.
    """
    return [
        "yt-dlp",
        "--no-playlist",
        "-x",
        "--audio-format",
        "best",  # Download best audio, we'll convert later
        "--audio-quality",
        "0",
        "-o",
        str(output_dir / "%(id)s.%(ext)s"),
        url
    ]


def youtube_safe_name(url: str) -> str:
    """Generate a stable filename token for a YouTube URL."""
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
    return f"youtube_{digest}"


def find_caption_file(output_dir: Path, lang: str) -> Optional[Path]:
    """Find a VTT captions file in the output directory."""
    candidates = list(output_dir.glob(f"*.{lang}.vtt"))
    if candidates:
        return candidates[0]

    # Fallback to any VTT if language-specific not found
    vtts = list(output_dir.glob("*.vtt"))
    return vtts[0] if vtts else None


def _parse_vtt_timestamp(ts: str) -> float:
    """Parse VTT timestamp to seconds (supports HH:MM:SS.mmm or MM:SS.mmm)."""
    parts = ts.split(":")
    if len(parts) == 3:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
    else:
        hours = 0
        minutes = int(parts[0])
        seconds = float(parts[1])
    return hours * 3600 + minutes * 60 + seconds


def parse_vtt_segments(vtt_text: str) -> List[dict]:
    """Parse VTT text into segments with start/end timestamps."""
    segments = []
    lines = [line.strip() for line in vtt_text.splitlines()]

    i = 0
    while i < len(lines):
        line = lines[i]
        if "-->" in line:
            try:
                start_str, end_str = [part.strip() for part in line.split("-->", 1)]
                start = _parse_vtt_timestamp(start_str.split(" ")[0])
                end = _parse_vtt_timestamp(end_str.split(" ")[0])
            except Exception:
                i += 1
                continue

            i += 1
            text_lines = []
            while i < len(lines) and lines[i]:
                text_lines.append(lines[i])
                i += 1

            text = " ".join(text_lines).strip()
            if text:
                segments.append({"start": start, "end": end, "text": text})
        else:
            i += 1

    return segments


def captions_to_text(segments: List[dict]) -> str:
    """Convert caption segments to a normalized text string."""
    text = " ".join(seg.get("text", "") for seg in segments if seg.get("text"))
    return normalize_whitespace(text)


def _strip_captions_lines(raw: str, merge_lines: bool = True) -> str:
    if not raw:
        return ""

    text = raw

    # Remove VTT headers and metadata lines
    text = re.sub(r"(?m)^(WEBVTT.*|STYLE.*|NOTE.*)$", "", text)

    # Remove timestamp lines
    text = re.sub(r"^\s*\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}\.\d{3}.*$", "", text, flags=re.MULTILINE)

    # Remove tags like <c>...</c>
    text = re.sub(r"<[^>]+>", "", text)

    # Remove align/position tokens inside lines
    text = re.sub(r"\b(align:\w+|position:\d+%|line:\d+%|size:\d+%)\b", "", text)

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    if merge_lines:
        text = " ".join(lines)
        return normalize_whitespace(text)

    return "\n".join(lines)


def strip_captions_timestamps(raw: str) -> str:
    """
    Remove timestamps/headers/tags and normalize captions to clean paragraphs.
    """
    return _strip_captions_lines(raw, merge_lines=True)


def strip_captions_timestamps_keep_lines(raw: str) -> str:
    """
    Remove timestamps/headers/tags but keep line breaks.
    """
    return _strip_captions_lines(raw, merge_lines=False)


def normalize_captions_text(raw: str) -> str:
    """
    Backward-compatible normalization for captions text.
    """
    return strip_captions_timestamps(raw)


def download_captions_text(url: str, lang: str, output_dir: Path) -> Tuple[str, List[dict], bool, str]:
    """
    Download captions (manual first, then auto) and return (text, segments, used_auto).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Try manual captions
    cmd_manual = build_ytdlp_captions_command(url, lang, output_dir, auto=False)
    subprocess.run(cmd_manual, capture_output=True, text=True, check=False)

    caption_file = find_caption_file(output_dir, lang)
    used_auto = False

    # If manual not found, try auto captions
    if not caption_file:
        cmd_auto = build_ytdlp_captions_command(url, lang, output_dir, auto=True)
        subprocess.run(cmd_auto, capture_output=True, text=True, check=False)
        caption_file = find_caption_file(output_dir, lang)
        used_auto = True

    if not caption_file or not caption_file.exists():
        raise FileNotFoundError("Captions not found for requested language")

    vtt_text = caption_file.read_text(encoding="utf-8", errors="ignore")
    segments = parse_vtt_segments(vtt_text)
    cleaned_text = normalize_captions_text(vtt_text)

    return cleaned_text, segments, used_auto, vtt_text


def download_audio(url: str, output_dir: Path) -> Path:
    """
    Download audio-only via yt-dlp, convert to WAV using ffmpeg.
    
    Args:
        url: YouTube URL
        output_dir: Directory to save files (should be .tmp folder)
    
    Returns:
        Path to normalized WAV file
    
    Raises:
        FileNotFoundError: If download or conversion fails
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Starting yt-dlp audio download to: {output_dir}")

    # Step 1: Download audio (any format)
    cmd = build_ytdlp_audio_command(url, output_dir)
    logger.debug(f"yt-dlp command: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    
    logger.info(f"yt-dlp exit code: {result.returncode}")
    if result.stdout:
        logger.debug(f"yt-dlp stdout (first 500 chars): {result.stdout[:500]}")
    if result.stderr:
        logger.debug(f"yt-dlp stderr (first 500 chars): {result.stderr[:500]}")
    
    if result.returncode != 0:
        raise FileNotFoundError(
            f"yt-dlp failed with exit code {result.returncode}. "
            f"Check stderr: {result.stderr[:200] if result.stderr else 'N/A'}"
        )

    # Step 2: Find downloaded audio file (any format: m4a, webm, opus, mp3, etc.)
    audio_files = []
    for ext in ['m4a', 'webm', 'opus', 'mp3', 'aac', 'wav', 'ogg']:
        audio_files.extend(output_dir.glob(f"*.{ext}"))
    
    if not audio_files:
        raise FileNotFoundError(
            f"Audio download failed: no audio files found in {output_dir}. "
            f"Expected formats: m4a, webm, opus, mp3, etc."
        )
    
    downloaded_path = audio_files[0]
    logger.info(f"Downloaded audio file: {downloaded_path} ({downloaded_path.stat().st_size} bytes)")

    # Step 3: Convert to WAV using ffmpeg
    wav_path = output_dir / f"{downloaded_path.stem}.wav"
    logger.info(f"Converting to WAV: {downloaded_path} -> {wav_path}")
    
    try:
        convert_audio_format(
            input_path=downloaded_path,
            output_path=wav_path,
            sample_rate=16000,
            channels=1,
            verbose=True
        )
    except Exception as e:
        logger.error(f"ffmpeg conversion failed: {e}")
        raise FileNotFoundError(f"ffmpeg conversion failed: {e}")
    
    # Step 4: Verify WAV file exists
    if not wav_path.exists():
        raise FileNotFoundError(
            f"WAV file not created after conversion: {wav_path}"
        )
    
    logger.info(f"WAV file ready: {wav_path} ({wav_path.stat().st_size} bytes)")
    return wav_path