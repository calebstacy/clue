# LocalCluely - Project Documentation

## Overview
LocalCluely is a 100% local AI meeting assistant that runs entirely on your machine with zero cloud dependencies. It captures system audio, transcribes it in real-time using Whisper, and provides AI-powered suggestions and meeting notes using local LLMs.

## Architecture

### Core Components

```
System Audio (WASAPI Loopback)
         ↓
   Audio Capture (audio_capture.py)
         ↓
   Whisper GPU Transcription (transcriber.py)
         ↓
   Rolling Transcript Buffer
         ↓
   LLM Client (llm_client.py) - Ollama/Claude/OpenAI
         ↓
   Socket Bridge (socket_bridge.py) - TCP Port 9999
         ↓
   Electron UI (electron-ui/)
```

### File Structure

```
cluely-local/
├── main.py                 # PyQt UI version (legacy)
├── main_electron.py        # Main entry point for Electron version
├── audio_capture.py        # WASAPI loopback audio capture
├── transcriber.py          # faster-whisper GPU transcription
├── llm_client.py          # Multi-provider LLM client
├── socket_bridge.py        # TCP socket for Electron communication
├── overlay.py             # PyQt overlay UI (legacy)
├── config.json            # Configuration (gitignored)
├── requirements.txt       # Python dependencies
├── start.bat              # Startup script
├── electron-ui/
│   ├── index.html         # Glassmorphic UI
│   ├── main.js            # Electron main process
│   ├── preload.js         # Electron preload script
│   └── package.json       # Node dependencies
├── logs/                  # Session logs (gitignored)
└── venv/                  # Python virtual environment
```

## Configuration

### config.json Structure
```json
{
  "whisper": {
    "model": "large-v3",      // or: tiny, base, small, medium
    "device": "cuda",         // or: cpu
    "compute_type": "float16", // or: int8 for CPU
    "language": "en"
  },
  "llm": {
    "provider": "ollama",     // or: claude, openai
    "model": "llama3.2:3b",   // Model name for selected provider
    "temperature": 0.7,
    "max_tokens": 150,
    "anthropic_api_key": "",  // For Claude API
    "openai_api_key": "",     // For OpenAI API
    "openai_api_base": ""     // For custom OpenAI endpoints
  },
  "audio": {
    "buffer_seconds": 120,    // Rolling audio buffer
    "chunk_seconds": 5        // Transcription chunk size
  },
  "context": {
    "transcript_seconds": 60  // Context window for LLM
  },
  "hotkeys": {
    "suggest": "ctrl+shift+space",
    "toggle": "ctrl+shift+o",
    "clear": "ctrl+shift+c",
    "quit": "ctrl+shift+q"
  }
}
```

## LLM Provider Support

### Ollama (Local - Default)
- **Setup**: Install Ollama from https://ollama.ai
- **Pull model**: `ollama pull llama3.2:3b`
- **Usage**: Runs 100% locally, no API key needed
- **Models**: llama3.2:3b, mistral, phi3, etc.

### Claude (Anthropic API)
- **Setup**: Get API key from https://console.anthropic.com
- **Config**: Set `provider: "claude"` and add `anthropic_api_key`
- **Models**: claude-3-5-sonnet-20241022, claude-3-opus, etc.
- **Usage**: Cloud-based, requires internet and API key

### OpenAI (OpenAI API or compatible)
- **Setup**: Get API key from OpenAI or compatible service
- **Config**: Set `provider: "openai"`, add `api_key` and optional `api_base`
- **Models**: gpt-4, gpt-3.5-turbo, or custom models
- **Usage**: Cloud-based, requires internet and API key

## UI Design - Glassmorphic Style

### Design System
- **Background**: rgba(15, 15, 20, 0.35) with 60px blur
- **Border radius**: 18px with 8px transparent padding fallback
- **Borders**: rgba(255, 255, 255, 0.15)
- **Shadows**: Layered for depth
- **Backdrop filter**: blur(60px) saturate(200%)

### Color Palette
```css
--bg-glass: rgba(255, 255, 255, 0.02)
--bg-card: rgba(255, 255, 255, 0.03)
--bg-input: rgba(255, 255, 255, 0.06)
--bg-hover: rgba(255, 255, 255, 0.1)
--border: rgba(255, 255, 255, 0.12)
--text-primary: rgba(255, 255, 255, 0.95)
--text-secondary: rgba(255, 255, 255, 0.7)
--text-muted: rgba(255, 255, 255, 0.45)
```

### UI Components
- **Control Bar**: Timer, audio indicator, context button, window controls
- **Main Panel**: Tabbed interface (Insights, Chat, Transcript)
- **Insights View**: Auto-updating meeting notes with card-based layout
- **Chat View**: Q&A interface with quick action buttons
- **Transcript View**: Live transcript feed
- **Nav Bar**: Bottom navigation tabs

## Development Setup

### Prerequisites
- Windows 10/11 (for WASAPI audio capture)
- NVIDIA GPU with CUDA (for faster-whisper)
- Python 3.10+
- Node.js 18+
- Ollama installed and running

### Installation

1. **Clone repository**
```bash
git clone https://github.com/calebstacy/clue.git
cd clue
```

