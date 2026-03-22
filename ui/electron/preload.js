const { contextBridge } = require('electron')

contextBridge.exposeInMainWorld('electron', {
    appVersion: process.env.APP_VERSION ?? '',
})
