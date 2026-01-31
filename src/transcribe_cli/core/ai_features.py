"""
AI Processing logic for summarization, key points, speech conversion, etc.
"""
from __future__ import annotations
import logging
from openai import AsyncOpenAI
from transcribe_cli.config import load_settings

logger = logging.getLogger(__name__)

async def generate_summary(text: str, length: str = "medium", model: str = None) -> str:
    """Generate a summary of the text."""
    settings = load_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    length_prompts = {
        "short": "very concise (bullet points)",
        "medium": "moderate length with key details",
        "detailed": "comprehensive and detailed"
    }
    
    prompt = f"""
    Summarize the following text in Arabic.
    Target length/style: {length_prompts.get(length, 'medium')}.
    
    Text:
    {text[:50000]}  # Limit context window if needed
    """
    
    response = await client.chat.completions.create(
        model=model or settings.openai_model or "gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content

async def extract_key_points(text: str, model: str = None) -> str:
    """Extract key points from the text."""
    settings = load_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    prompt = f"""
    Extract the main ideas from the following text as a numbered list in Arabic.
    Focus on the most important information.
    
    Text:
    {text[:50000]}
    """
    
    response = await client.chat.completions.create(
        model=model or settings.openai_model or "gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5
    )
    return response.choices[0].message.content

async def convert_to_speech(text: str, audience: str, model: str = None) -> str:
    """Convert text to a formal speech/letter."""
    settings = load_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    prompt = f"""
    Rewrite the following text as a formal speech or letter in Arabic.
    Target Audience: {audience}.
    Structure:
    1. Greeting (السلام عليكم ورحمة الله وبركاته)
    2. Introduction
    3. Body (Main Content)
    4. Conclusion
    5. Closing
    
    Use formal and professional language suitable for the audience.
    
    Text:
    {text[:50000]}
    """
    
    response = await client.chat.completions.create(
        model=model or settings.openai_model or "gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content

async def rewrite_text(text: str, style: str, structure: str, options: list[str], model: str = None) -> str:
    """Rewrite text with specific style and structure."""
    settings = load_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    options_str = ", ".join(options) if options else "None"
    
    prompt = f"""
    Rewrite the following text in Arabic.
    Style: {style}
    Structure: {structure}
    Additional Requirements: {options_str}
    
    Maintain the core meaning but adapt the tone and format effectively.
    
    Text:
    {text[:50000]}
    """
    
    response = await client.chat.completions.create(
        model=model or settings.openai_model or "gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    return response.choices[0].message.content

async def translate_text(text: str, target_lang: str, model: str = None) -> str:
    """Translate text to target language."""
    settings = load_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    prompt = f"""
    Translate the following text to {target_lang}.
    Ensure the translation is accurate and natural.
    
    Text:
    {text[:20000]} 
    """
    # 20k chars limit for translation safety
    
    response = await client.chat.completions.create(
        model=model or settings.openai_model or "gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return response.choices[0].message.content

async def generate_dubbing_audio(text: str, voice: str = "alloy") -> bytes:
    """Generate audio from text using OpenAI TTS."""
    settings = load_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    
    # TTS supports max 4096 chars per request roughly, we might need to chunk if text is long
    # For now, we truncate to safe limit
    safe_text = text[:4000]
    
    response = await client.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=safe_text
    )
    return response.read()
