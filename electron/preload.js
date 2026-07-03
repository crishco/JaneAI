const { contextBridge } = require('electron')

const BACKEND_URL = process.env.JANE_BACKEND_URL || 'http://127.0.0.1:8765'

contextBridge.exposeInMainWorld('janeAPI', {
  backendUrl: BACKEND_URL,
  platform: process.platform,
})
