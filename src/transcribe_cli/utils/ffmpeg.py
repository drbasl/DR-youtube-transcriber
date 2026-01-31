"""
FFmpeg wrapper for audio extraction and processing
"""
import subprocess
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class FFmpegError(Exception):
    """FFmpeg operation error"""
    pass


def check_ffmpeg_installed() -> bool:
    """Check if ffmpeg is installed and accessible"""
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def get_ffmpeg_installation_instructions() -> str:
    """Get platform-specific ffmpeg installation instructions"""
    import platform
    system = platform.system()
    
    instructions = {
        'Darwin': 'Install ffmpeg using Homebrew: brew install ffmpeg',
        'Linux': 'Install ffmpeg: sudo apt-get install ffmpeg (Ubuntu/Debian) or sudo yum install ffmpeg (CentOS/RHEL)',
        'Windows': 'Download ffmpeg from https://ffmpeg.org/download.html and add to PATH'
    }
    
    return instructions.get(system, 'Install ffmpeg from https://ffmpeg.org/download.html')


def extract_audio_from_video(
    video_path: Path,
    output_path: Path,
    sample_rate: int = 16000,
    channels: int = 1,
    verbose: bool = False
) -> Path:
    """
    Extract audio from video file and convert to mono WAV
    
    Args:
        video_path: Input video file
        output_path: Output audio file (WAV)
        sample_rate: Audio sample rate (default 16kHz for speech)
        channels: Number of audio channels (1=mono, 2=stereo)
        verbose: Show ffmpeg output
        
    Returns:
        Path to extracted audio file
        
    Raises:
        FFmpegError: If extraction fails
    """
    if not check_ffmpeg_installed():
        raise FFmpegError(
            f"ffmpeg is not installed or not in PATH.\n{get_ffmpeg_installation_instructions()}"
        )
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Build ffmpeg command
    cmd = [
        'ffmpeg',
        '-i', str(video_path),
        '-vn',  # No video
        '-acodec', 'pcm_s16le',  # PCM 16-bit
        '-ar', str(sample_rate),  # Sample rate
        '-ac', str(channels),  # Channels
        '-y',  # Overwrite output
        str(output_path)
    ]
    
    try:
        if verbose:
            logger.debug(f"Running ffmpeg: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else "Unknown error"
            raise FFmpegError(f"ffmpeg failed: {error_msg}")
        
        if verbose and result.stderr:
            logger.debug(f"ffmpeg output: {result.stderr}")
        
        if not output_path.exists():
            raise FFmpegError(f"Output file not created: {output_path}")
        
        return output_path
        
    except subprocess.TimeoutExpired:
        raise FFmpegError("ffmpeg timed out (>5 minutes)")
    except Exception as e:
        raise FFmpegError(f"Failed to extract audio: {e}")


def convert_audio_format(
    input_path: Path,
    output_path: Path,
    sample_rate: int = 16000,
    channels: int = 1,
    verbose: bool = False
) -> Path:
    """
    Convert audio to standardized format (mono, 16kHz WAV)
    
    Args:
        input_path: Input audio file
        output_path: Output audio file
        sample_rate: Target sample rate
        channels: Target channels
        verbose: Show ffmpeg output
        
    Returns:
        Path to converted audio file
    """
    if not check_ffmpeg_installed():
        raise FFmpegError(
            f"ffmpeg is not installed.\n{get_ffmpeg_installation_instructions()}"
        )
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        'ffmpeg',
        '-i', str(input_path),
        '-acodec', 'pcm_s16le',
        '-ar', str(sample_rate),
        '-ac', str(channels),
        '-y',
        str(output_path)
    ]
    
    try:
        if verbose:
            logger.debug(f"Converting audio: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            raise FFmpegError(f"Audio conversion failed: {result.stderr}")
        
        return output_path
        
    except subprocess.TimeoutExpired:
        raise FFmpegError("Audio conversion timed out")
    except Exception as e:
        raise FFmpegError(f"Failed to convert audio: {e}")


def get_audio_duration(file_path: Path) -> float:
    """
    Get audio duration in seconds using ffprobe
    
    Returns:
        Duration in seconds
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(file_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
        
        return 0.0
        
    except Exception as e:
        logger.warning(f"Could not get audio duration: {e}")
        return 0.0


def split_audio_chunk(
    input_path: Path,
    output_path: Path,
    start_time: float,
    duration: float,
    verbose: bool = False
) -> Path:
    """
    Extract a chunk of audio from start_time for duration seconds
    
    Args:
        input_path: Input audio file
        output_path: Output chunk file
        start_time: Start time in seconds
        duration: Duration in seconds
        verbose: Show ffmpeg output
        
    Returns:
        Path to audio chunk
    """
    if not check_ffmpeg_installed():
        raise FFmpegError("ffmpeg is not installed")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        'ffmpeg',
        '-ss', str(start_time),
        '-t', str(duration),
        '-i', str(input_path),
        '-acodec', 'copy',
        '-y',
        str(output_path)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            raise FFmpegError(f"Audio splitting failed: {result.stderr}")
        
        return output_path
        
    except Exception as e:
        raise FFmpegError(f"Failed to split audio: {e}")
