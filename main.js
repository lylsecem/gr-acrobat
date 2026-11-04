// GR Acrobat — main process. 龙禹良制作
const { app, BrowserWindow, ipcMain, nativeTheme, Tray, Menu, protocol, net, shell, dialog } = require('electron');
const { pathToFileURL } = require('url');
const path = require('path');
const fs = require('fs');

const APP_NAME = 'GR Acrobat';
const APP_ID = 'com.lylsecem.gracrobat';
const PERF = !!process.env.GR_PERF;                 // GR_PERF=1 prints startup timings
const T0 = Date.now();
let bytesRead = 0;                                  // counted for the GR_PERF log only
const perf = (label) => { if (PERF) console.log(`[perf] ${label} +${Date.now() - T0}ms, read ${(bytesRead / 1048576).toFixed(1)} MB`); };

// The page is served from app://gr/ rather than file://, so pdf.js can run its parser in a real
// background thread (Chromium refuses workers on file:// pages, which pushes parsing onto the UI thread).
protocol.registerSchemesAsPrivileged([
  { scheme: 'app', privileges: { standard: true, secure: true, supportFetchAPI: true, corsEnabled: true } },
]);
function serveApp() {
  protocol.handle('app', (request) => {
    let rel = decodeURIComponent(new URL(request.url).pathname).replace(/^\/+/, '');
    // app://gr/ocr/… is the text recognition add-on, kept in the user's data folder.
    const root = rel.startsWith('ocr/') ? ocrDir() : path.resolve(__dirname);
    if (rel.startsWith('ocr/')) rel = rel.slice(4);
    const file = path.resolve(root, rel || 'index.html');
    if (!file.startsWith(root + path.sep)) return new Response('not found', { status: 404 });
    return net.fetch(pathToFileURL(file).toString());
  });
}

let mainWindow = null;
let tray = null;
let quitting = false;
let rendererReady = false;
const pendingLaunches = [];                        // launches that arrived before the page was ready

/* ---------- Settings (userData/settings.json) ---------- */
const settingsPath = () => path.join(app.getPath('userData'), 'settings.json');
function readSettings() {
  try { return JSON.parse(fs.readFileSync(settingsPath(), 'utf8')); } catch { return {}; }
}
function writeSettings(change) {
  fs.mkdirSync(path.dirname(settingsPath()), { recursive: true });
  fs.writeFileSync(settingsPath(), JSON.stringify({ ...readSettings(), ...change }));
}

