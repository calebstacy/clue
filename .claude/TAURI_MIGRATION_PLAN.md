# Tauri Migration Plan - Hybrid Approach

**Goal:** Migrate from Electron to Tauri while keeping the Python backend unchanged.

**Why:** Get native Windows Acrylic/Mica blur + macOS vibrancy without rewriting the entire application.

**Estimated Time:** 4-8 hours

**Status:** Ready to start

---

## Overview

### Current Architecture (Electron)
```
Python Backend (main_electron.py)
    ↓ [Socket 9999]
Electron UI (electron-ui/)
```

### Target Architecture (Tauri Hybrid)
```
Python Backend (main_electron.py) - UNCHANGED
    ↓ [Socket 9999]
Tauri UI (tauri-ui/) - NEW
```

### What Changes:
- ❌ Remove: Electron (electron-ui/)
- ✅ Add: Tauri frontend
- ✅ Keep: ALL Python backend code
- ✅ Keep: Socket bridge on port 9999
- ✅ Reuse: HTML/CSS/JS from Electron UI

---

## Phase 1: Setup Tauri Project (30 mins)

### Prerequisites
- [x] Node.js 18+ (already have)
- [x] Rust toolchain (need to install)
- [x] Python backend (already working)

### Install Rust
```bash
# Windows (PowerShell)
winget install --id Rustlang.Rustup

# Or download from: https://rustup.rs/
```

### Create Tauri App
```bash
# In project root
npm create tauri-app@latest

# Answers:
# - Project name: tauri-ui
# - Package manager: npm
# - UI template: Vanilla
# - Add TypeScript: No (keep it simple)
```

### Project Structure After Setup
```
cluely-local/
├── main_electron.py          # Python backend (unchanged)
├── tauri-ui/                  # NEW Tauri app
│   ├── src/                   # Frontend code
│   ├── src-tauri/             # Rust backend
│   │   ├── src/
│   │   │   └── main.rs        # Tauri main
│   │   ├── Cargo.toml         # Rust dependencies
│   │   └── tauri.conf.json    # Tauri config
│   └── package.json
├── electron-ui/               # OLD (keep for reference, remove later)
└── ...
```

---

## Phase 2: Configure Tauri for Glassmorphism (1 hour)

### Update `tauri-ui/src-tauri/tauri.conf.json`

```json
{
  "build": {
    "beforeBuildCommand": "",
    "beforeDevCommand": "",
    "devPath": "../src",
    "distDir": "../src"
  },
  "package": {
    "productName": "LocalCluely",
    "version": "0.1.0"
  },
  "tauri": {
    "allowlist": {
      "all": false,
      "window": {
        "all": false,
        "close": true,
        "hide": true,
        "show": true,
        "maximize": false,
        "minimize": true,
        "unmaximize": false,
        "unminimize": false,
        "startDragging": true
      }
    },
    "windows": [
      {
        "title": "LocalCluely",
        "width": 476,
        "height": 636,
        "resizable": false,
        "fullscreen": false,
        "decorations": false,
        "transparent": true,
        "alwaysOnTop": true,
        "skipTaskbar": false,
        "center": false,
        "x": 1400,
        "y": 72,
        "fileDropEnabled": false,
        "visible": true
      }
    ],
    "security": {
      "csp": null
    }
  }
}
```

### Update `tauri-ui/src-tauri/src/main.rs`

