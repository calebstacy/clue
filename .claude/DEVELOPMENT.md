# Development Guide for LocalCluely

## For Claude/AI Assistants Working on This Project

### Project Understanding
This is a Windows-based local AI meeting assistant. Key points:
- **Platform**: Windows-only (WASAPI audio), WSL for development
- **GPU Required**: CUDA for Whisper transcription
- **Local-first**: Default mode uses Ollama (no cloud)
- **Architecture**: Python backend + Electron frontend
- **Communication**: TCP socket on port 9999

### Quick Orientation

**Main Files to Know:**
- `main_electron.py` - Entry point, orchestrates everything
- `llm_client.py` - Multi-provider LLM client (Ollama/Claude/OpenAI)
- `transcriber.py` - Whisper GPU transcription
- `audio_capture.py` - WASAPI loopback capture
- `socket_bridge.py` - Python ↔ Electron communication
- `electron-ui/index.html` - Glassmorphic UI
- `electron-ui/main.js` - Electron main process
- `start.bat` - Startup orchestration
- `config.json` - User configuration (gitignored!)

**Legacy Files (Don't Use):**
- `main.py` - Old PyQt version
- `overlay.py` - Old PyQt overlay UI

### Making Changes

#### Backend Changes (Python)
1. Edit the `.py` files
2. Clear cache: `cmd.exe /c "rmdir /s /q __pycache__"`
3. Kill old processes: `taskkill /F /IM python.exe`
4. Test with: `venv/Scripts/python.exe main_electron.py`

#### Frontend Changes (Electron)
1. Edit `electron-ui/index.html`, `main.js`, or `preload.js`
2. Restart Electron (close and reopen)
3. Changes to HTML/CSS are immediate on refresh

#### Configuration Changes
1. Edit `config.json` (never commit!)
2. Restart entire app for changes to take effect
3. Backend reads config on startup only

### Common Development Tasks

#### Adding a New LLM Provider
1. Update `llm_client.py`:
   - Add import (with try/except for optional)
   - Add to `__init__` provider initialization
   - Add to `_query_llm` method
2. Update `main_electron.py`:
   - Add to `--llm` choices in argparse
3. Update `requirements.txt` if needed
4. Document in `.claude/PROJECT.md`

#### Modifying UI Design
- Main styles in `electron-ui/index.html` `<style>` block
- Glassmorphic effect uses `backdrop-filter: blur()`
- Color variables at top of CSS
- Window size in `electron-ui/main.js` createWindow()
- Transparent padding (8px) for rounded corner fallback

#### Adding a Hotkey
1. Register in `main_electron.py` `_setup_hotkeys()` method
2. Add to `config.json` hotkeys section
3. Connect to appropriate handler function
4. Update documentation

#### Changing Transcription Model
- Edit `config.json` whisper.model
- Or use `--whisper` flag: `python main_electron.py --whisper medium`
- Options: tiny, base, small, medium, large-v3

### Testing Strategy

#### Manual Testing
1. **Ollama Connection**: Run quick test
   ```bash
   venv/Scripts/python.exe -c "from llm_client import LLMClient; c = LLMClient(provider='ollama', model='llama3.2:3b'); print(c.get_suggestion('Test'))"
   ```

2. **Whisper GPU**: Check startup logs for "cuda"

3. **Audio Capture**: Play audio and check transcript appears

4. **Socket Connection**: Backend logs "Electron UI connected"

5. **Full Flow**: Audio → Transcript → AI Response

#### Common Gotchas
- **Cache Issues**: Always clear `__pycache__` after changes
- **Multiple Backends**: Old Python processes stay running
- **Config Not Reloading**: Must restart backend
- **Electron Cache**: Sometimes need to clear Electron cache
- **Git Secrets**: NEVER commit config.json with API keys

### Git Workflow

#### Before Committing
1. Check `config.json` not staged: `git status`
2. Verify `.gitignore` includes config.json
3. Clear any API keys from code
4. Test the changes work

#### Commit Messages
Use descriptive commits following this format:
```
[Component] Brief description

Details:
- Change 1
- Change 2

Co-Authored-By: Claude <noreply@anthropic.com>
```

#### Branches
- `master` - Main branch, stable code
- Feature branches for experimental work
- Always test before merging to master

### Windows + WSL Development

**WSL Limitations:**
- Can't run Electron directly (X11 possible but slow)
- Can't access WASAPI (Windows-only)
- Can run Python backend for testing
- File paths: `/mnt/c/Users/...` in WSL = `C:\Users\...` in Windows

**Best Workflow:**
1. Edit files in WSL (good tools)
2. Test backend in WSL when possible
3. Full testing in Windows PowerShell
4. Git operations in WSL

**Path Conversions:**
- WSL to Windows: `/mnt/c/Users/caleb` → `C:\Users\caleb`
- Windows to WSL: `C:\Users\caleb` → `/mnt/c/Users/caleb`

### Performance Optimization

**Whisper Speed:**
- Model size: tiny (fastest) → large-v3 (best quality)
- compute_type: int8 (CPU) vs float16 (GPU)
- chunk_seconds: 5s is good balance

**LLM Speed:**
- Ollama: Local, fast for small models (llama3.2:3b)
- Claude API: Cloud, fast but costs money
- max_tokens: 150 for suggestions, 500+ for notes

**Memory Usage:**
- Whisper large-v3: ~4GB VRAM
- Ollama llama3.2:3b: ~2GB RAM
- Electron: ~100MB
- Total: ~6-8GB recommended

### Debugging

#### Enable Verbose Logging
Uncomment in `electron-ui/main.js`:
```javascript
mainWindow.webContents.openDevTools();
```

#### Check Backend Logs
Look for:
- Model loading confirmations
- Socket connection status
- Error messages from Ollama
- Transcript chunks

#### Common Error Messages

**"model 'llama3.x' not found"**
- Ollama model not pulled
- Wrong model name in config
- Old backend still running with old config

**"Could not find CUDA"**
- No NVIDIA GPU
- CUDA not installed
- Wrong compute_type in config

**"No loopback device found"**
- Not on Windows
- No audio playing
- Permissions issue

**"Waiting for Electron UI..."**
- Electron not started
- Port 9999 blocked
- Timing issue (wait longer)

### Code Style

**Python:**
- Follow PEP 8
- Type hints where helpful
- Docstrings for classes and complex functions
- Clear variable names

**JavaScript:**
- camelCase for variables
- Clear function names
- Comments for non-obvious logic

**CSS:**
- CSS variables for colors
- Consistent spacing (8px grid)
- Mobile-first (even though this is desktop)

### Security Considerations

**Never Commit:**
- API keys in any file
- config.json with real data
- Session logs with private conversations
- Personal audio recordings

**Safe Practices:**
- API keys in config.json only (gitignored)
- Environment variables for CI/CD
- Clear separation of config template vs real config
- Document what should be gitignored

### Deployment

**For End Users:**
1. ZIP the entire folder (minus venv, node_modules, logs, config.json)
2. Include README.md and requirements.txt
3. User runs setup steps from QUICKSTART.md
4. User creates their own config.json

**Future: Packaged Build**
- PyInstaller for Python backend
- Electron Builder for UI
- NSIS installer for Windows
- Auto-updater support

### Resources

**Dependencies:**
- [faster-whisper](https://github.com/guillaumekln/faster-whisper) - Whisper transcription
- [Ollama](https://github.com/ollama/ollama) - Local LLM runtime
- [PyAudioWPatch](https://github.com/s0d3s/PyAudioWPatch) - WASAPI audio capture
- [Electron](https://www.electronjs.org/) - UI framework
- [Anthropic SDK](https://github.com/anthropics/anthropic-sdk-python) - Claude API

**Documentation:**
- Whisper models: https://github.com/openai/whisper
- Ollama API: https://github.com/ollama/ollama/blob/main/docs/api.md
- Electron IPC: https://www.electronjs.org/docs/latest/tutorial/ipc
- Windows WASAPI: https://learn.microsoft.com/en-us/windows/win32/coreaudio/wasapi

### Getting Help

**Where to Look:**
1. `.claude/PROJECT.md` - Full project documentation
2. Session logs in `logs/` - Debug runtime issues
3. Electron DevTools - Frontend debugging
4. Backend console - Python errors
5. GitHub issues - Known problems

**What to Include in Bug Reports:**
- OS version
- GPU model
- Python version
- Ollama version
- Error message from backend console
- Relevant session log snippet
- Steps to reproduce

---

**Remember:** This is a local-first app. The goal is to keep everything running on the user's machine with zero cloud dependencies (except optional Claude/OpenAI API).
