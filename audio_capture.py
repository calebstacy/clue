"""
Audio capture using WASAPI loopback (Windows system audio)
"""

import numpy as np
import pyaudiowpatch as pyaudio
import threading
import queue
from collections import deque
import time


class AudioCapture:
    def __init__(self, buffer_seconds: int = 120):
        """
        Capture system audio via WASAPI loopback.
        
        Args:
            buffer_seconds: How many seconds of audio to keep in rolling buffer
        """
        self.buffer_seconds = buffer_seconds
        self.audio_queue = queue.Queue()
        self.is_running = False
        self.sample_rate = None
        self.channels = None
        self._thread = None
        
    def _get_loopback_device(self, p: pyaudio.PyAudio):
        """Find the default loopback device for system audio."""
        try:
            # Get default WASAPI output device
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
            
            # Find the loopback device for these speakers
            for i in range(p.get_device_count()):
                device = p.get_device_info_by_index(i)
                if (device.get("isLoopbackDevice") and 
                    device.get("hostApi") == wasapi_info["index"]):
                    # Match by name prefix
                    if default_speakers["name"] in device["name"]:
                        return device
                        
            # Fallback: just get any loopback device
            for i in range(p.get_device_count()):
                device = p.get_device_info_by_index(i)
                if device.get("isLoopbackDevice"):
                    return device
                    
        except Exception as e:
            print(f"Error finding loopback device: {e}")
            
        return None
    
    def _capture_loop(self):
        """Main capture loop running in background thread."""
        p = pyaudio.PyAudio()
        
        loopback = self._get_loopback_device(p)
        if not loopback:
            print("ERROR: No loopback device found. Make sure you're on Windows with WASAPI support.")
            return
            
        self.sample_rate = int(loopback["defaultSampleRate"])
        self.channels = loopback["maxInputChannels"]
        
        print(f"Capturing from: {loopback['name']}")
        print(f"Sample rate: {self.sample_rate}, Channels: {self.channels}")
        
        # Open stream
        chunk_size = 1024
        stream = p.open(
            format=pyaudio.paFloat32,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            input_device_index=loopback["index"],
            frames_per_buffer=chunk_size
        )
        
        while self.is_running:
            try:
                data = stream.read(chunk_size, exception_on_overflow=False)
                audio_np = np.frombuffer(data, dtype=np.float32)
                
                # Convert to mono if stereo
                if self.channels == 2:
                    audio_np = audio_np.reshape(-1, 2).mean(axis=1)
                    
                self.audio_queue.put((time.time(), audio_np))
                
            except Exception as e:
                print(f"Audio capture error: {e}")
                continue
                
        stream.stop_stream()
        stream.close()
        p.terminate()
        
    def start(self):
        """Start capturing audio in background."""
        if self.is_running:
            return
            
        self.is_running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        print("Audio capture started")
        
    def stop(self):
        """Stop capturing."""
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        print("Audio capture stopped")
        
    def get_recent_audio(self, seconds: float = 30) -> np.ndarray:
        """
        Get the last N seconds of captured audio.
        
        Returns:
            numpy array of audio samples (mono, float32)
        """
        # Drain queue into list
        chunks = []
        timestamps = []
        
        while not self.audio_queue.empty():
            try:
                ts, chunk = self.audio_queue.get_nowait()
                chunks.append((ts, chunk))
            except queue.Empty:
                break
                
        if not chunks:
            return np.array([], dtype=np.float32)
            
        # Filter to last N seconds
        now = time.time()
        cutoff = now - seconds
        recent_chunks = [chunk for ts, chunk in chunks if ts >= cutoff]
        
        # Put back chunks we want to keep (for rolling buffer)
        buffer_cutoff = now - self.buffer_seconds
        for ts, chunk in chunks:
            if ts >= buffer_cutoff:
                self.audio_queue.put((ts, chunk))
                
        if not recent_chunks:
            return np.array([], dtype=np.float32)
            
        return np.concatenate(recent_chunks)


# Quick test
if __name__ == "__main__":
    capture = AudioCapture()
    capture.start()
    
    print("Recording for 5 seconds...")
    time.sleep(5)
    
    audio = capture.get_recent_audio(seconds=5)
    print(f"Captured {len(audio)} samples ({len(audio)/capture.sample_rate:.2f} seconds)")
    
    capture.stop()
