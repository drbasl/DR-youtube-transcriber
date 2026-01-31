"""
Post-processing utilities for transcripts
"""
import re
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text
    - Replace multiple spaces with single space
    - Remove leading/trailing whitespace
    - Normalize line breaks
    """
    # Replace multiple spaces/tabs with single space
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Replace multiple newlines with double newline
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)
    
    # Remove leading/trailing whitespace from entire text
    text = text.strip()
    
    return text


def remove_repeated_words(text: str) -> str:
    """
    Remove consecutive repeated words (e.g., "نعم نعم" -> "نعم").
    Applies to all languages but is intended for Arabic transcripts.
    """
    if not text:
        return ""

    # Replace consecutive duplicate words (case-insensitive, preserve first occurrence)
    def _dedupe_line(line: str) -> str:
        tokens = line.split()
        if not tokens:
            return line
        result = [tokens[0]]
        for token in tokens[1:]:
            if token.lower() != result[-1].lower():
                result.append(token)
        return " ".join(result)

    lines = [_dedupe_line(line) for line in text.split("\n")]
    return "\n".join(lines)


def format_arabic_text(text: str, language: str = "ar") -> str:
    """
    Light formatting for Arabic transcripts:
    - normalize whitespace
    - remove consecutive repeated words
    - add minimal punctuation
    """
    if not text:
        return ""

    text = normalize_whitespace(text)
    text = remove_repeated_words(text)
    text = add_minimal_punctuation(text, language=language)
    text = normalize_whitespace(text)

    return text


def apply_glossary(text: str, glossary: Dict[str, str]) -> str:
    """
    Apply glossary replacements to text
    
    Args:
        text: Input text
        glossary: Dictionary of {term: replacement}
        
    Returns:
        Text with replacements applied
    """
    if not glossary:
        return text
    
    # Sort by length (longest first) to handle overlapping terms
    sorted_terms = sorted(glossary.keys(), key=len, reverse=True)
    
    for term in sorted_terms:
        replacement = glossary[term]
        
        # Case-insensitive replacement, preserving whole words
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        text = pattern.sub(replacement, text)
    
    return text


def add_minimal_punctuation(text: str, language: str = "ar") -> str:
    """
    Add minimal punctuation to improve readability
    WITHOUT changing the meaning or adding content
    
    This is conservative - only adds periods at clear sentence boundaries
    """
    # Don't modify if already has good punctuation
    if text.count('.') > len(text) / 100:  # Already has punctuation
        return text
    
    # For Arabic, look for common sentence-ending patterns
    if language == "ar":
        # Add period after common ending patterns (if not already there)
        patterns = [
            (r'(\s)(شكرا|شكراً|والسلام|إن شاء الله)(\s)', r'\1\2.\3'),
            (r'(\s)(نعم|لا|حسناً|جيد|صحيح)(\s)', r'\1\2.\3'),
        ]
        
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text)
    
    # For English
    elif language == "en":
        patterns = [
            (r'(\s)(thank you|thanks|okay|yes|no)(\s)', r'\1\2.\3'),
        ]
        
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    return text


def clean_transcript(
    text: str,
    glossary: Optional[Dict[str, str]] = None,
    language: str = "ar",
    add_punctuation: bool = False
) -> str:
    """
    Clean and post-process transcript
    
    Args:
        text: Raw transcript text
        glossary: Optional glossary for term replacement
        language: Language code
        add_punctuation: Whether to add minimal punctuation
        
    Returns:
        Cleaned transcript
    """
    if not text:
        return ""
    
    # Step 1: Normalize whitespace
    text = normalize_whitespace(text)
    
    # Step 2: Apply glossary replacements
    if glossary:
        text = apply_glossary(text, glossary)
    
    # Step 3: Add minimal punctuation (optional)
    if add_punctuation:
        text = add_minimal_punctuation(text, language)
    
    # Step 4: Final whitespace normalization
    text = normalize_whitespace(text)
    
    return text


def extract_segments_from_response(response: Dict) -> list:
    """
    Extract segments with timestamps from OpenAI response
    
    Args:
        response: OpenAI API response (verbose_json format)
        
    Returns:
        List of segments with timestamps
    """
    segments = []
    
    if 'segments' in response:
        for seg in response['segments']:
            segments.append({
                'id': seg.get('id'),
                'start': seg.get('start', 0),
                'end': seg.get('end', 0),
                'text': seg.get('text', '').strip()
            })
    
    return segments


def format_timestamp(seconds: float, format: str = "srt") -> str:
    """
    Format timestamp for subtitle files
    
    Args:
        seconds: Time in seconds
        format: 'srt' or 'vtt'
        
    Returns:
        Formatted timestamp string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    
    if format == "srt":
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    else:  # vtt
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