/* ---------- Language: 中文, English, ไทย ---------- */
// Chosen in the window's bottom-left corner and kept in settings.json; until then Windows' display language
// (Chinese or Thai, anything else English). The window gets it in its address (index.html?lang=…).
const LANGS = ['zh', 'en', 'th'];
let lang = 'zh';
function systemLang() {
  const l = String((app.getPreferredSystemLanguages && app.getPreferredSystemLanguages()[0]) || app.getLocale() || '').toLowerCase();
  return l.startsWith('zh') ? 'zh' : l.startsWith('th') ? 'th' : 'en';
}
// Messages the main process shows are written in Chinese; mt() gives the chosen language ({name} marks a value).
const MESSAGES = {
  '密码不对。': ['Wrong password.', 'รหัสผ่านไม่ถูกต้อง'],
  '缺少解除密码保护的组件，请重新安装 GR Acrobat。': ['A component for unlocking PDFs is missing. Please reinstall GR Acrobat.', 'ไม่พบส่วนประกอบสำหรับปลดรหัสผ่าน PDF โปรดติดตั้ง GR Acrobat ใหม่'],
  '无法解除这个 PDF 的密码保护。': ["Couldn't remove this PDF's password protection.", 'ปลดรหัสผ่านของ PDF นี้ไม่ได้'],
  '不知道原文档在哪个文件夹。': ["The original document's folder isn't known.", 'ไม่ทราบว่าเอกสารต้นฉบับอยู่ในโฟลเดอร์ใด'],
  '没能保存到原文档所在的文件夹，这个文件夹可能不允许写入（{code}）。': ["Couldn't save in the original document's folder. The folder may not allow writing ({code}).", 'บันทึกในโฟลเดอร์ของเอกสารต้นฉบับไม่ได้ โฟลเดอร์อาจไม่อนุญาตให้เขียนไฟล์ ({code})'],
  '原文档的文件夹里同名的拆分文件太多了。': ['There are too many split files with this name in the folder.', 'ในโฟลเดอร์มีไฟล์ที่แยกออกมาชื่อเดียวกันมากเกินไป'],
  '找不到原文档。': ["The original document can't be found.", 'ไม่พบเอกสารต้นฉบับ'],
  '原文档可能正被别的程序打开，或者它所在的文件夹不允许写入。关掉别的程序后再试。': ["The original may be open in another program, or its folder doesn't allow writing. Close the other program and try again.", 'เอกสารต้นฉบับอาจเปิดอยู่ในโปรแกรมอื่น หรือโฟลเดอร์ไม่อนุญาตให้เขียนไฟล์ ปิดโปรแกรมอื่นแล้วลองอีกครั้ง'],
  '没能改写原文档（{code}）。': ["Couldn't rewrite the original document ({code}).", 'เขียนทับเอกสารต้นฉบับไม่ได้ ({code})'],
  '文件夹里同名的文件太多了。': ['There are too many files with this name in the folder.', 'ในโฟลเดอร์มีไฟล์ชื่อเดียวกันมากเกินไป'],
  '没能保存，这个文件夹可能不允许写入（{code}）。': ["Couldn't save. The folder may not allow writing ({code}).", 'บันทึกไม่ได้ โฟลเดอร์อาจไม่อนุญาตให้เขียนไฟล์ ({code})'],
  '不知道要保存到哪里。': ["Where to save it isn't known.", 'ไม่ทราบว่าจะบันทึกไว้ที่ใด'],
  '保存 PDF': ['Save PDF', 'บันทึก PDF'],
  '选择保存图片的文件夹': ['Choose a folder for the images', 'เลือกโฟลเดอร์สำหรับเก็บรูปภาพ'],
  '下载失败（{status}），请检查网络后重试': ['Download failed ({status}). Check the network and try again.', 'ดาวน์โหลดไม่สำเร็จ ({status}) โปรดตรวจสอบเครือข่ายแล้วลองอีกครั้ง'],
  '下载的文件不完整，请重试': ['The download was incomplete. Please try again.', 'ไฟล์ที่ดาวน์โหลดไม่สมบูรณ์ โปรดลองอีกครั้ง'],
  '下载中断，请检查网络后重试': ['The download was interrupted. Check the network and try again.', 'การดาวน์โหลดหยุดกลางคัน โปรดตรวจสอบเครือข่ายแล้วลองอีกครั้ง'],
  '只能在 Windows 上安装': ['Can only be installed on Windows.', 'ติดตั้งได้บน Windows เท่านั้น'],
  '没有开始安装：Windows 询问时选了「否」': ['Not installed: "No" was chosen when Windows asked.', 'ไม่ได้ติดตั้ง: เลือก “ไม่” เมื่อ Windows ถาม'],
  '打开 {app}': ['Open {app}', 'เปิด {app}'],
  '退出': ['Quit', 'ออก'],
};
function mt(zh, vars) {
  const tr = MESSAGES[zh];
  const text = (lang !== 'zh' && tr && tr[lang === 'en' ? 0 : 1]) || zh;
  return vars ? text.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? vars[k] : m)) : text;
}
// An error whose message is meant for the person (the others are replaced by a general one).
const shownError = (message) => Object.assign(new Error(message), { shown: true });
// Resident mode: start hidden at login and stay in the tray, so opening a PDF never pays the cold start.
// Windows keeps it as a login item; elsewhere (development only) the settings file stands in.
function residentEnabled() {
  if (process.platform !== 'win32') return !!readSettings().resident;
  const items = app.getLoginItemSettings({ path: process.execPath, args: ['--background'] });
  return items.openAtLogin || items.launchItems.some((i) => i.name === APP_NAME && i.enabled);
}
function setResident(on) {
  if (process.platform === 'win32') {
    app.setLoginItemSettings({ openAtLogin: on, path: process.execPath, args: ['--background'], name: APP_NAME });
  } else {
    writeSettings({ resident: on });
  }
  updateTray(on);
}

/* ---------- Launch arguments ---------- */
// Actions come from double-click / 打开方式 (open) and from the Explorer right-click menu. Open takes PDFs and
// pictures (the window shows both); 转为 PDF takes pictures and 转为图片 PDFs (both in 转换); the others take PDFs.
const ACTIONS = { '--merge': 'merge', '--split': 'split', '--pdf2img': 'pdf2img', '--print': 'print', '--img2pdf': 'img2pdf' };
const IMG_EXT = /\.(jpe?g|png|gif|bmp|webp|tiff?)$/i;
function parseArgs(argv) {
  let action = 'open';
  let background = false;
  const files = [];
  for (const a of argv.slice(1)) {
    if (ACTIONS[a]) action = ACTIONS[a];
    else if (a === '--background') background = true;
    else if (!a.startsWith('-') && (/\.pdf$/i.test(a) || IMG_EXT.test(a))) {
      try { if (fs.statSync(a).isFile()) files.push(path.resolve(a)); } catch {}
    }
  }
  if (action === 'img2pdf') return { action, background, files: files.filter((f) => IMG_EXT.test(f)) };
  if (action === 'open') return { action, background, files };
  return { action, background, files: files.filter((f) => /\.pdf$/i.test(f)) };
}

