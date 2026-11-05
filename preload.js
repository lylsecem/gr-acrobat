// GR Acrobat — bridge between the page and the main process. 龙禹良制作
const { contextBridge, ipcRenderer, webUtils } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  // { action: 'open'|'merge'|'split'|'pdf2img'|'print'|'img2pdf', files: [{ path, name, size }] }
  onLaunch: (callback) => ipcRenderer.on('launch', (_event, launch) => callback(launch)),
  ready: () => ipcRenderer.invoke('app:ready'),
  readFile: (p) => ipcRenderer.invoke('file:read', p),
  readRange: (p, start, end) => ipcRenderer.invoke('file:range', p, start, end),
  print: () => ipcRenderer.invoke('print'),
  // An unprotected copy of a password-protected PDF, for saving pages from it: { bytes } or { error }
  unlockPdf: (bytes, password) => ipcRenderer.invoke('pdf:unlock', bytes, password),
  // Where a file picked or dropped in the page is on disk ('' when it isn't a file on this computer)
  pathOf: (file) => webUtils.getPathForFile(file),
  // 合并拆分: save split-off pages beside their document ({ path, name } or { error }), rewrite the original
  saveBeside: (srcPath, bytes) => ipcRenderer.invoke('pdf:save-beside', srcPath, bytes),
  replaceFile: (filePath, bytes) => ipcRenderer.invoke('pdf:replace', filePath, bytes),
  // Pictures of pages: a new folder beside the document or in a picked folder (parent) ({ dir, name } or { error });
  // a picture saved beside the document (dir null) or in such a folder ({ path, name } or { error }); a saved file
  // shown in Explorer
  makeFolder: (srcPath, name, parent) => ipcRenderer.invoke('export:folder', srcPath, name, parent),
  saveImage: (srcPath, dir, name, bytes) => ipcRenderer.invoke('export:image', srcPath, dir, name, bytes),
  showInFolder: (p) => ipcRenderer.invoke('export:show', p),
  // 转换: Windows' save window for a PDF made from pictures (the path picked, or null), writing the PDF there
  // ({ path, name } or { error }), and Windows' folder window for pictures (the folder picked, or null)
  choosePdfPath: (suggested) => ipcRenderer.invoke('convert:pdf-path', suggested),
  writePdf: (file, bytes) => ipcRenderer.invoke('convert:write-pdf', file, bytes),
  chooseFolder: (start) => ipcRenderer.invoke('convert:folder', start),
  getSettings: () => ipcRenderer.invoke('settings:get'),
  setResident: (on) => ipcRenderer.invoke('settings:set-resident', on),
  setLang: (lang) => ipcRenderer.invoke('settings:set-lang', lang),
  perf: (label) => ipcRenderer.send('perf', label),
  // { state: 'available'|'downloading'|'installing'|'error', version, notes?, percent?, message? }
  onUpdate: (callback) => ipcRenderer.on('update', (_event, u) => callback(u)),
  installUpdate: () => ipcRenderer.invoke('update:install'),
  // Text recognition add-on: { state: 'downloading', percent } or { state: 'error', message } while installing
  onOcr: (callback) => ipcRenderer.on('ocr', (_event, m) => callback(m)),
  installOcr: () => ipcRenderer.invoke('ocr:install'),
  removeOcr: () => ipcRenderer.invoke('ocr:remove'),
});
