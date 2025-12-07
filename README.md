# LocalCluely 🎧

Local AI meeting assistant - like Cluely but running entirely on your machine.

## Features

- **Real-time transcription** via Whisper (runs on your 3090)
- **AI suggestions** via Ollama (local) or Claude API
- **Always-on-top overlay** with hotkey activation
- **Zero cloud dependency** (with Ollama)

## Requirements

- Windows 10/11
- NVIDIA GPU with CUDA (tested on 3090)
- Python 3.10+
- [Ollama](https://ollama.ai) installed (for local LLM)

## Quick Start

### 1. Install Ollama

Download from https://ollama.ai and install.

Then pull a model:
```bash
ollama pull llama3.1:8b
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

### 3. Run it

```bash
python main.py
```

## Usage

| Hotkey | Action |
|--------|--------|
| `Ctrl+Shift+Space` | Get AI suggestion based on last 60s of conversation |
| `Ctrl+Shift+O` | Toggle overlay visibility |
| `Ctrl+Shift+C` | Clear transcript buffer |
| `Ctrl+Shift+Q` | Quit |
| `Esc` | Hide overlay |

## Options

```bash
python main.py --help

# Use smaller/faster Whisper model
python main.py --whisper base

# Use Claude API instead of Ollama
python main.py --llm claude

# Different Ollama model
python main.py --model mistral

# More context (90 seconds)
python main.py --context 90
```

## Using Claude API (Optional)

If you want to use Claude instead of local Ollama:

1. Set your API key:
   ```bash
   set ANTHROPIC_API_KEY=your-key-here
   ```

2. Install the anthropic package:
   ```bash
   pip install anthropic
   ```

3. Run with Claude:
   ```bash
   python main.py --llm claude
   ```

## Architecture

```
System Audio (WASAPI Loopback)
         ↓
   Audio Capture
         ↓
   Whisper (GPU) → Rolling Transcript Buffer
         ↓
   [Hotkey Pressed]
         ↓
   LLM (Ollama/Claude)
         ↓
   Overlay Display
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

### Overlay not showing
- Check if it's behind other windows
- Press `Ctrl+Shift+O` to toggle
- Try dragging it (it's draggable)

## License

MIT - do whatever you want with it
