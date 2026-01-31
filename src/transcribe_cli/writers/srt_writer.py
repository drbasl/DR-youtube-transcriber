"""
SRT (SubRip) subtitle writer
"""
from pathlib import Path
from typing import Dict, Any, List
import logging

from transcribe_cli.core.postprocess import format_timestamp

logger = logging.getLogger(__name__)


def write_srt(result: Dict[str, Any], output_path: Path) -> Path:
    """
    Write transcript to SRT subtitle file
    
    SRT Format:
    1
    00:00:00,000 --> 00:00:05,000
    Subtitle text here
    
    Args:
        result: Transcription result dictionary
        output_path: Output file path
        
    Returns:
        Path to written file
        
    Raises:
        ValueError: If timestamps/segments not available
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    segments = result.get('segments', [])
    if segments is None:
        segments = []
    
    # SRT requires timestamps - reject if not available
    if not segments or not any(seg.get('start') is not None for seg in segments):
        raise ValueError(
            "SRT format requires timestamps/segments. "
            "Use --format text/json or choose a model/response_format that returns segments. "
            "OpenAI Whisper API may not return segments for all response formats."
        )
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(segments, 1):
            start = segment.get('start', 0)
            end = segment.get('end', 0)
            text = segment.get('text', '').strip()
            
            if not text:
                continue
            
            # Write SRT entry
            f.write(f"{i}\n")
            f.write(f"{format_timestamp(start, 'srt')} --> {format_timestamp(end, 'srt')}\n")
            f.write(f"{text}\n")
            f.write("\n")
    
    logger.info(f"SRT subtitle written: {output_path} ({len(segments)} segments)")
    
    return output_path
