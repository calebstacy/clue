"""
LocalCluely - Local AI meeting assistant

Hotkeys:
    Ctrl+Shift+Space: Get suggestion based on recent conversation
    Ctrl+Shift+T: Toggle transcript display
    Ctrl+Shift+Q: Quit application
    Esc: Hide overlay
"""

import sys
import threading
import time
from typing import Optional

from pynput import keyboard as pynput_keyboard

from audio_capture import AudioCapture
from transcriber import Transcriber, ContinuousTranscriber
from llm_client import LLMClient, get_logger
from overlay import OverlayController


class LocalCluely:
    def __init__(
        self,
        whisper_model: str = "large-v3",
        llm_provider: str = "ollama",
        llm_model: str = "llama3.1:8b",
        transcript_seconds: float = 60,
        api_base_url: str = None,
        api_key: str = None,
        anthropic_api_key: str = None,
    ):
        """
        Initialize LocalCluely.

        Args:
            whisper_model: Whisper model size (large-v3 recommended for 3090)
            llm_provider: "ollama" for local, "claude" for API, "openai" for OpenAI-compatible
            llm_model: Model to use for suggestions
            transcript_seconds: How many seconds of transcript to use for context
            api_base_url: Base URL for OpenAI-compatible API
            api_key: API key for OpenAI-compatible API
            anthropic_api_key: API key for Claude
        """
        self.transcript_seconds = transcript_seconds
        self.is_running = False

        print("=" * 50)
        print("  LocalCluely - Your Local Meeting Assistant")
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

        print("[3/4] Initializing LLM client...")
        self.llm_client = LLMClient(
            provider=llm_provider,
            model=llm_model,
            api_base_url=api_base_url,
            api_key=api_key,
            anthropic_api_key=anthropic_api_key,
        )

        print("[4/4] Setting up overlay...")
        self.overlay = OverlayController()
        self._connect_ui_signals()

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

    def _connect_ui_signals(self):
        """Connect UI button signals to actions."""
        # These will be connected after init_qt is called
        pass

    def _setup_ui_connections(self):
        """Set up connections after Qt is initialized."""
        if self.overlay.window:
            self.overlay.window.signals.request_suggestion.connect(self._get_suggestion)
            self.overlay.window.signals.request_clear.connect(self._clear_session)
            self.overlay.window.signals.request_quit.connect(self._quit)
            self.overlay.window.signals.context_changed.connect(self._on_context_changed)
            self.overlay.window.signals.ask_question.connect(self._handle_question)

    def _on_context_changed(self, context: str):
        """Handle context input changes."""
        self._user_context = context

    def _get_loaded_files(self):
        """Get list of loaded files from the overlay."""
        if self.overlay.window:
            return self.overlay.window.get_loaded_files()
        return []

    def _handle_question(self, question: str):
        """Handle a question about the conversation."""
        print(f"Question: {question}")

        # Capture files at call time (thread-safe)
        files = self._get_loaded_files()

        def answer_question():
            try:
                transcript = self.transcriber.get_recent_transcript(self.transcript_seconds)
                answer = self.llm_client.ask_question(
                    transcript,
                    question,
                    context=self._user_context if self._user_context else None,
                    files=files if files else None
                )
                self.overlay.set_answer(answer)
            except Exception as e:
                self.overlay.set_answer(f"Error: {e}")

        thread = threading.Thread(target=answer_question, daemon=True)
        thread.start()

    def _clear_session(self):
        """Clear the entire session - transcript, notes, etc."""
        print("Clearing session...")
        self.transcriber.clear_buffer()
        if self.overlay.window:
            self.overlay.window.clear_session()

    def _on_transcript(self, text: str):
        """Called when new transcript chunk is available."""
        if text.strip():
            self._last_transcript = text
            # Log the transcript
            get_logger().log_transcript(text)
            # Append to transcript view (the new text chunk)
            self.overlay.set_transcript(text)

    def _notes_loop(self):
        """Background loop that continuously updates meeting notes."""
        while self._notes_running:
            try:
                transcript = self.transcriber.get_recent_transcript(self.transcript_seconds)
                if transcript.strip():
                    files = self._get_loaded_files()
                    notes = self.llm_client.get_interpretation(
                        transcript,
                        context=self._user_context if self._user_context else None,
                        files=files if files else None
                    )
                    self.overlay.set_notes(notes)
            except Exception as e:
                print(f"Notes error: {e}")

            # Update every 30 seconds for meeting notes style
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
        # Get recent transcript
        transcript = self.transcriber.get_recent_transcript(self.transcript_seconds)

        if not transcript.strip():
            self.overlay.set_suggestion("No conversation detected yet. Start talking!")
            return

        # Get context from UI
        context = self._user_context if self._user_context else None
        files = self._get_loaded_files()

        self.overlay.set_loading()
        self.overlay.show()

        # Generate suggestion in background
        def generate():
            try:
                suggestion = self.llm_client.get_suggestion(
                    transcript,
                    context=context,
                    files=files if files else None
                )
                self.overlay.set_suggestion(f'"{suggestion}"')
            except Exception as e:
                self.overlay.set_suggestion(f"Error: {e}")

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
        # Normalize keys to check
        ctrl = (pynput_keyboard.Key.ctrl_l in self._pressed_keys or
                pynput_keyboard.Key.ctrl_r in self._pressed_keys)
        shift = (pynput_keyboard.Key.shift_l in self._pressed_keys or
                 pynput_keyboard.Key.shift_r in self._pressed_keys)

        # Check for character keys
        char_keys = {k for k in self._pressed_keys
                     if hasattr(k, 'char') and k.char is not None}
        vk_keys = {k for k in self._pressed_keys
                   if hasattr(k, 'vk')}

        if ctrl and shift:
            # Ctrl+Shift+Space - Get suggestion
            if pynput_keyboard.Key.space in self._pressed_keys:
                self._pressed_keys.clear()  # Prevent repeat
                print("Hotkey: Getting suggestion...")
                self._get_suggestion()

            # Ctrl+Shift+O - Toggle overlay
            elif any(getattr(k, 'char', None) == 'o' for k in char_keys):
                self._pressed_keys.clear()
                print("Hotkey: Toggling overlay...")
                if self.overlay.window.isVisible():
                    self.overlay.hide()
                else:
                    self.overlay.show()

            # Ctrl+Shift+C - Clear session
            elif any(getattr(k, 'char', None) == 'c' for k in char_keys):
                self._pressed_keys.clear()
                print("Hotkey: Clearing session...")
                self._clear_session()

            # Ctrl+Shift+Q - Quit
            elif any(getattr(k, 'char', None) == 'q' for k in char_keys):
                self._pressed_keys.clear()
                print("Hotkey: Quitting...")
                self._quit()

        # Escape - Hide overlay
        if pynput_keyboard.Key.esc in self._pressed_keys:
            self._pressed_keys.clear()
            self.overlay.hide()

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
        print("  Ctrl+Shift+O      - Toggle window")
        print("  Ctrl+Shift+C      - Clear session")
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
        if self.overlay.app:
            self.overlay.app.quit()
        sys.exit(0)

    def run(self):
        """Main run loop."""
        # Initialize Qt (must be in main thread)
        app, window = self.overlay.init_qt()

        # Connect UI signals after Qt is initialized
        self._setup_ui_connections()

        # Start background services - auto-listen on startup
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
        print("=" * 50)
        print()

        # Show window and start background notes generation
        window.show()
        self._start_notes()

        # Run Qt event loop
        try:
            sys.exit(app.exec())
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


