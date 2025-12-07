# LocalCluely 🎧

Local AI meeting assistant - runs **100% locally** on your machine. No cloud APIs, no data leaves your computer.

## Features

- **Real-time transcription** via Whisper (runs on your GPU)
- **AI suggestions** via Ollama (completely local)
- **Glassmorphism Electron UI** with Windows acrylic blur
- **Zero cloud dependency** - everything runs on your machine

## Requirements

- Windows 10/11
- NVIDIA GPU with CUDA (tested on 3090)
- Python 3.10+
- Node.js 18+ (for Electron UI)
- [Ollama](https://ollama.ai) installed

## Quick Start

### 1. Install Ollama

Download from https://ollama.ai and install.

Then pull a model:
```bash
ollama pull llama3.2:3b
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

Note: You may need to install CUDA toolkit if faster-whisper can't find it:
```bash
# If using conda
conda install cudatoolkit=11.8

# Or install CUDA from NVIDIA directly
```

### 3. Install Electron dependencies

```bash
cd electron-ui
npm install
cd ..
```

### 4. Run it

Start both the Python backend and Electron UI:

```bash
# Terminal 1 - Python backend
python main_electron.py

# Terminal 2 - Electron UI
cd electron-ui && npx electron .
```

## Usage

| Hotkey | Action |
|--------|--------|
| `Ctrl+Shift+Space` | Get AI suggestion based on last 60s of conversation |
| `Ctrl+Shift+Q` | Quit |

## Options

```bash
python main_electron.py --help

# Use smaller/faster Whisper model
python main_electron.py --whisper base

# Different Ollama model
python main_electron.py --model mistral

# More context (90 seconds)
python main_electron.py --context 90
```

## Architecture

```
System Audio (WASAPI Loopback)
         ↓
   Audio Capture
         ↓
   Whisper (GPU) → Rolling Transcript Buffer
         ↓
   [Auto/Hotkey]
         ↓
   Ollama LLM (Local)
         ↓
   Electron UI (via TCP Socket)
```

## Troubleshooting

### "No loopback device found"
Make sure you're running on Windows. macOS requires additional setup (BlackHole).

### Whisper is slow
- Make sure CUDA is being used: check for "cuda" in startup messages
- Try a smaller model: `--whisper medium` or `--whisper small`

### Ollama errors
- Make sure Ollama is running: `ollama serve`
- Make sure model is pulled: `ollama pull llama3.1:8b`

### Electron UI not connecting
- Make sure Python backend is running first
- Check that port 9999 is not blocked

## License

MIT - do whatever you want with it
