"""
VTT (WebVTT) subtitle writer
"""
from pathlib import Path
from typing import Dict, Any
import logging

from transcribe_cli.core.postprocess import format_timestamp

logger = logging.getLogger(__name__)


def write_vtt(result: Dict[str, Any], output_path: Path) -> Path:
    """
    Write transcript to VTT (WebVTT) subtitle file
    
    VTT Format:
    WEBVTT
    
    00:00:00.000 --> 00:00:05.000
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
    
    # VTT requires timestamps - reject if not available
    if not segments or not any(seg.get('start') is not None for seg in segments):
        raise ValueError(
            "VTT format requires timestamps/segments. "
            "Use --format text/json or choose a model/response_format that returns segments. "
            "OpenAI Whisper API may not return segments for all response formats."
        )
    
    with open(output_path, 'w', encoding='utf-8') as f:
        # Write VTT header
        f.write("WEBVTT\n\n")
        
        for segment in segments:
            start = segment.get('start', 0)
            end = segment.get('end', 0)
            text = segment.get('text', '').strip()
            
            if not text:
                continue
            
            # Write VTT entry
            f.write(f"{format_timestamp(start, 'vtt')} --> {format_timestamp(end, 'vtt')}\n")
            f.write(f"{text}\n")
            f.write("\n")
    
    logger.info(f"VTT subtitle written: {output_path} ({len(segments)} segments)")
    
    return output_path
