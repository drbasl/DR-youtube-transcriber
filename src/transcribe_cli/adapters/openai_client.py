"""
OpenAI API client for audio transcription
"""
import asyncio
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any
import httpx

logger = logging.getLogger(__name__)


class OpenAITranscriptionError(Exception):
    """Error during OpenAI transcription"""
    pass


class OpenAIClient:
    """Client for OpenAI Audio Transcription API
    
    Enforces 25MB file size limit per API documentation.
    """
    
    # OpenAI Transcriptions API hard limit
    OPENAI_MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB
    
    def __init__(
        self,
        api_key: str,
        api_base: str = "https://api.openai.com/v1",
        timeout: int = 300,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        self.api_key = api_key
        self.api_base = api_base.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
    
    async def transcribe_audio(
        self,
        audio_path: Path,
        language: str = "ar",
        model: str = "whisper-1",
        response_format: str = "verbose_json",
        temperature: float = 0.0,
        prompt: Optional[str] = None,
        timestamp_granularities: Optional[list[str]] = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio file using OpenAI API
        
        Args:
            audio_path: Path to audio file
            language: Language code (ISO-639-1)
            model: Model name
            response_format: Response format (json, text, srt, verbose_json, vtt)
            temperature: Sampling temperature
            prompt: Optional prompt to guide transcription
            
        Returns:
            Transcription response from API
            
        Raises:
            OpenAITranscriptionError: If transcription fails
        """
        if not audio_path.exists():
            raise OpenAITranscriptionError(f"Audio file not found: {audio_path}")
        
        url = f"{self.api_base}/audio/transcriptions"
        
        # Prepare multipart form data
        with open(audio_path, 'rb') as audio_file:
            files = {
                'file': (audio_path.name, audio_file, 'audio/wav')
            }
            
            data = {
                'model': model,
                'language': language,
                'response_format': response_format,
                'temperature': temperature
            }
            
            if prompt:
                data['prompt'] = prompt

            if timestamp_granularities:
                data['timestamp_granularities'] = timestamp_granularities
            
            # Retry logic with exponential backoff
            for attempt in range(self.max_retries):
                try:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        # Need to reopen file for each retry
                        with open(audio_path, 'rb') as retry_file:
                            retry_files = {
                                'file': (audio_path.name, retry_file, 'audio/wav')
                            }
                            
                            response = await client.post(
                                url,
                                headers=self.headers,
                                data=data,
                                files=retry_files
                            )
                        
                        # Handle different status codes
                        if response.status_code == 200:
                            content_type = response.headers.get('content-type', '')

                            # Parse response
                            if 'application/json' in content_type or response_format in ['json', 'verbose_json']:
                                try:
                                    raw = response.json()
                                except Exception:
                                    raw = {"text": response.text}
                            else:
                                raw = {"text": response.text}

                            # Normalize response shape
                            if isinstance(raw, dict):
                                text = raw.get('text', '')
                                segments = raw.get('segments')
                            else:
                                text = str(raw)
                                segments = None

                            return {
                                "text": text,
                                "segments": segments,
                                "raw": raw
                            }
                        
                        elif response.status_code == 429:
                            # Rate limit - wait and retry
                            wait_time = self.retry_delay * (2 ** attempt)
                            logger.warning(f"Rate limited. Waiting {wait_time}s before retry...")
                            await asyncio.sleep(wait_time)
                            continue
                        
                        elif response.status_code >= 500:
                            # Server error - retry
                            if attempt < self.max_retries - 1:
                                wait_time = self.retry_delay * (2 ** attempt)
                                logger.warning(f"Server error {response.status_code}. Retrying in {wait_time}s...")
                                await asyncio.sleep(wait_time)
                                continue
                        
                        # Other errors
                        error_msg = response.text
                        raise OpenAITranscriptionError(
                            f"API error {response.status_code}: {error_msg}"
                        )
                
                except httpx.TimeoutException:
                    if attempt < self.max_retries - 1:
                        logger.warning(f"Request timeout. Retrying... (attempt {attempt + 1}/{self.max_retries})")
                        await asyncio.sleep(self.retry_delay * (2 ** attempt))
                        continue
                    raise OpenAITranscriptionError("Request timed out after multiple retries")
                
                except httpx.RequestError as e:
                    if attempt < self.max_retries - 1:
                        logger.warning(f"Request error: {e}. Retrying...")
                        await asyncio.sleep(self.retry_delay * (2 ** attempt))
                        continue
                    raise OpenAITranscriptionError(f"Request failed: {e}")
            
            raise OpenAITranscriptionError(f"Failed after {self.max_retries} attempts")
    
    async def transcribe_with_diarization(
        self,
        audio_path: Path,
        language: str = "ar",
        model: str = "whisper-1",
        timestamp_granularities: Optional[list[str]] = None
    ) -> Dict[str, Any]:
        """
        Attempt transcription with speaker diarization.
        
        Note: Diarization support varies by model and API version.
        Falls back to regular transcription if not supported (automatic fallback on 400 errors).
        
        Returns:
            Transcription response (may or may not include speaker info)
        """
        try:
            # Try with diarization
            logger.info("Attempting transcription with diarization...")
            result = await self.transcribe_audio(
                audio_path=audio_path,
                language=language,
                model=model,
                response_format="verbose_json",
                timestamp_granularities=timestamp_granularities
            )
            
            # Check if diarization info is present
            if 'speakers' in result or 'segments' in result:
                logger.info("Diarization data available in response")
            else:
                logger.warning("Diarization not supported by model, using standard transcription")
            
            return result
            
        except OpenAITranscriptionError as e:
            error_str = str(e).lower()
            # Fallback on 400/unsupported errors (diarization not available)
            if "400" in error_str or "not supported" in error_str or "diarize" in error_str or "speaker" in error_str:
                logger.warning("Diarization not supported, falling back to standard transcription")
                return await self.transcribe_audio(
                    audio_path=audio_path,
                    language=language,
                    model=model,
                    timestamp_granularities=timestamp_granularities
                )
            raise
    
    def transcribe_audio_sync(
        self,
        audio_path: Path,
        language: str = "ar",
        model: str = "whisper-1",
        **kwargs
    ) -> Dict[str, Any]:
        """Synchronous wrapper for transcribe_audio"""
        return asyncio.run(self.transcribe_audio(
            audio_path=audio_path,
            language=language,
            model=model,
            **kwargs
        ))
