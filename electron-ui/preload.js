const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
    // Send message to Python backend
    sendToPython: (message) => ipcRenderer.send('send-to-python', message),

    // Receive messages from Python
    onPythonMessage: (callback) => ipcRenderer.on('python-message', (event, data) => callback(data)),

    // Window controls
    minimize: () => ipcRenderer.send('minimize-window'),
    close: () => ipcRenderer.send('close-window'),

    // Drag window
    startDrag: (deltaX, deltaY) => ipcRenderer.send('window-drag', { deltaX, deltaY })
});
