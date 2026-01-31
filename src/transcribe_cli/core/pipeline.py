"""
Main transcription pipeline orchestrator
"""
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from transcribe_cli.config import TranscribeConfig, load_glossary, load_settings
from transcribe_cli.utils.fs import (
    is_video_file,
    is_audio_file,
    create_temp_dir,
    cleanup_temp_files,
    ensure_dir
)
from transcribe_cli.utils.ffmpeg import (
    extract_audio_from_video,
    convert_audio_format,
    FFmpegError,
    get_audio_duration
)
from transcribe_cli.adapters.openai_client import OpenAIClient, OpenAITranscriptionError
from transcribe_cli.core.chunking import ChunkingManager, AudioChunk
from transcribe_cli.core.postprocess import clean_transcript, extract_segments_from_response

logger = logging.getLogger(__name__)


class TranscriptionPipeline:
    """Main pipeline for transcribing audio/video files"""
    
    def __init__(self, config: TranscribeConfig):
        self.config = config
        
        # Load settings
        self.settings = load_settings()
        
        # Initialize OpenAI client
        self.client = OpenAIClient(
            api_key=self.settings.openai_api_key,
            api_base=self.settings.openai_api_base,
            timeout=self.settings.request_timeout,
            max_retries=self.settings.max_retries,
            retry_delay=self.settings.retry_delay
        )
        
        # Load glossary if provided
        self.glossary = {}
        if config.glossary_path:
            self.glossary = load_glossary(config.glossary_path)
            logger.info(f"Loaded {len(self.glossary)} glossary terms")
        
        # Temp directory for processing
        self.temp_dir: Optional[Path] = None
        self.work_audio_path: Optional[Path] = None
    
    async def run(self) -> Dict[str, Any]:
        """
        Execute full transcription pipeline
        
        Returns:
            Dictionary with transcript and metadata
        """
        try:
            # Step A: Prepare audio
            audio_path = await self._prepare_audio()
            
            # Step B: Setup chunking
            chunking_mgr = self._setup_chunking(audio_path)

            if chunking_mgr.chunks is None:
                raise ValueError("chunking failed; check ffmpeg extraction")
            
            # Step C: Transcribe chunks
            await self._transcribe_chunks(chunking_mgr)
            
            # Step D: Get full transcript
            raw_transcript = chunking_mgr.get_full_transcript()
            
            # Step E: Post-process
            final_transcript = clean_transcript(
                text=raw_transcript,
                glossary=self.glossary,
                language=self.config.language,
                add_punctuation=False  # Keep it minimal per requirements
            )
            
            # Collect metadata
            segments = self._collect_segments(chunking_mgr)
            if segments is None:
                segments = []

            duration_seconds = None
            try:
                duration_seconds = get_audio_duration(audio_path)
            except Exception:
                duration_seconds = None

            result = {
                'text': final_transcript,
                'chunks_count': len(chunking_mgr.chunks),
                'duration_seconds': duration_seconds,
                'segments': segments,
                'warnings': [],
                # Backwards-compatible fields
                'transcript': final_transcript,
                'language': self.config.language,
                'model': self.config.model or self.settings.openai_model,
                'chunks': len(chunking_mgr.chunks),
                'input_file': self.config.input_path.name
            }
            
            # Cleanup checkpoint if successful
            if not self.config.resume:
                chunking_mgr.cleanup()
            
            return result
            
        finally:
            # Cleanup temp files
            if self.temp_dir and self.temp_dir.exists():
                cleanup_temp_files(self.temp_dir, self.config.verbose)
    
    async def _prepare_audio(self) -> Path:
        """
        Prepare audio for transcription
        - Extract from video if needed
        - Convert to standard format (mono, 16kHz WAV)
        
        Returns:
            Path to prepared audio file
        """
        input_path = self.config.input_path
        
        # Create temp directory
        self.temp_dir = create_temp_dir(self.config.output_dir)
        logger.info(f"Working directory: {self.temp_dir}")
        
        if is_video_file(input_path):
            logger.info(f"Extracting audio from video: {input_path.name}")
            try:
                audio_path = self.temp_dir / "extracted_audio.wav"
                extract_audio_from_video(
                    video_path=input_path,
                    output_path=audio_path,
                    sample_rate=16000,
                    channels=1,
                    verbose=self.config.verbose
                )
                logger.info(f"Audio extracted: {audio_path.name}")
                return audio_path
                
            except FFmpegError as e:
                logger.error(f"Failed to extract audio: {e}")
                raise
        
        elif is_audio_file(input_path):
            # Convert to standard format
            logger.info(f"Converting audio to standard format: {input_path.name}")
            try:
                audio_path = self.temp_dir / "converted_audio.wav"
                convert_audio_format(
                    input_path=input_path,
                    output_path=audio_path,
                    sample_rate=16000,
                    channels=1,
                    verbose=self.config.verbose
                )
                logger.info(f"Audio converted: {audio_path.name}")
                return audio_path
                
            except FFmpegError as e:
                logger.warning(f"Conversion failed, using original: {e}")
                return input_path
        
        else:
            raise ValueError(f"Unsupported file type: {input_path.suffix}")
    
    def _setup_chunking(self, audio_path: Path) -> ChunkingManager:
        """
        Setup chunking manager and create/load chunks
        
        Args:
            audio_path: Path to prepared audio
            
        Returns:
            Initialized ChunkingManager
        """
        # Create checkpoint directory
        checkpoint_dir = ensure_dir(self.config.output_dir / ".checkpoints")
        
        chunking_mgr = ChunkingManager(
            input_path=self.config.input_path,
            work_dir=self.temp_dir,
            chunk_duration=self.config.chunk_duration_seconds,
            max_chunk_size=self.config.max_bytes_per_chunk
        )
        
        # Try to load checkpoint if resume is enabled
        if self.config.resume:
            loaded = chunking_mgr.load_checkpoint()
            if loaded:
                logger.info("Resuming from checkpoint")
                return chunking_mgr
        
        # Create new chunks
        chunking_mgr.create_chunks(audio_path)
        chunking_mgr.save_checkpoint()
        
        return chunking_mgr
    
    async def _transcribe_chunks(self, chunking_mgr: ChunkingManager):
        """
        Transcribe all pending chunks
        
        Args:
            chunking_mgr: ChunkingManager with chunks to process
        """
        pending_chunks = chunking_mgr.get_pending_chunks()
        total_chunks = len(chunking_mgr.chunks)
        completed = total_chunks - len(pending_chunks)
        
        logger.info(f"Transcribing {len(pending_chunks)} chunks ({completed}/{total_chunks} already done)")
        
        model = self.config.model or self.settings.openai_model

        # Choose response format based on output requirements
        if self.config.output_format in ["srt", "vtt", "json"]:
            response_format = "verbose_json"
        else:
            response_format = "text"

        timestamp_granularities = None
        if response_format == "verbose_json" and model == "whisper-1":
            timestamp_granularities = ["segment"]
        
        for i, chunk in enumerate(pending_chunks, 1):
            logger.info(f"Processing chunk {chunk.index + 1}/{total_chunks} (pending: {i}/{len(pending_chunks)})")
            
            try:
                # Choose transcription method
                if self.config.diarize:
                    result = await self.client.transcribe_with_diarization(
                        audio_path=chunk.file_path,
                        language=self.config.language,
                        model=model,
                        timestamp_granularities=timestamp_granularities
                    )
                else:
                    result = await self.client.transcribe_audio(
                        audio_path=chunk.file_path,
                        language=self.config.language,
                        model=model,
                        response_format=response_format,
                        timestamp_granularities=timestamp_granularities
                    )
                
                # Extract transcript
                transcript = result.get('text', '')
                
                # Mark as completed
                chunking_mgr.mark_chunk_completed(
                    index=chunk.index,
                    transcript=transcript,
                    metadata=result
                )
                
                logger.info(f"✓ Chunk {chunk.index + 1} completed")
                
            except OpenAITranscriptionError as e:
                logger.error(f"Failed to transcribe chunk {chunk.index + 1}: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error on chunk {chunk.index + 1}: {e}")
                raise
    
    def _collect_segments(self, chunking_mgr: ChunkingManager) -> list:
        """
        Collect all segments with timestamps from chunks
        
        Args:
            chunking_mgr: ChunkingManager with transcribed chunks
            
        Returns:
            List of segments with adjusted timestamps
        """
        all_segments = []
        
        for chunk in sorted(chunking_mgr.chunks, key=lambda c: c.index):
            if chunk.metadata and 'segments' in chunk.metadata:
                segment_list = chunk.metadata.get('segments') or []
                # Adjust timestamps relative to chunk start
                for seg in segment_list:
                    segment = {
                        'start': chunk.start_time + seg.get('start', 0),
                        'end': chunk.start_time + seg.get('end', 0),
                        'text': seg.get('text', '').strip()
                    }
                    all_segments.append(segment)
        
        return all_segments


async def transcribe_file(config: TranscribeConfig) -> Dict[str, Any]:
    """
    Convenience function to transcribe a single file
    
    Args:
        config: Transcription configuration
        
    Returns:
        Transcription result
    """
    pipeline = TranscriptionPipeline(config)
    return await pipeline.run()
