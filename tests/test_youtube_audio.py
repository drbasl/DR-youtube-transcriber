"""
Unit tests for YouTube audio download functionality
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from transcribe_cli.utils.youtube import (
    build_ytdlp_audio_command,
    download_audio
)


def test_build_ytdlp_audio_command():
    """Test that audio command uses 'best' format instead of wav"""
    output_dir = Path("/tmp/test")
    url = "https://www.youtube.com/watch?v=test123"
    
    cmd = build_ytdlp_audio_command(url, output_dir)
    
    assert "yt-dlp" in cmd
    assert "-x" in cmd
    assert "--audio-format" in cmd
    # Should use 'best' not 'wav'
    assert "best" in cmd
    assert "wav" not in cmd
    assert url in cmd


def test_build_ytdlp_audio_command_output_template():
    """Test that output template is in out/.tmp for safety"""
    output_dir = Path("out/.tmp")
    url = "https://www.youtube.com/watch?v=test"
    
    cmd = build_ytdlp_audio_command(url, output_dir)
    
    # Check -o flag points to correct directory
    o_index = cmd.index("-o")
    output_template = cmd[o_index + 1]
    assert "out" in output_template or ".tmp" in output_template


@patch('transcribe_cli.utils.youtube.subprocess.run')
@patch('transcribe_cli.utils.youtube.convert_audio_format')
def test_download_audio_success(mock_convert, mock_run):
    """Test successful audio download and conversion"""
    output_dir = Path("/tmp/test_audio")
    url = "https://www.youtube.com/watch?v=test"
    
    # Mock successful yt-dlp execution
    mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")
    
    # Create mock m4a file
    with patch.object(Path, 'mkdir'):
        with patch.object(Path, 'glob') as mock_glob:
            mock_m4a = Mock(spec=Path)
            mock_m4a.stem = "test_video"
            mock_m4a.stat.return_value.st_size = 1024000
            mock_glob.return_value = [mock_m4a]
            
            # Mock WAV file existence
            with patch.object(Path, 'exists', return_value=True):
                # Mock WAV file stat
                with patch.object(Path, 'stat') as mock_stat:
                    mock_stat.return_value.st_size = 2048000
                    
                    result = download_audio(url, output_dir)
                    
                    # Verify yt-dlp was called
                    assert mock_run.called
                    
                    # Verify conversion was called
                    assert mock_convert.called
                    args = mock_convert.call_args[1]
                    assert args['sample_rate'] == 16000
                    assert args['channels'] == 1
                    
                    # Verify result is WAV path
                    assert isinstance(result, Path)
                    assert result.suffix == ".wav"


@patch('transcribe_cli.utils.youtube.subprocess.run')
def test_download_audio_ytdlp_failure(mock_run):
    """Test yt-dlp failure with proper error message"""
    output_dir = Path("/tmp/test_audio")
    url = "https://www.youtube.com/watch?v=test"
    
    # Mock failed yt-dlp execution
    mock_run.return_value = Mock(
        returncode=1, 
        stdout="",
        stderr="ERROR: Video unavailable"
    )
    
    with patch.object(Path, 'mkdir'):
        with pytest.raises(FileNotFoundError) as exc_info:
            download_audio(url, output_dir)
        
        # Check error message contains details
        error_msg = str(exc_info.value)
        assert "yt-dlp failed" in error_msg
        assert "exit code 1" in error_msg


@patch('transcribe_cli.utils.youtube.subprocess.run')
def test_download_audio_no_file_found(mock_run):
    """Test error when no audio file downloaded"""
    output_dir = Path("/tmp/test_audio")
    url = "https://www.youtube.com/watch?v=test"
    
    # Mock successful yt-dlp but no files created
    mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")
    
    with patch.object(Path, 'mkdir'):
        with patch.object(Path, 'glob', return_value=[]):
            with pytest.raises(FileNotFoundError) as exc_info:
                download_audio(url, output_dir)
            
            error_msg = str(exc_info.value)
            assert "no audio files found" in error_msg
            assert "m4a" in error_msg  # Should mention expected formats


@patch('transcribe_cli.utils.youtube.subprocess.run')
@patch('transcribe_cli.utils.youtube.convert_audio_format')
def test_download_audio_ffmpeg_failure(mock_convert, mock_run):
    """Test ffmpeg conversion failure"""
    output_dir = Path("/tmp/test_audio")
    url = "https://www.youtube.com/watch?v=test"
    
    # Mock successful yt-dlp
    mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")
    
    # Mock ffmpeg failure
    mock_convert.side_effect = Exception("ffmpeg not found")
    
    with patch.object(Path, 'mkdir'):
        with patch.object(Path, 'glob') as mock_glob:
            mock_m4a = Mock(spec=Path)
            mock_m4a.stem = "test_video"
            mock_m4a.stat.return_value.st_size = 1024000
            mock_glob.return_value = [mock_m4a]
            
            with pytest.raises(FileNotFoundError) as exc_info:
                download_audio(url, output_dir)
            
            error_msg = str(exc_info.value)
            assert "ffmpeg conversion failed" in error_msg


@patch('transcribe_cli.utils.youtube.subprocess.run')
@patch('transcribe_cli.utils.youtube.convert_audio_format')
def test_download_audio_wav_not_created(mock_convert, mock_run):
    """Test error when WAV file not created after conversion"""
    output_dir = Path("/tmp/test_audio")
    url = "https://www.youtube.com/watch?v=test"
    
    # Mock successful yt-dlp
    mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")
    
    # Mock successful conversion but file doesn't exist
    mock_convert.return_value = None
    
    with patch.object(Path, 'mkdir'):
        with patch.object(Path, 'glob') as mock_glob:
            mock_m4a = Mock(spec=Path)
            mock_m4a.stem = "test_video"
            mock_m4a.stat.return_value.st_size = 1024000
            mock_glob.return_value = [mock_m4a]
            
            # WAV doesn't exist
            with patch.object(Path, 'exists', return_value=False):
                with pytest.raises(FileNotFoundError) as exc_info:
                    download_audio(url, output_dir)
                
                error_msg = str(exc_info.value)
                assert "WAV file not created" in error_msg


def test_download_audio_handles_multiple_formats():
    """Test that function searches for multiple audio formats"""
    from transcribe_cli.utils.youtube import download_audio
    
    # This is more of a code review test - verify the formats list
    import inspect
    source = inspect.getsource(download_audio)
    
    # Should check for common audio formats
    assert "'m4a'" in source
    assert "'webm'" in source
    assert "'opus'" in source
    assert "'mp3'" in source
