// Compiles build/installer.nsi into dist/GR-Acrobat-Setup-<version>-<arch>.exe, and writes dist/latest.json
// for the GitHub release that installed copies check for updates.
// Runs after `electron-builder --win dir`. Works on Windows, macOS and Linux (no Wine needed).
const path = require('path');
const crypto = require('crypto');
const fs = require('fs');
const { execFileSync } = require('child_process');
const { getBinFromUrl } = require('app-builder-lib/out/binDownload');
const RELEASES = 'https://github.com/lylsecem/gr-acrobat/releases';
// NSIS 3.0.4.1, the build electron-builder itself uses (checksum from app-builder-lib).
const NSIS_PATH = () => process.env.ELECTRON_BUILDER_NSIS_DIR ||
  getBinFromUrl('nsis', '3.0.4.1', 'VKMiizYdmNdJOWpRGz4trl4lD++BvYP2irAXpMilheUP0pc93iKlWAoP843Vlraj8YG19CVn0j+dCo/hURz9+Q==');

(async () => {
  const root = path.join(__dirname, '..');
  const { version } = require(path.join(root, 'package.json'));
  const nsisDir = await NSIS_PATH();   // downloads NSIS once into electron-builder's cache
  const bin = process.platform === 'win32' ? path.join(nsisDir, 'Bin', 'makensis.exe')
    : path.join(nsisDir, process.platform === 'darwin' ? 'mac' : 'linux', 'makensis');
  if (process.platform !== 'win32') fs.chmodSync(bin, 0o755);
  const flag = process.platform === 'win32' ? '/' : '-';

  // One installer per architecture: 64-bit for most PCs, 32-bit for older ones running 32-bit Windows 10.
  const targets = [['x64', 'win-unpacked'], ['ia32', 'win-ia32-unpacked']];
  for (const [arch, dir] of targets) {
    const appDir = path.join(root, 'dist', dir);
    if (!fs.existsSync(appDir)) { console.log(`跳过 ${arch}：没有 dist/${dir}`); continue; }
    const thumbDir = path.join(__dirname, 'thumbs', arch);
    for (const f of ['GRAcrobatThumbs.dll', 'GRAcrobatUnlock.exe', 'pdfium.dll']) {
      if (!fs.existsSync(path.join(thumbDir, f))) throw new Error(`缺少 build/thumbs/${arch}/${f}：先运行 build/thumbs/build.sh`);
    }
    const out = path.join(root, 'dist', `GR-Acrobat-Setup-${version}-${arch}.exe`);
    execFileSync(bin, [
      `${flag}INPUTCHARSET`, 'UTF8',
      `${flag}DVERSION=${version}`, `${flag}DARCH=${arch}`, `${flag}DAPPDIR=${appDir}`, `${flag}DOUTFILE=${out}`,
      `${flag}DTHUMBDIR=${thumbDir}`,   // File Explorer thumbnails and the unlock helper, built by thumbs/build.sh
      `${flag}V2`, path.join(__dirname, 'installer.nsi'),
    ], { stdio: 'inherit', env: { ...process.env, NSISDIR: nsisDir, LANG: 'C.UTF-8', LC_ALL: 'C.UTF-8' } });   // UTF-8 locale keeps the Chinese text intact
    console.log('\n安装包已生成：' + out);
  }

  // latest.json: the version, the notes the program shows, and where each installer is with its checksum.
  // The notes the program shows, in Chinese, and in English and Thai when release-notes.en.txt / .th.txt exist.
  const read = (name) => fs.existsSync(path.join(__dirname, name)) ? fs.readFileSync(path.join(__dirname, name), 'utf8').trim() : undefined;
  const notes = read('release-notes.txt'), notes_en = read('release-notes.en.txt'), notes_th = read('release-notes.th.txt');
  const files = {};
  for (const [arch] of targets) {
    const name = `GR-Acrobat-Setup-${version}-${arch}.exe`;
    const file = path.join(root, 'dist', name);
    if (!fs.existsSync(file)) continue;
    const data = fs.readFileSync(file);
    // latest/download/<name> is the newest published release's copy, whatever its tag is called.
    files[arch] = { name, url: `${RELEASES}/latest/download/${name}`, size: data.length,
      sha512: crypto.createHash('sha512').update(data).digest('base64') };
  }
  if (!Object.keys(files).length) throw new Error('没有生成任何安装包：先运行 npm run pack:win');
  const latest = { version, notes: notes || '', files };
  if (notes_en) latest.notes_en = notes_en;
  if (notes_th) latest.notes_th = notes_th;
  fs.writeFileSync(path.join(root, 'dist', 'latest.json'), JSON.stringify(latest, null, 2) + '\n');
  console.log('更新信息已生成：' + path.join(root, 'dist', 'latest.json'));
})().catch((err) => { console.error(err.message || err); process.exit(1); });
