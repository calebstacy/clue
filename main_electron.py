"""
LocalCluely with Electron UI - Local AI meeting assistant (Local-only version)

Hotkeys:
    Ctrl+Shift+Space: Get suggestion based on recent conversation
    Ctrl+Shift+Q: Quit application
"""

import sys
import threading
import time
from typing import Optional

from pynput import keyboard as pynput_keyboard

from audio_capture import AudioCapture
from transcriber import Transcriber, ContinuousTranscriber
from llm_client import LLMClient, get_logger
from socket_bridge import SocketBridge


class LocalCluelyElectron:
    def __init__(
        self,
        whisper_model: str = "large-v3",
        llm_model: str = "llama3.1:8b",
        transcript_seconds: float = 60,
    ):
        self.transcript_seconds = transcript_seconds
        self.is_running = False

        print("=" * 50)
        print("  LocalCluely (Electron UI) - Meeting Assistant")
        print("  100% Local - No Cloud APIs")
        print("=" * 50)
        print()

        # Initialize components
        print("[1/4] Initializing audio capture...")
        self.audio_capture = AudioCapture(buffer_seconds=120)

        print("[2/4] Loading Whisper model (this may take a moment)...")
        self.transcriber = Transcriber(
            model_size=whisper_model,
            device="cuda",
            compute_type="float16"
        )

        print("[3/4] Initializing Ollama LLM client...")
        self.llm_client = LLMClient(model=llm_model)

        print("[4/4] Setting up socket bridge for Electron UI...")
        self.bridge = SocketBridge(port=9999)
        self._setup_bridge_handlers()

        # Continuous transcriber
        self.continuous_transcriber = ContinuousTranscriber(
            audio_capture=self.audio_capture,
            transcriber=self.transcriber,
            chunk_seconds=5,
            on_transcript=self._on_transcript
        )

        self._last_transcript = ""

        # Track pressed keys for hotkey detection
        self._pressed_keys = set()
        self._hotkey_listener = None

        # Continuous meeting notes
        self._notes_thread = None
        self._notes_running = False

        # User-provided context
        self._user_context = ""

    def _setup_bridge_handlers(self):
        """Set up handlers for messages from Electron UI."""
        self.bridge.on('suggest', self._handle_suggest)
        self.bridge.on('question', self._handle_question)
        self.bridge.on('clear', self._handle_clear)

    def _handle_suggest(self, data):
        """Handle suggestion request from Electron."""
        print("Electron requested suggestion...")
        self._get_suggestion()

    def _handle_question(self, data):
        """Handle question from Electron."""
        question = data.get('text', '')
        if question:
            print(f"Electron asked: {question}")
            self._answer_question(question)

    def _handle_clear(self, data):
        """Handle clear session request from Electron."""
        print("Clearing session...")
        self.transcriber.clear_buffer()
        self.bridge.send_transcript("")
        self.bridge.send_notes("")

    def _answer_question(self, question: str):
        """Answer a question about the conversation."""
        def answer():
            try:
                transcript = self.transcriber.get_recent_transcript(self.transcript_seconds)
                answer = self.llm_client.ask_question(
                    transcript,
                    question,
                    context=self._user_context if self._user_context else None
                )
                self.bridge.send_answer(answer)
            except Exception as e:
                self.bridge.send_answer(f"Error: {e}")

        thread = threading.Thread(target=answer, daemon=True)
        thread.start()

    def _on_transcript(self, text: str):
        """Called when new transcript chunk is available."""
        if text.strip():
            self._last_transcript = text
            get_logger().log_transcript(text)
            # Send to Electron UI
            self.bridge.send_transcript(text)

    def _notes_loop(self):
        """Background loop that continuously updates meeting notes."""
        while self._notes_running:
            try:
                transcript = self.transcriber.get_recent_transcript(self.transcript_seconds)
                if transcript.strip():
                    notes = self.llm_client.get_interpretation(
                        transcript,
                        context=self._user_context if self._user_context else None
                    )
                    self.bridge.send_notes(notes)
            except Exception as e:
                print(f"Notes error: {e}")

            time.sleep(30)

    def _start_notes(self):
        """Start the continuous notes generation."""
        if self._notes_running:
            return
        self._notes_running = True
        self._notes_thread = threading.Thread(
            target=self._notes_loop, daemon=True
        )
        self._notes_thread.start()
        print("Meeting notes generation started")

    def _get_suggestion(self):
        """Generate suggestion from recent transcript."""
        transcript = self.transcriber.get_recent_transcript(self.transcript_seconds)

        if not transcript.strip():
            self.bridge.send_suggestion("No conversation detected yet. Start talking!")
            return

        context = self._user_context if self._user_context else None

        self.bridge.send_status("loading")

        def generate():
            try:
                suggestion = self.llm_client.get_suggestion(
                    transcript,
                    context=context
                )
                self.bridge.send_suggestion(f'"{suggestion}"')
                self.bridge.send_status("ready")
            except Exception as e:
                self.bridge.send_suggestion(f"Error: {e}")
                self.bridge.send_status("error")

        thread = threading.Thread(target=generate, daemon=True)
        thread.start()

    def _on_key_press(self, key):
        """Handle key press events."""
        self._pressed_keys.add(key)
        self._check_hotkeys()

    def _on_key_release(self, key):
        """Handle key release events."""
        self._pressed_keys.discard(key)

    def _check_hotkeys(self):
        """Check if any hotkey combination is pressed."""
        ctrl = (pynput_keyboard.Key.ctrl_l in self._pressed_keys or
                pynput_keyboard.Key.ctrl_r in self._pressed_keys)
        shift = (pynput_keyboard.Key.shift_l in self._pressed_keys or
                 pynput_keyboard.Key.shift_r in self._pressed_keys)

        char_keys = {k for k in self._pressed_keys
                     if hasattr(k, 'char') and k.char is not None}

        if ctrl and shift:
            # Ctrl+Shift+Space - Get suggestion
            if pynput_keyboard.Key.space in self._pressed_keys:
                self._pressed_keys.clear()
                print("Hotkey: Getting suggestion...")
                self._get_suggestion()

            # Ctrl+Shift+Q - Quit
            elif any(getattr(k, 'char', None) == 'q' for k in char_keys):
                self._pressed_keys.clear()
                print("Hotkey: Quitting...")
                self._quit()

    def _setup_hotkeys(self):
        """Register global hotkeys using pynput."""
        self._hotkey_listener = pynput_keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release
        )
        self._hotkey_listener.start()

        print()
        print("Hotkeys:")
        print("  Ctrl+Shift+Space  - Get suggestion")
        print("  Ctrl+Shift+Q      - Quit")
        print()

    def _quit(self):
        """Clean shutdown."""
        print("\nShutting down...")
        self.is_running = False
        self._notes_running = False
        if self._hotkey_listener:
            self._hotkey_listener.stop()
        self.audio_capture.stop()
        self.continuous_transcriber.stop()
        self.bridge.stop()
        sys.exit(0)

    def run(self):
        """Main run loop."""
        # Start socket bridge for Electron
        self.bridge.start()

        # Start background services
        self.audio_capture.start()
        self.continuous_transcriber.start()

        # Setup hotkeys
        self._setup_hotkeys()

        self.is_running = True

        # Initialize logger
        logger = get_logger()

        print("=" * 50)
        print("  LocalCluely Ready!")
        print(f"  Logs: {logger.log_file}")
        print("  Waiting for Electron UI to connect on port 9999...")
        print("=" * 50)
        print()

        # Start background notes generation
        self._start_notes()

        # Keep running until quit
        try:
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            self._quit()


