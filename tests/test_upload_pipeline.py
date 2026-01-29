import asyncio
from pathlib import Path

from transcribe_cli.config import TranscribeConfig
from transcribe_cli.core.pipeline import TranscriptionPipeline


class DummyChunkingManager:
    def __init__(self, chunks):
        self.chunks = chunks

    def get_full_transcript(self):
        return "hello world"

    def cleanup(self):
        return None


async def _run_pipeline_with_mocks(tmp_path: Path):
    dummy_audio = tmp_path / "dummy.wav"
    dummy_audio.write_bytes(b"RIFF" + b"0" * 1024)

    config = TranscribeConfig(
        input_path=dummy_audio,
        output_dir=tmp_path,
        language="ar",
        model="whisper-1",
        output_format="text",
        diarize=False,
        max_bytes_per_chunk=5 * 1024 * 1024
    )

    pipeline = TranscriptionPipeline(config)

    async def _prepare_audio():
        return dummy_audio

    def _setup_chunking(_audio_path):
        return DummyChunkingManager(chunks=[object()])

    async def _transcribe_chunks(_chunking_mgr):
        return None

    def _collect_segments(_chunking_mgr):
        return None

    pipeline._prepare_audio = _prepare_audio
    pipeline._setup_chunking = _setup_chunking
    pipeline._transcribe_chunks = _transcribe_chunks
    pipeline._collect_segments = _collect_segments

    result = await pipeline.run()
    return result


def test_upload_pipeline_contracts(tmp_path):
    result = asyncio.run(_run_pipeline_with_mocks(tmp_path))

    assert isinstance(result, dict)
    assert "text" in result
    assert "chunks_count" in result
    assert "duration_seconds" in result
    assert "segments" in result
    assert "warnings" in result

    assert isinstance(result["segments"], list)
    assert isinstance(result["warnings"], list)
    assert isinstance(result["chunks_count"], int)
