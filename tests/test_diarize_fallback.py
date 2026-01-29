"""
Tests for diarization fallback behavior
"""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from transcribe_cli.adapters.openai_client import OpenAIClient, OpenAITranscriptionError


@pytest.fixture
def dummy_audio_file(tmp_path):
    """Create a dummy audio file"""
    audio_file = tmp_path / "test_audio.wav"
    audio_file.write_bytes(b"RIFF" + b"\x00" * 100)
    return audio_file


@pytest.mark.asyncio
async def test_diarize_fallback_on_400_error(dummy_audio_file):
    """Test that diarization falls back to regular transcription on 400 error"""
    client = OpenAIClient(api_key="test-key")
    
    # Mock the transcribe_audio method to fail on first call, succeed on second
    with patch.object(client, 'transcribe_audio', new_callable=AsyncMock) as mock_transcribe:
        # First call (diarization attempt) raises error
        mock_transcribe.side_effect = [
            OpenAITranscriptionError("API error 400: Diarization not supported"),
            {'text': 'Fallback transcript', 'segments': []}
        ]
        
        result = await client.transcribe_with_diarization(
            audio_path=dummy_audio_file,
            language="ar",
            model="whisper-1"
        )
        
        assert result['text'] == 'Fallback transcript'
        assert mock_transcribe.call_count == 2


@pytest.mark.asyncio
async def test_diarize_no_fallback_on_other_errors(dummy_audio_file):
    """Test that non-400 errors are not caught for fallback"""
    client = OpenAIClient(api_key="test-key")
    
    with patch.object(client, 'transcribe_audio', new_callable=AsyncMock) as mock_transcribe:
        # Raise non-400 error
        mock_transcribe.side_effect = OpenAITranscriptionError("API error 401: Unauthorized")
        
        with pytest.raises(OpenAITranscriptionError):
            await client.transcribe_with_diarization(
                audio_path=dummy_audio_file,
                language="ar",
                model="whisper-1"
            )


@pytest.mark.asyncio
async def test_diarize_success_with_segments(dummy_audio_file):
    """Test successful diarization with speaker info"""
    client = OpenAIClient(api_key="test-key")
    
    with patch.object(client, 'transcribe_audio', new_callable=AsyncMock) as mock_transcribe:
        mock_transcribe.return_value = {
            'text': 'Speaker 1: Hello. Speaker 2: Hi.',
            'segments': [
                {'start': 0, 'end': 2, 'text': 'Hello'}
            ]
        }
        
        result = await client.transcribe_with_diarization(
            audio_path=dummy_audio_file,
            language="ar",
            model="whisper-1"
        )
        
        assert 'segments' in result
        assert result['text'] == 'Speaker 1: Hello. Speaker 2: Hi.'
