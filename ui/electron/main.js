const { app, BrowserWindow } = require('electron')
const path = require('path')
const { spawn } = require('child_process')

let apiProcess = null

function getApiBinaryPath() {
    if (app.isPackaged) {
        // electron-builder places extraResources at process.resourcesPath
        return path.join(process.resourcesPath, 'personal-tracker-api')
    }
    // Dev: binary staged in electron/binaries/
    return path.join(__dirname, 'binaries', 'personal-tracker-api')
}

function startApi() {
    const binaryPath = getApiBinaryPath()
    const userDataPath = app.getPath('userData')
    const dbPath = path.join(userDataPath, 'tracker.db')
    const uploadsPath = path.join(userDataPath, 'uploads')

    // Ensure data directories exist
    require('fs').mkdirSync(uploadsPath, { recursive: true })

    apiProcess = spawn(binaryPath, [], {
        env: {
            ...process.env,
            PORT: '8743',
            HOST: '127.0.0.1',
            DATABASE_PATH: dbPath,
            UPLOADS_PATH: uploadsPath,
        },
    })

    apiProcess.stdout.on('data', (d) => console.log('[api]', d.toString()))
    apiProcess.stderr.on('data', (d) => console.error('[api]', d.toString()))
    apiProcess.on('error', (err) => console.error('[api] failed to start:', err))
}

function waitForApi(url, retries, delay, callback) {
    const http = require('http')
    http.get(url, () => callback())
        .on('error', () => {
            if (retries <= 0) {
                console.error('[api] did not become ready in time')
                callback()
                return
            }
            setTimeout(() => waitForApi(url, retries - 1, delay, callback), delay)
        })
}

function createWindow() {
    const win = new BrowserWindow({
        width: 1280,
        height: 800,
        resizable: true,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
        },
    })

    if (app.isPackaged) {
        win.loadFile(path.join(__dirname, '..', 'dist', 'index.html'))
    } else {
        win.loadURL('http://localhost:3099')
    }
}

app.whenReady().then(() => {
    startApi()
    // Poll until API is up, then open the window
    waitForApi('http://127.0.0.1:8743/api/v1/health', 30, 500, createWindow)

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) createWindow()
    })
})

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit()
})

app.on('before-quit', () => {
    if (apiProcess) {
        apiProcess.kill()
        apiProcess = null
    }
})
