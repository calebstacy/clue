"""
Real-time transcription using faster-whisper with CUDA
"""

import os
import sys

# Add NVIDIA cuDNN DLLs to PATH before importing ctranslate2/faster_whisper
try:
    import nvidia.cudnn
    cudnn_path = os.path.join(os.path.dirname(nvidia.cudnn.__path__[0]), "cudnn", "bin")
    if os.path.exists(cudnn_path):
        os.add_dll_directory(cudnn_path)
        os.environ["PATH"] = cudnn_path + os.pathsep + os.environ.get("PATH", "")
except ImportError:
    pass

try:
    import nvidia.cublas
    cublas_path = os.path.join(os.path.dirname(nvidia.cublas.__path__[0]), "cublas", "bin")
    if os.path.exists(cublas_path):
        os.add_dll_directory(cublas_path)
        os.environ["PATH"] = cublas_path + os.pathsep + os.environ.get("PATH", "")
except ImportError:
    pass

from faster_whisper import WhisperModel
import numpy as np
import threading
import time
from typing import Optional, Callable
from collections import deque


class Transcriber:
    def __init__(
        self, 
        model_size: str = "large-v3",
        device: str = "cuda",
        compute_type: str = "float16"
    ):
        """
        Initialize the Whisper transcriber.
        
        Args:
            model_size: Whisper model size (tiny, base, small, medium, large-v3)
                       With a 3090, large-v3 runs great
            device: "cuda" or "cpu"
            compute_type: "float16" for GPU, "int8" for CPU
        """
        print(f"Loading Whisper {model_size} on {device}...")
        self.model = WhisperModel(
            model_size, 
            device=device, 
            compute_type=compute_type
        )
        print("Whisper model loaded!")
        
        self.transcript_buffer = deque(maxlen=100)  # Last 100 segments
        self._lock = threading.Lock()
        
    def transcribe(
        self, 
        audio: np.ndarray, 
        sample_rate: int = 16000
    ) -> str:
        """
        Transcribe audio array to text.
        
        Args:
            audio: numpy array of audio samples (mono, float32)
            sample_rate: sample rate of the audio
            
        Returns:
            Transcribed text
        """
        if len(audio) == 0:
            return ""
            
        # Resample to 16kHz if needed (Whisper expects 16kHz)
        if sample_rate != 16000:
            # Simple resampling - for production you'd want librosa
            ratio = 16000 / sample_rate
            new_length = int(len(audio) * ratio)
            indices = np.linspace(0, len(audio) - 1, new_length).astype(int)
            audio = audio[indices]
            
        # Normalize
        audio = audio.astype(np.float32)
        if np.abs(audio).max() > 0:
            audio = audio / np.abs(audio).max()
            
        # Transcribe
        segments, info = self.model.transcribe(
            audio,
            beam_size=5,
            language="en",  # Force English for speed, remove for auto-detect
            vad_filter=True,  # Filter out silence
            vad_parameters=dict(
                min_silence_duration_ms=500,
            )
        )
        
        # Collect text
        texts = []
        for segment in segments:
            texts.append(segment.text.strip())
            
        full_text = " ".join(texts)
        
        # Add to buffer with timestamp
        if full_text:
            with self._lock:
                self.transcript_buffer.append({
                    "time": time.time(),
                    "text": full_text
                })
                
        return full_text
        
    def get_recent_transcript(self, seconds: float = 60) -> str:
        """Get transcript from the last N seconds."""
        with self._lock:
            now = time.time()
            cutoff = now - seconds
            
            recent = [
                entry["text"] 
                for entry in self.transcript_buffer 
                if entry["time"] >= cutoff
            ]
            
            return " ".join(recent)
            
    def clear_buffer(self):
        """Clear the transcript buffer."""
        with self._lock:
            self.transcript_buffer.clear()


class ContinuousTranscriber:
    """
    Wrapper that continuously transcribes from an AudioCapture instance.
    """
    
    def __init__(
        self,
        audio_capture,
        transcriber: Transcriber,
        chunk_seconds: float = 5,
        on_transcript: Optional[Callable[[str], None]] = None
    ):
        self.audio_capture = audio_capture
        self.transcriber = transcriber
        self.chunk_seconds = chunk_seconds
        self.on_transcript = on_transcript
        self.is_running = False
        self._thread = None
        
    def _transcribe_loop(self):
        """Continuous transcription loop."""
        last_process_time = time.time()
        
        while self.is_running:
            time.sleep(0.5)  # Check every 500ms
            
            now = time.time()
            if now - last_process_time >= self.chunk_seconds:
                # Get recent audio
                audio = self.audio_capture.get_recent_audio(seconds=self.chunk_seconds)
                
                if len(audio) > 0 and self.audio_capture.sample_rate:
                    # Transcribe
                    text = self.transcriber.transcribe(
                        audio, 
                        sample_rate=self.audio_capture.sample_rate
                    )
                    
                    if text and self.on_transcript:
                        self.on_transcript(text)
                        
                last_process_time = now
                
    def start(self):
        """Start continuous transcription."""
        if self.is_running:
            return
            
        self.is_running = True
        self._thread = threading.Thread(target=self._transcribe_loop, daemon=True)
        self._thread.start()
        print("Continuous transcription started")
        
    def stop(self):
        """Stop transcription."""
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=2.0)


# Test
if __name__ == "__main__":
    # Quick test with a simple audio array
    transcriber = Transcriber(model_size="base")  # Use base for quick test
    
    # Generate some test audio (silence basically)
    test_audio = np.zeros(16000 * 2, dtype=np.float32)  # 2 seconds of silence
    
    result = transcriber.transcribe(test_audio, sample_rate=16000)
    print(f"Transcription result: '{result}'")
