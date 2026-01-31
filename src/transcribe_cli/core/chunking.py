"""
Audio chunking logic with checkpoint/resume support
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

from transcribe_cli.utils.fs import get_file_hash, ensure_dir
from transcribe_cli.utils.ffmpeg import get_audio_duration, split_audio_chunk

logger = logging.getLogger(__name__)


@dataclass
class AudioChunk:
    """Represents a chunk of audio to be transcribed"""
    index: int
    start_time: float
    duration: float
    file_path: Path
    transcribed: bool = False
    transcript: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ChunkingManager:
    """Manages audio chunking and checkpoint state
    
    Enforces OpenAI Transcriptions API limit: 25MB per request
    """
    
    # OpenAI Transcriptions API hard limit
    OPENAI_MAX_CHUNK_SIZE = 25 * 1024 * 1024  # 25MB
    
    def __init__(
        self,
        input_path: Path,
        work_dir: Path,
        chunk_duration: int = 300,  # 5 minutes
        max_chunk_size: int = 25 * 1024 * 1024  # 25MB (OpenAI limit)
    ):
        self.input_path = input_path
        self.work_dir = ensure_dir(work_dir)
        self.chunk_duration = chunk_duration
        # Enforce 25MB limit
        self.max_chunk_size = min(max_chunk_size, self.OPENAI_MAX_CHUNK_SIZE)
        
        # Create checkpoint file path
        file_hash = get_file_hash(input_path)
        self.checkpoint_file = self.work_dir / f"checkpoint_{file_hash}.json"
        
        self.chunks: List[AudioChunk] = []
    
    def create_chunks(self, audio_path: Path) -> List[AudioChunk]:
        """
        Split audio into chunks based on duration and size constraints.
        Enforces OpenAI 25MB limit on each chunk.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            List of AudioChunk objects
        """
        logger.info(f"Creating chunks for {audio_path.name}")
        
        # Get total duration
        total_duration = get_audio_duration(audio_path)
        if total_duration <= 0:
            logger.warning("Could not determine audio duration, creating single chunk")
            chunk = AudioChunk(
                index=0,
                start_time=0,
                duration=0,
                file_path=audio_path,
                transcribed=False
            )
            self.chunks = [chunk]
            return self.chunks
        
        logger.info(f"Total duration: {total_duration:.2f} seconds (limit: {self.OPENAI_MAX_CHUNK_SIZE / 1024 / 1024:.0f}MB)")
        
        # Estimate file size and adjust chunk duration if needed
        from transcribe_cli.utils.fs import get_file_size
        total_size = get_file_size(audio_path)
        bytes_per_second = total_size / total_duration if total_duration > 0 else 0
        
        # Calculate max chunk duration based on 25MB limit
        effective_chunk_duration = self.chunk_duration
        if bytes_per_second > 0:
            max_duration_from_size = int(self.max_chunk_size / bytes_per_second)
            effective_chunk_duration = min(self.chunk_duration, max_duration_from_size)
            if effective_chunk_duration < self.chunk_duration:
                logger.info(f"Reducing chunk duration from {self.chunk_duration}s to {effective_chunk_duration}s to meet 25MB limit")
        
        # Calculate number of chunks
        num_chunks = max(1, int(total_duration / effective_chunk_duration) + 1)
        
        chunks: List[AudioChunk] = []
        for i in range(num_chunks):
            start_time = i * effective_chunk_duration
            if start_time >= total_duration:
                break
            
            duration = min(effective_chunk_duration, total_duration - start_time)
            
            chunk_path = self.work_dir / f"chunk_{i:04d}.wav"
            
            # Create chunk file
            try:
                split_audio_chunk(
                    input_path=audio_path,
                    output_path=chunk_path,
                    start_time=start_time,
                    duration=duration
                )
                
                # Verify chunk size
                chunk_size = get_file_size(chunk_path)
                if chunk_size > self.max_chunk_size:
                    logger.warning(f"Chunk {i} size {chunk_size / 1024 / 1024:.1f}MB exceeds limit, may fail")
                
                chunk = AudioChunk(
                    index=i,
                    start_time=start_time,
                    duration=duration,
                    file_path=chunk_path,
                    transcribed=False
                )
                chunks.append(chunk)
                
            except Exception as e:
                logger.error(f"Failed to create chunk {i}: {e}")
                # If chunking fails, use whole file
                if i == 0:
                    chunk = AudioChunk(
                        index=0,
                        start_time=0,
                        duration=total_duration,
                        file_path=audio_path,
                        transcribed=False
                    )
                    chunks = [chunk]
                    break
        
        if chunks is None:
            chunks = []

        self.chunks = chunks
        logger.info(f"Created {len(chunks)} chunks (effective duration: {effective_chunk_duration}s)")
        
        return chunks
    
    def save_checkpoint(self):
        """Save current progress to checkpoint file"""
        checkpoint_data = {
            'input_path': str(self.input_path),
            'chunks': [
                {
                    'index': chunk.index,
                    'start_time': chunk.start_time,
                    'duration': chunk.duration,
                    'file_path': str(chunk.file_path),
                    'transcribed': chunk.transcribed,
                    'transcript': chunk.transcript,
                    'metadata': chunk.metadata
                }
                for chunk in self.chunks
            ]
        }
        
        with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
        
        logger.debug(f"Checkpoint saved: {self.checkpoint_file}")
    
    def load_checkpoint(self) -> bool:
        """
        Load checkpoint if exists
        
        Returns:
            True if checkpoint was loaded, False otherwise
        """
        if not self.checkpoint_file.exists():
            return False
        
        try:
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
            
            # Verify it's for the same input file
            if checkpoint_data.get('input_path') != str(self.input_path):
                logger.warning("Checkpoint is for different input file, ignoring")
                return False
            
            # Restore chunks
            self.chunks = []
            for chunk_data in checkpoint_data.get('chunks', []):
                chunk = AudioChunk(
                    index=chunk_data['index'],
                    start_time=chunk_data['start_time'],
                    duration=chunk_data['duration'],
                    file_path=Path(chunk_data['file_path']),
                    transcribed=chunk_data['transcribed'],
                    transcript=chunk_data.get('transcript'),
                    metadata=chunk_data.get('metadata')
                )
                self.chunks.append(chunk)
            
            completed = sum(1 for c in self.chunks if c.transcribed)
            logger.info(f"Loaded checkpoint: {completed}/{len(self.chunks)} chunks completed")
            
            return True
            
        except Exception as e:
            logger.warning(f"Failed to load checkpoint: {e}")
            return False
    
    def get_pending_chunks(self) -> List[AudioChunk]:
        """Get list of chunks that haven't been transcribed yet"""
        return [chunk for chunk in self.chunks if not chunk.transcribed]
    
    def mark_chunk_completed(self, index: int, transcript: str, metadata: Optional[Dict] = None):
        """Mark a chunk as completed with its transcript"""
        for chunk in self.chunks:
            if chunk.index == index:
                chunk.transcribed = True
                chunk.transcript = transcript
                chunk.metadata = metadata
                break
        
        self.save_checkpoint()
    
    def get_full_transcript(self) -> str:
        """
        Stitch together transcripts from all chunks in order
        
        Returns:
            Combined transcript
        """
        sorted_chunks = sorted(self.chunks, key=lambda c: c.index)
        transcripts = [
            chunk.transcript
            for chunk in sorted_chunks
            if chunk.transcript
        ]

        if transcripts is None:
            transcripts = []
        
        # Join with space, ensuring no double spaces
        full_text = ' '.join(transcripts)
        full_text = ' '.join(full_text.split())  # Normalize whitespace
        
        return full_text
    
    def cleanup(self):
        """Remove checkpoint file"""
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
            logger.debug("Checkpoint file removed")