/* ---------- File access for the page ---------- */
// The page may only read files that were handed to it through a launch.
const allowed = new Set();
const prefetched = new Map();                       // path -> Promise<Buffer>, started at launch
const SMALL = 8 * 1024 * 1024;                      // files up to 8 MB are read whole; bigger ones on demand
const PREFETCH = 512 * 1024;

const handles = new Map();                          // path -> Promise<FileHandle>, a few kept open
function handleFor(p) {
  if (!handles.has(p)) {
    if (handles.size >= 8) { const [k, h] = handles.entries().next().value; handles.delete(k); h.then((x) => x.close()).catch(() => {}); }
    handles.set(p, fs.promises.open(p, 'r'));
  }
  return handles.get(p);
}
async function readRange(p, start, end) {
  const fh = await handleFor(p);
  const len = Math.max(0, end - start);
  const buf = Buffer.allocUnsafe(len);
  let off = 0;
  while (off < len) {
    const { bytesRead } = await fh.read(buf, off, len - off, start + off);
    if (!bytesRead) break;
    off += bytesRead;
  }
  bytesRead += off;
  return off === len ? buf : buf.subarray(0, off);
}
const readWhole = (p) => fs.promises.readFile(p).then((b) => { bytesRead += b.length; return b; });
const warmed = new Set();
function prefetch(p, size) {
  if (warmed.has(p)) return;
  warmed.add(p);
  if (size <= SMALL) {
    prefetched.set(p, readWhole(p));
  } else {
    // Warm the start and the end of a large file: the cross-reference table and the first page live there.
    readRange(p, 0, PREFETCH).catch(() => {});
    readRange(p, Math.max(0, size - PREFETCH), size).catch(() => {});
  }
}
function describe(files) {
  const out = [];
  for (const p of files) {
    try {
      const size = fs.statSync(p).size;
      allowed.add(p);
      prefetch(p, size);
      out.push({ path: p, name: path.basename(p), size });
    } catch {}
  }
  return out;
}

ipcMain.handle('file:read', async (_e, p) => {
  if (!allowed.has(p)) throw new Error('not allowed');
  const pending = prefetched.get(p);
  prefetched.delete(p);
  return pending || readWhole(p);
});
ipcMain.handle('file:range', (_e, p, start, end) => {
  if (!allowed.has(p)) throw new Error('not allowed');
  return readRange(p, start, end);
});

/* ---------- Delivering launches to the page ---------- */
// Explorer starts one process per selected file; their requests are gathered for a moment
// so that "合并" on five files opens one merge with five documents.
let batch = null;
function queueLaunch(parsed) {
  if (!parsed.files.length) return;
  if (batch && batch.action === parsed.action && (parsed.action === 'merge' || parsed.action === 'img2pdf')) {
    batch.files.push(...parsed.files);
    clearTimeout(batch.timer);
  } else {
    if (batch) { clearTimeout(batch.timer); flush(); }
    batch = { action: parsed.action, files: [...parsed.files] };
  }
  const gather = batch.action === 'merge' || batch.action === 'img2pdf' ? 350 : 0;
  batch.timer = setTimeout(flush, gather);
}
function flush() {
  if (!batch) return;
  const { action, files } = batch;
  batch = null;
  const launch = { action, files: describe([...new Set(files)]) };
  if (!launch.files.length) return;
  if (rendererReady && mainWindow) mainWindow.webContents.send('launch', launch);
  else pendingLaunches.push(launch);
  showWindow();
}

ipcMain.handle('app:ready', () => {
  rendererReady = true;
  perf('page ready');
  return pendingLaunches.splice(0);
});
ipcMain.on('perf', (_e, label) => perf(label));
ipcMain.handle('settings:get', () => ({
  resident: residentEnabled(), platform: process.platform, version: app.getVersion(), ocr: ocrInstalled(),
  update: update && !update.busy ? { state: 'available', version: update.version, notes: update.notes } : null,
}));
ipcMain.handle('settings:set-resident', (_e, on) => { setResident(!!on); return residentEnabled(); });
ipcMain.handle('settings:set-lang', (_e, value) => {
  if (!LANGS.includes(value)) return lang;
  lang = value;
  writeSettings({ lang });
  if (tray) updateTray(true);
  return lang;
});