def load_config():
    """Load configuration from config.json."""
    import json
    from pathlib import Path

    config_path = Path(__file__).parent / "config.json"
    if config_path.exists():
        with open(config_path, "r") as f:
            return json.load(f)
    return {}


def main():
    """Entry point with configuration."""
    import argparse

    config = load_config()
    llm_config = config.get("llm", {})
    whisper_config = config.get("whisper", {})
    context_config = config.get("context", {})

    parser = argparse.ArgumentParser(description="LocalCluely with Electron UI (Local-only)")
    parser.add_argument(
        "--whisper",
        default=whisper_config.get("model", "large-v3"),
        choices=["tiny", "base", "small", "medium", "large-v3"],
        help="Whisper model size"
    )
    parser.add_argument(
        "--model",
        default=llm_config.get("model", "llama3.1:8b"),
        help="Ollama model name (e.g., llama3.1:8b, mistral, phi3)"
    )
    parser.add_argument(
        "--context",
        type=int,
        default=context_config.get("transcript_seconds", 60),
        help="Seconds of transcript to use for context"
    )

    args = parser.parse_args()

    cluely = LocalCluelyElectron(
        whisper_model=args.whisper,
        llm_model=args.model,
        transcript_seconds=args.context,
    )

    cluely.run()


if __name__ == "__main__":
    main()
