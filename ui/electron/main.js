const { app, BrowserWindow, dialog, ipcMain } = require('electron')
const path = require('path')
const { spawn } = require('child_process')
const { autoUpdater } = require('electron-updater')

ipcMain.handle('get-app-version', () => app.getVersion())

let apiProcess = null

function getApiBinaryPath() {
    const binaryName =
        process.platform === 'win32'
            ? 'personal-tracker-api.exe'
            : 'personal-tracker-api'
    if (app.isPackaged) {
        // electron-builder places extraResources at process.resourcesPath
        return path.join(process.resourcesPath, binaryName)
    }
    // Dev: binary staged in electron/binaries/
    return path.join(__dirname, 'binaries', binaryName)
}

function startApi() {
    const binaryPath = getApiBinaryPath()
    const userDataPath = app.getPath('userData')
    const dbPath = path.join(userDataPath, 'tracker.db')
    const uploadsPath = path.join(userDataPath, 'uploads')

    // Ensure data directories exist
    require('fs').mkdirSync(uploadsPath, { recursive: true })

    apiProcess = spawn(binaryPath, [], {
        cwd: userDataPath,
        env: {
            HOME: process.env.HOME,
            TMPDIR: process.env.TMPDIR || '/tmp',
            PATH: '/usr/bin:/bin:/usr/sbin:/sbin',
            PORT: '8743',
            HOST: '127.0.0.1',
            DATABASE_PATH: dbPath,
            UPLOADS_PATH: uploadsPath,
        },
    })

    apiProcess.stdout.on('data', (d) => console.log('[api]', d.toString()))
    apiProcess.stderr.on('data', (d) => console.error('[api]', d.toString()))
    apiProcess.on('error', (err) => console.error('[api] failed to start:', err))
    apiProcess.on('exit', (code, signal) => console.error('[api] exited — code:', code, 'signal:', signal))
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

function setupAutoUpdater() {
    autoUpdater.autoDownload = true
    autoUpdater.autoInstallOnAppQuit = true

    autoUpdater.on('update-downloaded', (info) => {
        dialog
            .showMessageBox({
                type: 'info',
                title: 'Update ready',
                message: `Version ${info.version} has been downloaded and will be installed when you quit the app.`,
                buttons: ['Install now', 'Later'],
                defaultId: 0,
            })
            .then(({ response }) => {
                if (response === 0) autoUpdater.quitAndInstall()
            })
    })

    autoUpdater.on('error', (err) => {
        console.error('[updater] error:', err.message)
    })

    // Check for updates (only when packaged — no update server in dev)
    if (app.isPackaged) {
        autoUpdater.checkForUpdates()
    }
}

app.whenReady().then(() => {
    startApi()
    // Poll until API is up, then open the window
    waitForApi('http://127.0.0.1:8743/api/v1/health', 30, 500, () => {
        createWindow()
        setupAutoUpdater()
    })

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