// The page lays out the pages to print with print CSS, then asks for the system print window.
ipcMain.handle('print', (event) => new Promise((resolve) => {
  event.sender.print({ silent: false, printBackground: true }, (success, failureReason) => resolve({ success, failureReason }));
}));

// Saving pages from a password-protected PDF needs an unprotected copy (pdf-lib reads only unprotected PDFs).
// GRAcrobatUnlock.exe makes it with PDFium; it is installed with the thumbnail component and gets the password
// on its standard input. The copy passes through a temporary folder that is removed at once: { bytes } or { error }.
const unlockExe = () => process.env.GR_UNLOCK ||
  path.join(path.dirname(process.execPath), 'thumbs', app.getVersion(), 'GRAcrobatUnlock.exe');
ipcMain.handle('pdf:unlock', async (_e, bytes, password) => {
  const dir = fs.mkdtempSync(path.join(app.getPath('temp'), 'gr-'));
  const src = path.join(dir, 'in.pdf'), out = path.join(dir, 'out.pdf');
  try {
    fs.writeFileSync(src, bytes);
    const code = await new Promise((resolve) => {
      const p = require('child_process').spawn(unlockExe(), [src, out], { windowsHide: true, stdio: ['pipe', 'ignore', 'ignore'] });
      p.on('error', () => resolve(-1));
      p.on('close', resolve);
      p.stdin.on('error', () => {});
      p.stdin.end(String(password || ''), 'utf8');
    });
    if (code === 0) return { bytes: fs.readFileSync(out) };
    return { error: mt(code === 2 ? '密码不对。' : code === -1 ? '缺少解除密码保护的组件，请重新安装 GR Acrobat。' : '无法解除这个 PDF 的密码保护。') };
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

/* ---------- Splitting in 合并拆分 ---------- */
// Pages split off a document are saved beside it as <name>_1.pdf, <name>_2.pdf, … (the first free name: an
// existing file is never overwritten). { path, name } or { error }.
const isPdfPath = (p) => typeof p === 'string' && path.isAbsolute(p) && /\.pdf$/i.test(p);
ipcMain.handle('pdf:save-beside', (_e, srcPath, bytes) => {
  if (!isPdfPath(srcPath)) return { error: mt('不知道原文档在哪个文件夹。') };
  const dir = path.dirname(srcPath), base = path.basename(srcPath).replace(/\.pdf$/i, '');
  for (let n = 1; n < 10000; n++) {
    const p = path.join(dir, `${base}_${n}.pdf`);
    try {
      fs.writeFileSync(p, bytes, { flag: 'wx' });
      allowed.add(p);
      return { path: p, name: path.basename(p) };
    } catch (err) {
      if (err.code !== 'EEXIST') return { error: mt('没能保存到原文档所在的文件夹，这个文件夹可能不允许写入（{code}）。', { code: err.code || err.message }) };
    }
  }
  return { error: mt('原文档的文件夹里同名的拆分文件太多了。') };
});
// The original rewritten without the pages split off it: written beside it first, then put in its place, so a
// failure leaves the original as it was. { ok } or { error }.
ipcMain.handle('pdf:replace', async (_e, filePath, bytes) => {
  if (!isPdfPath(filePath) || !fs.existsSync(filePath)) return { error: mt('找不到原文档。') };
  const open = handles.get(filePath);               // a large file read in pieces has a handle kept open
  if (open) { handles.delete(filePath); await open.then((h) => h.close()).catch(() => {}); }
  prefetched.delete(filePath);
  const tmp = filePath + '.gr-new';
  try {
    fs.writeFileSync(tmp, bytes);
    fs.renameSync(tmp, filePath);
    return { ok: true };
  } catch (err) {
    fs.rmSync(tmp, { force: true });
    return { error: ['EBUSY', 'EPERM', 'EACCES'].includes(err.code)
      ? mt('原文档可能正被别的程序打开，或者它所在的文件夹不允许写入。关掉别的程序后再试。')
      : mt('没能改写原文档（{code}）。', { code: err.code || err.message }) };
  }
});

/* ---------- Pictures of pages (转换, 导出为图片) ---------- */
// Pages saved as pictures go where their document is, or into a folder picked in 转换: one picture right there,
// several in a new folder there (<name>_图片, or <name>_图片 (2)… when that is taken). A taken file name becomes
// <name> (2).png, (3)…: nothing is overwritten. The page may write only there, and show in Explorer only what it saved.
const isDocPath = (p) => typeof p === 'string' && path.isAbsolute(p) && (/\.pdf$/i.test(p) || IMG_EXT.test(p));
const isPlainName = (n) => typeof n === 'string' && n.length > 0 && n.length < 200 && n === path.basename(n) &&
  !/[<>:"/\\|?*\x00-\x1f]/.test(n) && !/^\.+$/.test(n);
const exportDirs = new Set();                       // folders made here or picked in the folder window
const exported = new Set();
const writeFailed = (err) => ({ error: mt('没能保存，这个文件夹可能不允许写入（{code}）。', { code: err.code || err.message }) });
// parent: a folder picked in 转换, or null for beside srcPath. { dir, name } or { error }
ipcMain.handle('export:folder', (_e, srcPath, name, parent) => {
  const where = parent ? (exportDirs.has(parent) ? parent : null) : (isDocPath(srcPath) ? path.dirname(srcPath) : null);
  if (!where || !isPlainName(name)) return { error: mt('不知道原文档在哪个文件夹。') };
  for (let n = 1; n < 1000; n++) {
    const dir = path.join(where, n === 1 ? name : `${name} (${n})`);
    try {
      fs.mkdirSync(dir);
      exportDirs.add(dir);
      return { dir, name: path.basename(dir) };
    } catch (err) {
      if (err.code !== 'EEXIST') return writeFailed(err);
    }
  }
  return { error: mt('文件夹里同名的文件太多了。') };
});
// dir: a folder made by export:folder or picked in 转换, or null for beside srcPath. { path, name } or { error }.
ipcMain.handle('export:image', (_e, srcPath, dir, name, bytes) => {
  const where = dir ? (exportDirs.has(dir) ? dir : null) : (isDocPath(srcPath) ? path.dirname(srcPath) : null);
  if (!where || !isPlainName(name) || !/\.(png|jpe?g)$/i.test(name)) return { error: mt('不知道原文档在哪个文件夹。') };
  const ext = path.extname(name), stem = name.slice(0, -ext.length);
  for (let n = 1; n < 1000; n++) {
    const p = path.join(where, n === 1 ? name : `${stem} (${n})${ext}`);
    try {
      fs.writeFileSync(p, bytes, { flag: 'wx' });
      exported.add(p);
      return { path: p, name: path.basename(p) };
    } catch (err) {
      if (err.code !== 'EEXIST') return writeFailed(err);
    }
  }
  return { error: mt('文件夹里同名的文件太多了。') };
});
ipcMain.handle('export:show', (_e, p) => { if (exported.has(p)) shell.showItemInFolder(p); });

/* ---------- 转换: Windows' save and folder windows ---------- */
// Where a PDF made from pictures goes, and the folder for pictures of pages, are picked in Windows' own windows; the
// page may then write only there. The PDF may replace a file the person picked: the save window has asked about that.
// GR_TEST_DIALOGS (the tests) names a JSON file whose { save, folder } answer instead of the windows (null: cancelled).
const chosenPdfs = new Set();
const testAnswer = (key) => {
  try { return JSON.parse(fs.readFileSync(process.env.GR_TEST_DIALOGS, 'utf8'))[key] || null; } catch { return null; }
};
const startIn = (p) => (typeof p === 'string' && path.isAbsolute(p) ? p : undefined);
// The chosen path, or null when the window was cancelled.
ipcMain.handle('convert:pdf-path', async (_e, suggested) => {
  let file;
  if (process.env.GR_TEST_DIALOGS) file = testAnswer('save');
  else {
    const r = await dialog.showSaveDialog(mainWindow, { title: mt('保存 PDF'), defaultPath: startIn(suggested),
      filters: [{ name: 'PDF', extensions: ['pdf'] }] });
    file = r.canceled ? null : r.filePath;
  }
  if (!file) return null;
  if (!/\.pdf$/i.test(file)) file += '.pdf';
  chosenPdfs.add(file);
  return file;
});
// Written beside it first, then put in its place. { path, name } or { error }; the page may then open it.
ipcMain.handle('convert:write-pdf', (_e, file, bytes) => {
  if (!chosenPdfs.has(file)) return { error: mt('不知道要保存到哪里。') };
  chosenPdfs.delete(file);
  const tmp = file + '.gr-new';
  try {
    fs.writeFileSync(tmp, bytes);
    fs.renameSync(tmp, file);
  } catch (err) {
    fs.rmSync(tmp, { force: true });
    return writeFailed(err);
  }
  allowed.add(file);
  exported.add(file);
  return { path: file, name: path.basename(file) };
});
// The chosen folder, or null when the window was cancelled.
ipcMain.handle('convert:folder', async (_e, start) => {
  let dir;
  if (process.env.GR_TEST_DIALOGS) dir = testAnswer('folder');
  else {
    const r = await dialog.showOpenDialog(mainWindow, { title: mt('选择保存图片的文件夹'), defaultPath: startIn(start),
      properties: ['openDirectory', 'createDirectory'] });
    dir = r.canceled ? null : r.filePaths[0];
  }
  if (!dir) return null;
  exportDirs.add(dir);
  return dir;
});

/* ---------- Updates ---------- */
// New versions are GitHub releases of lylsecem/gr-acrobat: the two installers and latest.json
// ({ version, notes, notes_en, notes_th, files: { x64, ia32: { name, url, size, sha512 } } }). A little after starting, and every
// 6 hours while it runs, the program reads latest.json and the page offers a newer version. 立即更新
// downloads the installer, checks it and starts it with /S /UPDATE; Windows asks for administrator rights,
// and the installer replaces the program and starts it again.
const UPDATE_URL = process.env.GR_UPDATE_URL || 'https://github.com/lylsecem/gr-acrobat/releases/latest/download/latest.json';
const updateDir = () => path.join(app.getPath('temp'), 'GR Acrobat 更新');
let update = null;                                  // { version, notes, file, ready, busy } once a newer version is out
const sendUpdate = (msg) => { if (mainWindow) mainWindow.webContents.send('update', msg); };
function isNewer(a, b) {
  const x = String(a).split('.').map(Number), y = String(b).split('.').map(Number);
  for (let i = 0; i < 3; i++) if ((x[i] || 0) !== (y[i] || 0)) return (x[i] || 0) > (y[i] || 0);
  return false;
}
async function checkForUpdate() {
  if (update && update.busy) return;
  try {
    const res = await net.fetch(UPDATE_URL, { cache: 'no-store' });
    if (!res.ok) return;
    const info = await res.json();
    const file = info.files && info.files[process.arch === 'ia32' ? 'ia32' : 'x64'];
    if (!file || !isNewer(info.version, app.getVersion())) {
      fs.rm(updateDir(), { recursive: true, force: true }, () => {});   // the installer left by the last update
      return;
    }
    if (!update || update.version !== info.version) update = { version: info.version, notes: { zh: info.notes || '', en: info.notes_en, th: info.notes_th }, file };
    sendUpdate({ state: 'available', version: update.version, notes: update.notes });
  } catch {}                                        // offline, or GitHub out of reach: try again later
}
// Downloads a file from the first address that works, reporting the bytes received, and keeps it
// only if its size and SHA-512 checksum are right.
async function downloadVerified(urls, target, size, sha512, onBytes) {
  let lastError;
  for (const url of [].concat(urls)) {
    try {
      const res = await net.fetch(url, { cache: 'no-store' });
      if (!res.ok) throw shownError(mt('下载失败（{status}），请检查网络后重试', { status: res.status }));
      const hash = require('crypto').createHash('sha512');
      const fh = await fs.promises.open(target, 'w');
      let got = 0;
      try {
        for await (const chunk of res.body) {
          hash.update(chunk);
          await fh.write(chunk);
          got += chunk.length;
          onBytes(got);
        }
      } finally {
        await fh.close();
      }
      if (got !== size || hash.digest('base64') !== sha512) throw shownError(mt('下载的文件不完整，请重试'));
      return;
    } catch (err) {
      lastError = err.shown ? err : shownError(mt('下载中断，请检查网络后重试'));
    }
  }
  throw lastError;
}
async function downloadUpdate() {
  const { file, version } = update;
  const dir = updateDir();
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  const target = path.join(dir, path.basename(file.name));
  let shown = -1;
  await downloadVerified(file.url, target, file.size, file.sha512, (got) => {
    const percent = Math.min(100, Math.floor(got * 100 / file.size));
    if (percent !== shown) { shown = percent; sendUpdate({ state: 'downloading', version, percent }); }
  });
  return target;
}
// The installer needs administrator rights. PowerShell's Start-Process -Verb RunAs shows Windows'
// confirmation and exits with an error when it is refused.
function startInstaller(file) {
  return new Promise((resolve, reject) => {
    if (process.platform !== 'win32') { reject(new Error(mt('只能在 Windows 上安装'))); return; }
    const ps = require('child_process').spawn('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command',
      `Start-Process -FilePath '${file.replace(/'/g, "''")}' -ArgumentList '/S','/UPDATE' -Verb RunAs`], { windowsHide: true });
    ps.on('error', reject);
    ps.on('exit', (code) => (code === 0 ? resolve() : reject(new Error(mt('没有开始安装：Windows 询问时选了「否」')))));
  });
}
ipcMain.handle('update:install', async () => {
  if (!update || update.busy) return;
  update.busy = true;
  try {
    if (!update.ready || !fs.existsSync(update.ready)) update.ready = await downloadUpdate();
    sendUpdate({ state: 'installing', version: update.version });
    await startInstaller(update.ready);
    app.quit();                                     // the installer replaces the program's files, then starts it again
  } catch (err) {
    sendUpdate({ state: 'error', version: update.version, message: err.message });
  } finally {
    update.busy = false;
  }
});

/* ---------- Text recognition (OCR) add-on ---------- */
// Optional, and only installed when the user asks for it. The Tesseract engine (tesseract.js) and its
// Simplified Chinese, English and Thai models are downloaded from the npm mirrors on jsDelivr or unpkg
// into the user's data folder, each file checked against the size and checksum below. Nothing of it is
// read at start-up: the page loads it only when 文字识别 runs.
const OCR_VERSION = '1';
const OCR_FILES = [                                 // [file, path on the npm mirrors, size, sha512]
  ['tesseract.min.js', 'tesseract.js@7.0.0/dist/tesseract.min.js', 62961, 'kMjICPeuRYAQ5KvL0+s/ln7a+96IKohiAtfaXKg37aSLmzfP0nFweeaE7lDRN01XIjn0jUfYT5kSFM4XmcTThQ=='],
  ['worker.min.js', 'tesseract.js@7.0.0/dist/worker.min.js', 111307, 'EP+LbGLOFbGWC1aKAVdZ93LHibWGTETmv9WFn/cCOcPbHX/KwufvSB0MoKqUEOlgg81FuWyiPld1swTTRCVroQ=='],
  // The engine in three builds; the page picks the fastest one this computer's processor can run.
  ['tesseract-core-relaxedsimd-lstm.wasm.js', 'tesseract.js-core@7.0.0/tesseract-core-relaxedsimd-lstm.wasm.js', 3905767, 'MyG1ftBec6coMz6xGRd7zpNsZE3jqcX/LvyJUjPFr1VlAdke7jznyLNTj60xTTKW4dNanEY89maVSTcZH7U0eQ=='],
  ['tesseract-core-simd-lstm.wasm.js', 'tesseract.js-core@7.0.0/tesseract-core-simd-lstm.wasm.js', 3899472, '0yT2Wuwh97tRTT/WNdD2MIWIe+6OkBKbJajPowZxVeHOaTwrFEkRJkNdCU75o90zFPvYetVZm08iO6GHHss7Ng=='],
  ['tesseract-core-lstm.wasm.js', 'tesseract.js-core@7.0.0/tesseract-core-lstm.wasm.js', 3896484, '/P145+qizqSAgL2ExxYKGYp9pb+GMhNT0XPeDaXKfo1reWgXeO1DaXBMRcgpjZzZcj7MjO7Of03A8h58LChDhw=='],
  ['chi_sim.traineddata.gz', '@tesseract.js-data/chi_sim@1.0.0/4.0.0_best_int/chi_sim.traineddata.gz', 1718768, 'B20daP4TVCa1Ymg2tXkC12k2UUfaG7bgnQT9+kaWR4s5y+QSpjtncE1zRdfqXDeDCPtP62pGKoGeaL3TVBogiA=='],
  ['eng.traineddata.gz', '@tesseract.js-data/eng@1.0.0/4.0.0_best_int/eng.traineddata.gz', 2952873, 'P4DNceb+ok3w/jqI2gAI1ZuDNiQ56wqUJD0a+lewm5MzFNY5vWW70SEUfyU4ZDBn+gDy76lD8kdRz2t+5Srfeg=='],
  ['tha.traineddata.gz', '@tesseract.js-data/tha@1.0.0/4.0.0_best_int/tha.traineddata.gz', 896631, 'Kr2SHeKDn+AlrgRXMDqtf5+6h70072ixI7ZIukki6XMvBb8ez/Dfa4/sFNhJvhs5q182Enbs3iODYHURs2BkwA=='],
];
const OCR_MIRRORS = process.env.GR_OCR_MIRROR ? [process.env.GR_OCR_MIRROR] : ['https://cdn.jsdelivr.net/npm/', 'https://unpkg.com/'];
const ocrDir = () => path.join(app.getPath('userData'), 'ocr');
const ocrInstalled = () => {
  try { return fs.readFileSync(path.join(ocrDir(), 'installed'), 'utf8') === OCR_VERSION; } catch { return false; }
};
let ocrBusy = false;
ipcMain.handle('ocr:install', async (event) => {
  if (ocrBusy || ocrInstalled()) return ocrInstalled();
  ocrBusy = true;
  const send = (msg) => { if (!event.sender.isDestroyed()) event.sender.send('ocr', msg); };
  const tmp = ocrDir() + '-download';
  try {
    fs.rmSync(tmp, { recursive: true, force: true });
    fs.mkdirSync(tmp, { recursive: true });
    const total = OCR_FILES.reduce((n, f) => n + f[2], 0);
    let done = 0, shown = -1;
    for (const [name, npmPath, size, sha512] of OCR_FILES) {
      await downloadVerified(OCR_MIRRORS.map((m) => m + npmPath), path.join(tmp, name), size, sha512, (got) => {
        const percent = Math.floor((done + got) * 100 / total);
        if (percent !== shown) { shown = percent; send({ state: 'downloading', percent }); }
      });
      done += size;
    }
    fs.writeFileSync(path.join(tmp, 'installed'), OCR_VERSION);
    fs.rmSync(ocrDir(), { recursive: true, force: true });
    fs.renameSync(tmp, ocrDir());                   // complete, or not there at all
    return true;
  } catch (err) {
    fs.rmSync(tmp, { recursive: true, force: true });
    send({ state: 'error', message: err.message });
    return false;
  } finally {
    ocrBusy = false;
  }
});
ipcMain.handle('ocr:remove', () => { fs.rmSync(ocrDir(), { recursive: true, force: true }); return ocrInstalled(); });

/* ---------- Window and tray ---------- */
function createWindow({ show }) {
  mainWindow = new BrowserWindow({
    width: 1320,
    height: 880,
    minWidth: 760,
    minHeight: 480,
    show: false,
    title: APP_NAME,
    backgroundColor: nativeTheme.shouldUseDarkColors ? '#0e0e0e' : '#f2f5f4',
    icon: path.join(__dirname, 'icon.ico'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      spellcheck: false,
      backgroundThrottling: false,                  // a pre-loaded hidden window stays ready
    },
  });
  mainWindow.setMenuBarVisibility(false);
  mainWindow.loadURL(`app://gr/index.html?lang=${lang}`);
  mainWindow.once('ready-to-show', () => { perf('ready-to-show'); if (show) mainWindow.show(); });
  mainWindow.on('close', (e) => {
    // In resident mode closing hides the window; the tray's 退出 really quits. The documents close with it, as
    // they would if the program quit, so the next file opened is not shown among old ones.
    if (!quitting && residentEnabled()) { e.preventDefault(); mainWindow.hide(); mainWindow.webContents.send('closed-to-tray'); }
  });
  mainWindow.on('closed', () => { mainWindow = null; rendererReady = false; });
}
function showWindow() {
  if (!mainWindow) { createWindow({ show: true }); return; }
  if (mainWindow.isMinimized()) mainWindow.restore();
  if (!mainWindow.isVisible()) mainWindow.show();
  mainWindow.focus();
}
function updateTray(on) {
  if (!on) { if (tray) { tray.destroy(); tray = null; } return; }
  if (!tray) {
    tray = new Tray(path.join(__dirname, 'icon.ico'));
    tray.setToolTip(APP_NAME);
    tray.on('click', showWindow);
  }
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: mt('打开 {app}', { app: APP_NAME }), click: showWindow },
    { type: 'separator' },
    { label: mt('退出'), click: () => app.quit() },
  ]));
}

