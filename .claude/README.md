# .claude Directory

This directory contains comprehensive documentation for the LocalCluely project.

## Files

### 📘 [PROJECT.md](PROJECT.md)
**Complete project documentation** covering:
- Architecture and file structure
- Configuration reference
- LLM provider setup (Ollama, Claude, OpenAI)
- UI design system and glassmorphic styling
- Troubleshooting guide
- Performance tuning
- Security notes
- Tech stack details

**Use this when:** You need to understand the full project architecture or look up specific configuration options.

### 🚀 [QUICKSTART.md](QUICKSTART.md)
**Fast-track guide to getting started:**
- 5-minute setup instructions
- Basic usage and hotkeys
- Common issues and fixes
- Quick configuration reference

**Use this when:** You're setting up the project for the first time or need a quick reminder of how things work.

### 🛠️ [DEVELOPMENT.md](DEVELOPMENT.md)
**Development and contribution guide:**
- How to make changes to the codebase
- Testing strategies
- Git workflow
- WSL + Windows development tips
- Debugging techniques
- Code style guidelines
- Security considerations

**Use this when:** You're actively developing features, fixing bugs, or need to understand how to work with the codebase.

## Quick Navigation

**I want to...**
- **Set up the project** → [QUICKSTART.md](QUICKSTART.md)
- **Understand the architecture** → [PROJECT.md](PROJECT.md)
- **Fix a bug** → [DEVELOPMENT.md](DEVELOPMENT.md) → Debugging section
- **Add a feature** → [DEVELOPMENT.md](DEVELOPMENT.md) → Making Changes
- **Change LLM provider** → [PROJECT.md](PROJECT.md) → LLM Provider Support
- **Customize the UI** → [PROJECT.md](PROJECT.md) → UI Design System
- **Troubleshoot issues** → [PROJECT.md](PROJECT.md) → Troubleshooting

## For AI Assistants (Claude, etc.)

When working on this project:

1. **First Time?** Read [PROJECT.md](PROJECT.md) to understand the architecture
2. **Making Changes?** Check [DEVELOPMENT.md](DEVELOPMENT.md) for workflow
3. **User Questions?** Reference [QUICKSTART.md](QUICKSTART.md) for common tasks

### Important Reminders
- ⚠️ `config.json` is gitignored - NEVER commit with API keys
- 🔄 Clear `__pycache__` after Python changes
- 🔪 Kill old Python processes before testing: `taskkill /F /IM python.exe`
- 🪟 Windows-only (WASAPI audio capture)
- 🎮 NVIDIA GPU required for fast transcription

## Project Context

**What is this?**
LocalCluely is a 100% local AI meeting assistant that:
- Captures system audio in real-time
- Transcribes with Whisper (GPU-accelerated)
- Provides AI suggestions via Ollama/Claude/OpenAI
- Uses a beautiful glassmorphic Electron UI
- Runs entirely on your machine (Ollama mode)

**Tech Stack:**
- Python 3.10+ (backend)
- Electron 28+ (frontend)
- faster-whisper (transcription)
- Ollama (default LLM)
- WASAPI (audio capture)
- TCP sockets (communication)

**Current State:**
- ✅ Fully functional with Ollama
- ✅ Multi-provider support (Ollama/Claude/OpenAI)
- ✅ Glassmorphic UI with rounded corners
- ✅ Real-time transcription and AI features
- ✅ Session logging
- ✅ Hotkey support

## Changelog

### 2025-12-07
- Fixed Ollama model configuration (llama3.2:3b)
- Added multi-provider LLM support (Ollama, Claude, OpenAI)
- Restored glassmorphic UI design with proper backdrop-filter
- Implemented rounded corners fallback for Windows
- Increased transparency and blur effects
- Fixed start.bat to kill old processes
- Created comprehensive .claude documentation

### Earlier
- Initial project setup
- Electron UI implementation
- WASAPI audio capture
- Whisper GPU transcription
- Socket bridge communication
- Session logging
