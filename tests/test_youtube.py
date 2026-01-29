"""
Unit tests for YouTube features (no network/downloads)
"""
from pathlib import Path
from typer.testing import CliRunner

from transcribe_cli.cli import app
from transcribe_cli.utils.youtube import (
    build_ytdlp_captions_command,
    build_ytdlp_audio_command,
    parse_vtt_segments,
    captions_to_text,
    normalize_captions_text,
    strip_captions_timestamps
)


runner = CliRunner()


def test_youtube_command_help():
    result = runner.invoke(app, ["youtube", "--help"])
    assert result.exit_code == 0
    assert "youtube" in result.output.lower()


def test_build_ytdlp_captions_command_manual():
    cmd = build_ytdlp_captions_command("https://youtube.com/watch?v=abc", "ar", Path("./out"), auto=False)
    assert "yt-dlp" in cmd[0]
    assert "--write-subs" in cmd
    assert "--write-auto-subs" not in cmd
    assert "--sub-langs" in cmd
    assert "ar" in cmd


def test_build_ytdlp_captions_command_auto():
    cmd = build_ytdlp_captions_command("https://youtube.com/watch?v=abc", "en", Path("./out"), auto=True)
    assert "--write-auto-subs" in cmd
    assert "--write-subs" not in cmd


def test_build_ytdlp_audio_command():
    cmd = build_ytdlp_audio_command("https://youtube.com/watch?v=abc", Path("./out"))
    assert "-x" in cmd
    assert "--audio-format" in cmd
    assert "best" in cmd


def test_parse_vtt_segments_and_text():
    vtt_sample = """WEBVTT

00:00:01.000 --> 00:00:03.000
مرحبا بك

00:00:03.500 --> 00:00:05.000
نعم نعم هذا اختبار
"""
    segments = parse_vtt_segments(vtt_sample)
    assert len(segments) == 2
    assert segments[0]["start"] == 1.0
    assert segments[0]["end"] == 3.0

    text = captions_to_text(segments)
    assert "مرحبا" in text
    assert "اختبار" in text


def test_normalize_captions_text_removes_timestamps_and_tags():
    raw = """WEBVTT

00:00:01.000 --> 00:00:03.000 align:start position:0%
<c>مرحبا</c> بك

00:00:03.500 --> 00:00:05.000
<c>هذا</c> اختبار
"""
    cleaned = normalize_captions_text(raw)
    assert "WEBVTT" not in cleaned
    assert "-->" not in cleaned
    assert "<c>" not in cleaned
    assert "</c>" not in cleaned
    assert "align:" not in cleaned
    assert "00:00:01.000" not in cleaned
    assert "مرحبا" in cleaned
    assert "اختبار" in cleaned


def test_strip_captions_timestamps_removes_tokens():
    raw = """WEBVTT
NOTE this is a note

00:00:01.000 --> 00:00:03.000 align:start position:0% line:0% size:50%
<c>مرحبا</c> بك
"""
    cleaned = strip_captions_timestamps(raw)
    assert "WEBVTT" not in cleaned
    assert "NOTE" not in cleaned
    assert "-->" not in cleaned
    assert "<" not in cleaned
    assert "align:" not in cleaned
    assert "position:" not in cleaned
    assert "line:" not in cleaned
    assert "size:" not in cleaned
    assert "مرحبا" in cleaned