```rust
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{Manager, Runtime, Window};

#[cfg(target_os = "windows")]
fn apply_acrylic_blur<R: Runtime>(window: &Window<R>) {
    use window_vibrancy::apply_acrylic;

    // Apply Windows Acrylic blur
    apply_acrylic(&window, Some((18, 18, 23, 90)))
        .expect("Unsupported platform! 'apply_acrylic' is only supported on Windows 10/11.");
}

#[cfg(target_os = "macos")]
fn apply_acrylic_blur<R: Runtime>(window: &Window<R>) {
    use window_vibrancy::{apply_vibrancy, NSVisualEffectMaterial};

    // Apply macOS vibrancy
    apply_vibrancy(&window, NSVisualEffectMaterial::HudWindow, None, None)
        .expect("Unsupported platform! 'apply_vibrancy' is only supported on macOS 10.10+.");
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let window = app.get_window("main").unwrap();

            // Apply native blur effect
            apply_acrylic_blur(&window);

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

### Update `tauri-ui/src-tauri/Cargo.toml`

Add dependency:
```toml
[dependencies]
tauri = { version = "1.5", features = ["shell-open"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
window-vibrancy = "0.4"  # For native blur effects
```

---

## Phase 3: Port UI from Electron (2 hours)

### Copy Files
```bash
# Copy the HTML/CSS/JS from Electron
cp electron-ui/index.html tauri-ui/src/
cp electron-ui/styles.css tauri-ui/src/ (if separate)
```

### Update `tauri-ui/src/index.html`

**Remove Electron-specific code:**
```html
<!-- DELETE this Electron preload script -->
<script src="preload.js"></script>
```

**Add Tauri API:**
```html
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>LocalCluely</title>

  <!-- Tauri API -->
  <script type="module">
    import { appWindow } from '@tauri-apps/api/window';
    window.appWindow = appWindow;
  </script>
</head>
```

### Update Window Controls

**In the HTML, replace Electron IPC calls:**

**OLD (Electron):**
```javascript
// Minimize
window.electronAPI.minimize();

// Close
window.electronAPI.close();

// Drag window
window.electronAPI.startDrag(deltaX, deltaY);
```

**NEW (Tauri):**
```javascript
// Minimize
await window.appWindow.minimize();

// Close
await window.appWindow.close();

// Drag window (built-in with data-tauri-drag-region)
// Just add data-tauri-drag-region attribute to draggable elements
```

### Socket Connection (No Changes!)

The socket connection code stays EXACTLY the same since we're connecting to the Python backend on port 9999:

```javascript
// This code doesn't change!
const socket = new WebSocket('ws://localhost:9999');
// Or keep using raw TCP socket if already implemented
```

**Note:** The existing Electron UI uses raw TCP socket via Node.js `net` module. In Tauri, we'll use WebSocket instead (cleaner for browser context).

### Option: Update Python Backend to Support WebSocket

**Add to requirements.txt:**
```
websockets>=12.0
```

**Update socket_bridge.py** to support both TCP and WebSocket:
```python
# Add WebSocket support alongside existing TCP
# This way both Electron (old) and Tauri (new) can work during transition
```

**OR** simpler: Keep TCP socket and use a WebSocket-to-TCP bridge in Tauri's Rust backend.

---

## Phase 4: Update CSS for Native Blur (30 mins)

Since we now have NATIVE blur from the OS, we can simplify the CSS:

### Update Background Styles

**OLD (Electron - CSS blur):**
```css
.app {
    background: rgba(15, 15, 20, 0.35);
    backdrop-filter: blur(60px) saturate(200%);
    -webkit-backdrop-filter: blur(60px) saturate(200%);
}
```

**NEW (Tauri - native blur):**
```css
.app {
    background: rgba(15, 15, 20, 0.15);  /* More transparent! */
    /* NO backdrop-filter needed - OS handles it */
    /* The blur is REAL now */
}
```

**Make everything more transparent** since the native blur is stronger:
- Main container: 0.15 opacity (was 0.35)
- Cards: 0.02 opacity (was 0.04)
- Borders: Keep same or slightly more transparent

The result will be **glassier** and more beautiful!

---

## Phase 5: Update start.bat (15 mins)

### New Startup Script

**Create `start-tauri.bat`:**
```batch
@echo off
cd /d "%~dp0"
echo Starting LocalCluely with Tauri UI...
echo.

REM Kill any old Python processes
echo Cleaning up old processes...
taskkill /F /IM python.exe /T >nul 2>&1
timeout /t 1 /nobreak > nul

REM Start Python backend
echo Starting Python backend...
start "LocalCluely Backend" cmd /k "venv\Scripts\python.exe main_electron.py"

REM Wait for backend to initialize
echo Waiting for backend to initialize...
timeout /t 10 /nobreak > nul

REM Start Tauri UI
cd tauri-ui
echo Starting Tauri UI...
npm run tauri dev

REM Cleanup on exit
cd ..
taskkill /F /FI "WINDOWTITLE eq LocalCluely Backend*" > nul 2>&1
```

---

## Phase 6: Development Workflow

### Running During Development

**Terminal 1 - Python Backend:**
```bash
venv\Scripts\python.exe main_electron.py
```

**Terminal 2 - Tauri Dev:**
```bash
cd tauri-ui
npm run tauri dev
```

### Building Production Version

```bash
cd tauri-ui
npm run tauri build
```

**Output:** Single `.exe` installer in `tauri-ui/src-tauri/target/release/bundle/`

**Size comparison:**
- Electron app: ~100-120MB
- Tauri app: ~3-5MB (plus Python if distributed)

---

## Phase 7: Testing Checklist

### Visual Testing
- [ ] Window appears with rounded corners
- [ ] Native blur effect visible (not CSS blur)
- [ ] Transparency works correctly
- [ ] Window can be dragged
- [ ] Controls (minimize/close) work
- [ ] Always-on-top works

### Functional Testing
- [ ] Connects to Python backend on port 9999
- [ ] Receives transcript updates
- [ ] Receives AI suggestions
- [ ] Can send messages to backend
- [ ] Hotkeys work (might need new implementation)
- [ ] All three tabs work (Insights, Chat, Transcript)

### Cross-Platform Testing (if Mac available)
- [ ] macOS vibrancy effect works
- [ ] All features work on Mac

---

## Potential Issues & Solutions

### Issue 1: WebSocket vs TCP Socket

**Problem:** Electron UI uses raw TCP socket (Node.js `net` module). Browser/Tauri needs WebSocket.

**Solutions:**
1. **Option A:** Add WebSocket support to Python backend (simple with `websockets` library)
2. **Option B:** Create WebSocket-to-TCP bridge in Tauri's Rust code
3. **Option C:** Use Tauri's HTTP plugin to poll Python backend

**Recommended:** Option A (add WebSocket to Python) - cleanest solution.

### Issue 2: Hotkeys

**Problem:** Global hotkeys (Ctrl+Shift+Space) currently handled by Python with `pynput`.

**Solution:** Keep it in Python! Tauri app receives commands via socket when hotkey pressed.
- No changes needed if Python handles hotkeys
- OR migrate to Tauri's global-shortcut plugin

### Issue 3: Window Position

**Problem:** Need to position window in top-right corner.

**Solution:** Calculate in Tauri or set in config:
```rust
let monitor = window.current_monitor().unwrap().unwrap();
let screen_size = monitor.size();
let x = screen_size.width - 476 - 20;
window.set_position(tauri::Position::Physical(PhysicalPosition { x, y: 72 }));
```

---

## Rollback Plan

If Tauri doesn't work out:
1. Keep `electron-ui/` folder intact during development
2. Python backend unchanged - still works with Electron
3. Can switch back anytime by running old `start.bat`
4. Only delete `electron-ui/` after Tauri is fully working

---

## Success Criteria

**Migration is successful when:**
- [x] Tauri UI launches and connects to Python backend
- [x] Native blur effect visible (Windows Acrylic or macOS vibrancy)
- [x] All features work (transcript, suggestions, chat)
- [x] Performance is equal or better than Electron
- [x] App size is smaller than Electron version
- [x] User experience is better (more native feel)

---

## Next Steps After Completion

1. **Keep both versions** for a week to ensure stability
2. **Update documentation** in .claude/PROJECT.md
3. **Update README.md** with Tauri instructions
4. **Consider:** Full Rust migration (Phase 2 of migration)
5. **Test on macOS** if available
6. **Package for distribution**

---

## Resources

- **Tauri Docs:** https://tauri.app/v1/guides/
- **window-vibrancy:** https://github.com/tauri-apps/window-vibrancy
- **Tauri API:** https://tauri.app/v1/api/js/
- **Example Apps:** https://github.com/tauri-apps/awesome-tauri

---

## Notes for Tomorrow's Claude

**Context:**
- User wants native glassmorphic blur (not CSS hacks)
- Tauri provides native Windows Acrylic + macOS vibrancy
- We're keeping Python backend, only replacing Electron UI
- This is a hybrid approach - minimal risk, maximum visual improvement

**Start here:**
1. Install Rust if not installed
2. Create Tauri app with `npm create tauri-app@latest`
3. Follow Phase 2-3 to configure and port UI
4. Test with existing Python backend

**User expectations:**
- Beautiful native blur effect
- Cross-platform ready (Mac support later)
- Keep all existing functionality
- Better performance than Electron

**Time commitment:** Half day to full day of focused work.

Good luck! 🚀
