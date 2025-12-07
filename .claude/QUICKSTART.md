# LocalCluely - Quick Start Guide

## Fastest Path to Running

1. **Install Ollama**: https://ollama.ai
2. **Pull model**: `ollama pull llama3.2:3b`
3. **Run**: Double-click `start.bat`

That's it! The UI will appear in 10 seconds.

## First Time Setup (5 minutes)

### 1. Prerequisites
- Windows 10/11
- NVIDIA GPU (for fast transcription)
- Python 3.10+
- Node.js 18+

### 2. Install Dependencies

```bash
# Python
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Electron
cd electron-ui
npm install
cd ..
```

### 3. Install Ollama & Model
```bash
# Download from https://ollama.ai
# Then pull model:
ollama pull llama3.2:3b
```

### 4. Run
```bash
start.bat
```

## Using the App

### Interface
- **Top Bar**: Timer, audio indicator, context, window controls
- **Insights Tab**: Auto-generated meeting notes (updates every 30s)
- **Chat Tab**: Ask questions about the conversation
- **Transcript Tab**: Live transcript feed

### Hotkeys
- `Ctrl+Shift+Space` - Get AI suggestion ("What should I say?")
- `Ctrl+Shift+O` - Show/hide window
- `Ctrl+Shift+C` - Clear session
- `Ctrl+Shift+Q` - Quit
- `Esc` - Hide window

### Adding Context
1. Click the context button (top bar)
2. Enter information to guide the AI
3. Example: "I'm selling enterprise software to a Fortune 500 company"

## Using Claude API Instead of Ollama

1. **Get API Key**: https://console.anthropic.com
2. **Edit config.json**:
```json
{
  "llm": {
    "provider": "claude",
    "model": "claude-3-5-sonnet-20241022",
    "anthropic_api_key": "sk-ant-..."
  }
}
```
3. **Restart app**

## Common Issues

### "Model not found"
```bash
# Kill old processes
taskkill /F /IM python.exe

# Verify model
ollama list

# Restart
start.bat
```

### "No audio captured"
- Make sure audio is playing
- Windows only (not macOS/Linux yet)
- Check Windows sound settings

### Slow transcription
- Need NVIDIA GPU with CUDA
- Or use smaller model: Edit config.json `"model": "base"`

### Electron won't connect
- Python backend must start first
- `start.bat` handles this automatically
- Manual: wait 10 seconds between starting backend and UI

## Configuration

Edit `config.json` to customize:

```json
{
  "whisper": {
    "model": "large-v3"  // Change to: tiny, base, small, medium
  },
  "llm": {
    "provider": "ollama", // or: claude, openai
    "model": "llama3.2:3b"
  },
  "context": {
    "transcript_seconds": 60  // Context window (30-120)
  }
}
```

## Where Data is Stored

- **Logs**: `logs/session_YYYY-MM-DD_HH-MM-SS.jsonl`
- **Config**: `config.json` (gitignored)
- **Models**: Ollama stores in `~/.ollama/`

All processing is local - nothing sent to cloud (unless using Claude/OpenAI API).

## Next Steps

- Read `.claude/PROJECT.md` for full documentation
- Customize prompts in `config.json`
- Try different Whisper models for speed/quality tradeoff
- Add custom hotkeys
- Explore session logs for conversation history

## Getting Help

- Check `.claude/PROJECT.md` for troubleshooting
- GitHub: https://github.com/calebstacy/clue
- Logs are in `logs/` folder - include when reporting issues
