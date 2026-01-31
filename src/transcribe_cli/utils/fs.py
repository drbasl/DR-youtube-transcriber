"""
Filesystem utilities with security checks
"""
import os
import hashlib
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Allowed file extensions
ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.mkv', '.avi', '.webm', '.flv'}
ALLOWED_AUDIO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac', '.wma'}
ALLOWED_EXTENSIONS = ALLOWED_VIDEO_EXTENSIONS | ALLOWED_AUDIO_EXTENSIONS


def is_valid_media_file(file_path: Path) -> bool:
    """Check if file has valid media extension"""
    return file_path.suffix.lower() in ALLOWED_EXTENSIONS


def is_video_file(file_path: Path) -> bool:
    """Check if file is a video"""
    return file_path.suffix.lower() in ALLOWED_VIDEO_EXTENSIONS


def is_audio_file(file_path: Path) -> bool:
    """Check if file is audio"""
    return file_path.suffix.lower() in ALLOWED_AUDIO_EXTENSIONS


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal and other issues"""
    # Remove path separators
    filename = filename.replace('/', '_').replace('\\', '_')
    # Remove null bytes
    filename = filename.replace('\0', '')
    # Remove potentially dangerous characters
    dangerous_chars = '<>:"|?*'
    for char in dangerous_chars:
        filename = filename.replace(char, '_')
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    return filename


def safe_output_path(base_dir: Path, filename: str) -> Path:
    """
    Create safe output path preventing path traversal
    """
    base_dir = base_dir.resolve()
    sanitized = sanitize_filename(filename)
    output_path = (base_dir / sanitized).resolve()
    
    # Ensure output path is within base_dir
    try:
        output_path.relative_to(base_dir)
    except ValueError:
        raise ValueError(f"Path traversal detected: {filename}")
    
    return output_path


def ensure_dir(directory: Path) -> Path:
    """Ensure directory exists"""
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def get_file_hash(file_path: Path) -> str:
    """Get SHA256 hash of file for checkpoint identification"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read in chunks to handle large files
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()[:16]  # Use first 16 chars


def get_file_size(file_path: Path) -> int:
    """Get file size in bytes"""
    return file_path.stat().st_size


def create_temp_dir(base_dir: Path, prefix: str = "transcribe_") -> Path:
    """Create temporary directory"""
    import tempfile
    temp_dir = Path(tempfile.mkdtemp(prefix=prefix, dir=base_dir))
    return temp_dir


def cleanup_temp_files(temp_dir: Path, verbose: bool = False):
    """Cleanup temporary files"""
    if temp_dir.exists():
        try:
            import shutil
            shutil.rmtree(temp_dir)
            if verbose:
                logger.debug(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp directory {temp_dir}: {e}")