/* ---------- Single instance ---------- */
const startup = parseArgs(process.argv);
// The second process hands its own argv over unchanged (Chromium may reorder the argv it reports).
const gotLock = app.requestSingleInstanceLock({ argv: process.argv });
if (!gotLock) {
  app.quit();
} else {
  if (process.platform === 'win32') app.setAppUserModelId(APP_ID);
  // Start reading the file at once, in parallel with Chromium starting up.
  if (startup.files.length) for (const f of startup.files) { try { prefetch(f, fs.statSync(f).size); } catch {} }

  app.on('second-instance', (_event, argv, _cwd, data) => {
    const parsed = parseArgs((data && Array.isArray(data.argv)) ? data.argv : argv);
    if (parsed.files.length) queueLaunch(parsed);
    else showWindow();
  });

  app.whenReady().then(() => {
    perf('app ready');
    serveApp();
    const saved = readSettings().lang;
    lang = LANGS.includes(saved) ? saved : systemLang();
    createWindow({ show: !startup.background });
    if (residentEnabled()) updateTray(true);
    if (startup.files.length) queueLaunch(startup);
    setTimeout(checkForUpdate, 8000);               // after the first file is on screen, not competing with it
    setInterval(checkForUpdate, 6 * 3600 * 1000);
  });
}

app.on('before-quit', () => { quitting = true; });
// In resident mode the program stays in the tray even if its window is gone; showWindow() makes a new one.
app.on('window-all-closed', () => { if (!residentEnabled()) app.quit(); });