2. **Python setup**
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

3. **Electron setup**
```bash
cd electron-ui
npm install
cd ..
```

4. **Ollama setup**
```bash
ollama pull llama3.2:3b
```

5. **Create config.json** (copy from template or let it auto-generate)

### Running

**Option 1: Use start.bat (recommended)**
```bash
start.bat
```

**Option 2: Manual**
```bash
# Terminal 1 - Python backend
venv\Scripts\python.exe main_electron.py

# Terminal 2 - Electron UI
cd electron-ui
npx electron .
```

## Features

### Real-time Transcription
- Captures system audio via WASAPI loopback
- Processes in 5-second chunks
- GPU-accelerated with faster-whisper
- Rolling 120-second buffer
- VAD (Voice Activity Detection) to filter silence

### AI-Powered Features
- **Live Insights**: Auto-generated meeting notes (updates every 30s)
- **Suggestions**: "What should I say next?" triggered by hotkey
- **Q&A**: Ask questions about the conversation
- **Context Support**: Add custom context to guide AI responses

### Hotkeys
- `Ctrl+Shift+Space`: Get AI suggestion
- `Ctrl+Shift+O`: Toggle window visibility
- `Ctrl+Shift+C`: Clear session
- `Ctrl+Shift+Q`: Quit application
- `Esc`: Hide window

### Session Logging
All sessions are logged to `logs/session_YYYY-MM-DD_HH-MM-SS.jsonl` with:
- Transcript chunks with timestamps
- AI suggestions with the transcript context used
- Full session timeline

## Troubleshooting

### Ollama Model Not Found
- **Issue**: "model 'llama3.x:xb' not found"
- **Solution**:
  1. Kill all Python processes: `taskkill /F /IM python.exe`
  2. Verify model: `ollama list`
  3. Pull if needed: `ollama pull llama3.2:3b`
  4. Restart with `start.bat`

### Whisper Not Using GPU
- **Issue**: Slow transcription
- **Solution**:
  1. Check CUDA installation: `nvidia-smi`
  2. Install CUDA toolkit if missing
  3. Check startup logs for "cuda" confirmation
  4. Try smaller model: `--whisper medium`

### No Audio Captured
- **Issue**: "No loopback device found"
- **Solution**:
  1. Windows only (macOS requires BlackHole)
  2. Play audio to initialize devices
  3. Check Windows sound settings
  4. Restart application

### Electron Not Connecting
- **Issue**: "Waiting for Electron UI to connect..."
- **Solution**:
  1. Python backend must start first
  2. Wait 10 seconds for initialization
  3. Check port 9999 not blocked
  4. Use `start.bat` which handles timing

### Old Backend Still Running
- **Issue**: Changes not taking effect
- **Solution**:
  1. Close all windows
  2. Run: `taskkill /F /IM python.exe`
  3. Restart with `start.bat`

## Performance Tuning

### Whisper Model Selection
- **tiny**: Fastest, lowest quality
- **base**: Fast, acceptable quality
- **small**: Balanced
- **medium**: Good quality, slower
- **large-v3**: Best quality, slowest (recommended for 3090)

### LLM Configuration
- **Context window**: 60s default (adjustable via `--context`)
- **Temperature**: 0.7 (higher = more creative, lower = more focused)
- **Max tokens**: 150 for suggestions, 500 for notes

### Audio Buffer
- **buffer_seconds**: 120s rolling buffer for audio
- **chunk_seconds**: 5s transcription chunks (lower = more responsive)

## API Integration

### Adding New LLM Providers
Edit `llm_client.py`:

1. Add import for new provider
2. Add initialization in `__init__`
3. Add query method in `_query_llm`
4. Update provider choices in `main_electron.py`

Example structure:
```python
elif self.provider == "new_provider":
    response = new_provider_client.chat(...)
    return response.text
```

## Security Notes

- `config.json` is in `.gitignore` - never commit API keys
- All processing happens locally (Ollama mode)
- Logs contain transcript data - handle appropriately
- Session logs stored in `logs/` directory

## Windows-Specific Features

### WASAPI Loopback
- Captures system audio directly
- No virtual cables needed
- Automatic device detection
- Fallback to any loopback device

### Electron Window Transparency
- Uses Windows acrylic material
- Backdrop blur via CSS
- Transparent padding for rounded corners (fallback)
- Always-on-top floating window

## Future Improvements

- [ ] macOS support with BlackHole
- [ ] Linux support with PulseAudio
- [ ] Speaker diarization (who said what)
- [ ] Multi-language support
- [ ] Custom prompt templates
- [ ] Export meeting notes
- [ ] Integration with calendar/CRM
- [ ] Mobile companion app

## Tech Stack

- **Backend**: Python 3.10+
- **Audio**: PyAudioWPatch (WASAPI)
- **Transcription**: faster-whisper (OpenAI Whisper + CTranslate2)
- **LLM**: Ollama / Anthropic Claude / OpenAI
- **UI**: Electron 28+, HTML/CSS/JavaScript
- **Communication**: TCP sockets (port 9999)
- **Packaging**: Virtual environment (venv)

## Credits

Built with Claude Code by Caleb Stacy
Inspired by Cluely's meeting intelligence interface
