const { app, BrowserWindow, ipcMain, Tray, Menu, screen } = require('electron');
const path = require('path');
const net = require('net');

let mainWindow;
let tray;
let pythonClient;

// Connect to Python backend via socket (optional - UI works without it)
let pythonConnected = false;
let receiveBuffer = '';

function connectToPython() {
    if (pythonConnected) return;

    pythonClient = new net.Socket();
    pythonClient.setTimeout(5000);

    pythonClient.connect(9999, '127.0.0.1', () => {
        console.log('Connected to Python backend');
        pythonConnected = true;
        receiveBuffer = '';
    });

    pythonClient.on('data', (data) => {
        receiveBuffer += data.toString();

        // Process complete messages (newline-delimited JSON)
        let newlineIndex;
        while ((newlineIndex = receiveBuffer.indexOf('\n')) !== -1) {
            const line = receiveBuffer.substring(0, newlineIndex);
            receiveBuffer = receiveBuffer.substring(newlineIndex + 1);

            if (line.trim()) {
                try {
                    const message = JSON.parse(line);
                    if (mainWindow) {
                        mainWindow.webContents.send('python-message', message);
                    }
                } catch (e) {
                    console.error('Failed to parse message:', e, 'Line:', line);
                }
            }
        }
    });

    pythonClient.on('error', (err) => {
        pythonConnected = false;
        receiveBuffer = '';
        // Silent retry - don't spam console
    });

    pythonClient.on('close', () => {
        pythonConnected = false;
        receiveBuffer = '';
    });
}

// Try to connect periodically but don't block
setInterval(() => {
    if (!pythonConnected) {
        connectToPython();
    }
}, 5000);

function createWindow() {
    const { width: screenWidth } = screen.getPrimaryDisplay().workAreaSize;

    mainWindow = new BrowserWindow({
        width: 476,  // Increased for 8px padding on each side
        height: 636, // Increased for 8px padding on each side
        x: screenWidth - 496,
        y: 72,
        frame: false,
        transparent: true,
        alwaysOnTop: true,
        skipTaskbar: false,
        resizable: false,
        hasShadow: true,
        backgroundColor: '#00000000',
        vibrancy: 'dark', // macOS
        backgroundMaterial: 'acrylic', // Windows
        roundedCorners: true, // Windows 11
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js')
        }
    });

    // For Windows 11, try to enable rounded corners via DWM
    if (process.platform === 'win32') {
        mainWindow.setBackgroundColor('#00000000');
    }

    mainWindow.loadFile('index.html');

    // Apply rounded corners after window loads
    mainWindow.webContents.on('did-finish-load', () => {
        // Inject CSS to ensure rounded corners clip content
        mainWindow.webContents.insertCSS(`
            html, body {
                border-radius: 16px;
                overflow: hidden;
            }
        `);
    });

    // Prevent window from being destroyed, just hide it
    mainWindow.on('close', (e) => {
        if (!app.isQuitting) {
            e.preventDefault();
            mainWindow.hide();
        }
    });

    // Dev tools for debugging
    // mainWindow.webContents.openDevTools();
}

function createTray() {
    // Create a simple tray icon (you can replace with actual icon file)
    tray = new Tray(path.join(__dirname, 'icon.png'));

    const contextMenu = Menu.buildFromTemplate([
        { label: 'Show', click: () => mainWindow.show() },
        { label: 'Hide', click: () => mainWindow.hide() },
        { type: 'separator' },
        { label: 'Quit', click: () => { app.isQuitting = true; app.quit(); }}
    ]);

    tray.setToolTip('LocalCluely');
    tray.setContextMenu(contextMenu);

    tray.on('click', () => {
        mainWindow.isVisible() ? mainWindow.hide() : mainWindow.show();
    });
}

app.whenReady().then(() => {
    createWindow();
    // createTray(); // Enable when you have an icon
    connectToPython();
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
    }
});

// IPC handlers for communication with renderer
ipcMain.on('send-to-python', (event, message) => {
    if (pythonClient && pythonClient.writable) {
        pythonClient.write(JSON.stringify(message) + '\n');
    }
});

ipcMain.on('window-drag', (event, { deltaX, deltaY }) => {
    const [x, y] = mainWindow.getPosition();
    mainWindow.setPosition(x + deltaX, y + deltaY);
});

ipcMain.on('minimize-window', () => {
    mainWindow.hide();
});

ipcMain.on('close-window', () => {
    app.isQuitting = true;
    app.quit();
});
