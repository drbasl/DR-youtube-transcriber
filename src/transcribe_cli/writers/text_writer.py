"""
Text writer for plain text output
"""
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def write_text(result: Dict[str, Any], output_path: Path) -> Path:
    """
    Write transcript to plain text file
    
    Args:
        result: Transcription result dictionary
        output_path: Output file path
        
    Returns:
        Path to written file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    transcript = result.get('transcript', '')
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(transcript)
    
    logger.info(f"Text transcript written: {output_path}")
    
    return output_path
