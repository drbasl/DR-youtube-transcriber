"""
JSON writer for structured transcript output with metadata
"""
import json
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def write_json(result: Dict[str, Any], output_path: Path) -> Path:
    """
    Write transcript and metadata to JSON file
    
    Args:
        result: Transcription result dictionary
        output_path: Output file path
        
    Returns:
        Path to written file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Prepare JSON structure
    output_data = {
        'transcript': result.get('transcript', ''),
        'language': result.get('language', 'unknown'),
        'model': result.get('model', 'unknown'),
        'metadata': {
            'input_file': result.get('input_file', ''),
            'chunks': result.get('chunks', 0),
            'segments_count': len(result.get('segments', []))
        },
        'segments': result.get('segments', [])
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"JSON transcript written: {output_path}")
    
    return output_path