def save_config(config):
    """Save configuration to config.json."""
    import json
    from pathlib import Path

    config_path = Path(__file__).parent / "config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)


def main():
    """Entry point with configuration."""
    import argparse

    # Load saved config
    config = load_config()
    llm_config = config.get("llm", {})
    whisper_config = config.get("whisper", {})
    context_config = config.get("context", {})

    parser = argparse.ArgumentParser(description="LocalCluely - Local AI Meeting Assistant")
    parser.add_argument(
        "--whisper",
        default=whisper_config.get("model", "large-v3"),
        choices=["tiny", "base", "small", "medium", "large-v3"],
        help="Whisper model size"
    )
    parser.add_argument(
        "--llm",
        default=llm_config.get("provider", "claude"),
        choices=["ollama", "claude", "openai"],
        help="LLM provider"
    )
    parser.add_argument(
        "--model",
        default=llm_config.get("model", "llama3.1:8b"),
        help="LLM model name"
    )
    parser.add_argument(
        "--api-url",
        default=llm_config.get("openai_api_base"),
        help="Base URL for OpenAI-compatible API"
    )
    parser.add_argument(
        "--api-key",
        default=llm_config.get("openai_api_key"),
        help="API key for OpenAI-compatible API"
    )
    parser.add_argument(
        "--anthropic-key",
        default=llm_config.get("anthropic_api_key"),
        help="API key for Claude"
    )
    parser.add_argument(
        "--context",
        type=int,
        default=context_config.get("transcript_seconds", 60),
        help="Seconds of transcript to use for context"
    )
    parser.add_argument(
        "--save-key",
        action="store_true",
        help="Save the API key to config for future use"
    )

    args = parser.parse_args()

    # Save API key if requested
    if args.save_key and args.anthropic_key:
        config.setdefault("llm", {})["anthropic_api_key"] = args.anthropic_key
        config["llm"]["provider"] = "claude"
        save_config(config)
        print("API key saved to config.json")

    cluely = LocalCluely(
        whisper_model=args.whisper,
        llm_provider=args.llm,
        llm_model=args.model,
        transcript_seconds=args.context,
        api_base_url=args.api_url,
        api_key=args.api_key,
        anthropic_api_key=args.anthropic_key,
    )

    cluely.run()


if __name__ == "__main__":
    main()
