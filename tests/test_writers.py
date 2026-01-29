"""
Tests for output writers
"""
import pytest
from pathlib import Path
import json

from transcribe_cli.writers.text_writer import write_text
from transcribe_cli.writers.json_writer import write_json
from transcribe_cli.writers.srt_writer import write_srt
from transcribe_cli.writers.vtt_writer import write_vtt


@pytest.fixture
def sample_result():
    """Sample transcription result with segments"""
    return {
        'transcript': 'This is a sample transcript with some text.',
        'language': 'en',
        'model': 'whisper-1',
        'chunks': 2,
        'input_file': 'test.mp4',
        'segments': [
            {'start': 0.0, 'end': 5.0, 'text': 'This is a sample transcript'},
            {'start': 5.0, 'end': 10.0, 'text': 'with some text.'}
        ]
    }


@pytest.fixture
def sample_result_no_segments():
    """Sample result without segments"""
    return {
        'transcript': 'Simple transcript without timestamps.',
        'language': 'ar',
        'model': 'whisper-1',
        'chunks': 1,
        'input_file': 'test.wav',
        'segments': []
    }


def test_text_writer(tmp_path, sample_result):
    """Test text writer"""
    output_file = tmp_path / "transcript.txt"
    
    result_path = write_text(sample_result, output_file)
    
    assert result_path.exists()
    assert result_path == output_file
    
    content = output_file.read_text(encoding='utf-8')
    assert sample_result['transcript'] in content


def test_text_writer_creates_parent_dirs(tmp_path, sample_result):
    """Test that text writer creates parent directories"""
    output_file = tmp_path / "subdir" / "nested" / "transcript.txt"
    
    result_path = write_text(sample_result, output_file)
    
    assert result_path.exists()
    assert result_path.parent.exists()


def test_json_writer(tmp_path, sample_result):
    """Test JSON writer"""
    output_file = tmp_path / "transcript.json"
    
    result_path = write_json(sample_result, output_file)
    
    assert result_path.exists()
    
    with open(output_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    assert data['transcript'] == sample_result['transcript']
    assert data['language'] == 'en'
    assert data['model'] == 'whisper-1'
    assert len(data['segments']) == 2
    assert 'metadata' in data


def test_json_writer_structure(tmp_path, sample_result):
    """Test JSON output structure"""
    output_file = tmp_path / "transcript.json"
    
    write_json(sample_result, output_file)
    
    with open(output_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Check required fields
    assert 'transcript' in data
    assert 'language' in data
    assert 'model' in data
    assert 'metadata' in data
    assert 'segments' in data
    
    # Check metadata structure
    assert 'input_file' in data['metadata']
    assert 'chunks' in data['metadata']
    assert 'segments_count' in data['metadata']


def test_srt_writer(tmp_path, sample_result):
    """Test SRT writer with segments"""
    output_file = tmp_path / "transcript.srt"
    
    result_path = write_srt(sample_result, output_file)
    
    assert result_path.exists()
    
    content = output_file.read_text(encoding='utf-8')
    
    # Check SRT format
    assert '1\n' in content  # First subtitle index
    assert '00:00:00,000 --> 00:00:05,000' in content
    assert 'This is a sample transcript' in content
    assert '2\n' in content  # Second subtitle index


def test_srt_writer_no_segments_raises_error(tmp_path, sample_result_no_segments):
    """Test SRT writer raises error without segments"""
    output_file = tmp_path / "transcript.srt"
    
    with pytest.raises(ValueError) as exc_info:
        write_srt(sample_result_no_segments, output_file)
    
    assert "timestamps" in str(exc_info.value).lower()
    assert "not available" in str(exc_info.value).lower()


def test_vtt_writer(tmp_path, sample_result):
    """Test VTT writer with segments"""
    output_file = tmp_path / "transcript.vtt"
    
    result_path = write_vtt(sample_result, output_file)
    
    assert result_path.exists()
    
    content = output_file.read_text(encoding='utf-8')
    
    # Check VTT format
    assert content.startswith('WEBVTT\n')
    assert '00:00:00.000 --> 00:00:05.000' in content
    assert 'This is a sample transcript' in content
    assert 'with some text.' in content


def test_vtt_writer_no_segments_raises_error(tmp_path, sample_result_no_segments):
    """Test VTT writer raises error without segments"""
    output_file = tmp_path / "transcript.vtt"
    
    with pytest.raises(ValueError) as exc_info:
        write_vtt(sample_result_no_segments, output_file)
    
    assert "timestamps" in str(exc_info.value).lower()
    assert "not available" in str(exc_info.value).lower()


def test_all_writers_handle_unicode(tmp_path):
    """Test that all writers handle Unicode correctly"""
    arabic_result = {
        'transcript': 'مرحبا بك في اختبار النص العربي',
        'language': 'ar',
        'model': 'whisper-1',
        'chunks': 1,
        'input_file': 'test.mp4',
        'segments': [
            {'start': 0.0, 'end': 5.0, 'text': 'مرحبا بك في اختبار النص العربي'}
        ]
    }
    
    # Test text writer
    text_file = tmp_path / "arabic.txt"
    write_text(arabic_result, text_file)
    content = text_file.read_text(encoding='utf-8')
    assert 'مرحبا' in content
    
    # Test JSON writer
    json_file = tmp_path / "arabic.json"
    write_json(arabic_result, json_file)
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert 'مرحبا' in data['transcript']
    
    # Test SRT writer
    srt_file = tmp_path / "arabic.srt"
    write_srt(arabic_result, srt_file)
    content = srt_file.read_text(encoding='utf-8')
    assert 'مرحبا' in content
    
    # Test VTT writer
    vtt_file = tmp_path / "arabic.vtt"
    write_vtt(arabic_result, vtt_file)
    content = vtt_file.read_text(encoding='utf-8')
    assert 'مرحبا' in content


def test_writers_handle_empty_segments(tmp_path):
    """Test that writers handle segments with empty text"""
    result = {
        'transcript': 'Valid text',
        'language': 'en',
        'model': 'whisper-1',
        'chunks': 1,
        'input_file': 'test.mp4',
        'segments': [
            {'start': 0.0, 'end': 5.0, 'text': 'Valid text'},
            {'start': 5.0, 'end': 6.0, 'text': ''},  # Empty
            {'start': 6.0, 'end': 10.0, 'text': '   '},  # Whitespace only
        ]
    }
    
    # SRT should skip empty segments
    srt_file = tmp_path / "test.srt"
    write_srt(result, srt_file)
    content = srt_file.read_text(encoding='utf-8')
    # Should only have one subtitle
    assert content.count('\n\n') <= 2  # One segment + final newline
    
    # VTT should skip empty segments
    vtt_file = tmp_path / "test.vtt"
    write_vtt(result, vtt_file)
    content = vtt_file.read_text(encoding='utf-8')
    assert content.count('-->') == 1  # Only one timestamp line
