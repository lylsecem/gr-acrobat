// Sets the program icon and publisher details on the packaged Windows exe.
// Pure JavaScript (resedit), so the Windows build also works from Linux/macOS without Wine.
const fs = require('fs');
const path = require('path');
const ResEdit = require('resedit');

exports.default = async function afterPack(context) {
  if (context.electronPlatformName !== 'win32') return;
  const appInfo = context.packager.appInfo;
  const exePath = path.join(context.appOutDir, `${appInfo.productFilename}.exe`);
  const exe = ResEdit.NtExecutable.from(fs.readFileSync(exePath));
  const res = ResEdit.NtExecutableResource.from(exe);

  const iconFile = ResEdit.Data.IconFile.from(fs.readFileSync(path.join(__dirname, '..', 'icon.ico')));
  const group = ResEdit.Resource.IconGroupEntry.fromEntries(res.entries)[0];
  ResEdit.Resource.IconGroupEntry.replaceIconsForResource(
    res.entries, group ? group.id : 1, group ? group.lang : 1033, iconFile.icons.map((i) => i.data));

  const [major, minor, patch] = appInfo.version.split('.').map(Number);
  const vi = ResEdit.Resource.VersionInfo.fromEntries(res.entries)[0];
  const strings = {
    ProductName: appInfo.productName,
    FileDescription: appInfo.productName,
    CompanyName: '龙禹良制作',
    LegalCopyright: '© 2026 龙禹良制作',
    OriginalFilename: `${appInfo.productFilename}.exe`,
    InternalName: appInfo.productFilename,
    ProductVersion: appInfo.version,
    FileVersion: appInfo.version,
  };
  // Every language block Electron's exe carries gets the same details, so Explorer shows them whatever
  // the language of Windows.
  // Electron's own entries (SquirrelAwareVersion …) go: they are about Electron's installer, not this one.
  const langs = vi.getAllLanguagesForStringValues();
  for (const lang of langs.length ? langs : [{ lang: 1033, codepage: 1200 }]) {
    for (const key of Object.keys(vi.getStringValues(lang))) if (!(key in strings)) vi.removeStringValue(lang, key);
    vi.setStringValues(lang, strings);
  }
  vi.setFileVersion(major, minor, patch, 0, 1033);
  vi.setProductVersion(major, minor, patch, 0, 1033);
  vi.outputToResourceEntries(res.entries);

  res.outputResource(exe);
  fs.writeFileSync(exePath, Buffer.from(exe.generate()));
};
