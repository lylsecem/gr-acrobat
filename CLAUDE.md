# GR Acrobat — 给 Claude Code 的项目说明

离线的 Windows PDF 软件（Electron）：查看 PDF 和图片（多个文档用标签页同时打开）、转换（图片转 PDF、PDF 转图片）、合并拆分、
打印、可选的文字识别。
作者龙禹良（GitHub：lylsecem），程序署名「龙禹良制作」。面向旧电脑、机械硬盘，**打开速度是第一要求**。

## 和作者沟通

- 用**中文**回答，说结果，不讲过程；作者不是程序员，避免术语，界面元素用程序里的名字（「合并拆分」「打印」）。
- 交付新版本时给出：做了什么、怎么测的、发布步骤。**只有作者明确要求时才发布**（推送版本标签就会发布）。
- 版本号：小改动升第三位（3.0.1），较大的功能升第二位，作者说「重大更新」时升第一位。

## 目录

```
main.js        主进程：单实例与启动参数（双击 / 打开方式打开 PDF 和图片；资源管理器右键菜单的 --merge/--split/--pdf2img/--print/--img2pdf）、
               文件读取白名单与按需分块读取、托盘与开机预加载、打印、自动更新、文字识别附加组件的下载、
               有密码 PDF 的解锁（调用 GRAcrobatUnlock.exe）、合并拆分写文件、转换的保存窗口和写文件、界面语言
preload.js     contextBridge：页面能调用的全部主进程功能（window.electronAPI）
index.html     界面和全部页面逻辑（单文件：样式、标记、一个 <script>），按「/* ---- 区块 ---- */」分段
i18n.js        界面语言：TEXTS 以中文原文为键，值是 [English, ไทย]；t()、translateMarkup()
vendor/        pdf.js 3.11（显示）、pdf-lib 1.17（写 PDF，延迟加载）、IBM Plex Sans
build/         打包：electron-builder 只生成目录，NSIS 安装程序由 make-installer.js 编译（任何系统都行）
build/thumbs/  两个 C 小组件（PDFium 8125）：资源管理器缩略图 GRAcrobatThumbs.dll、解锁 GRAcrobatUnlock.exe；
               编好的 x64/ia32 文件入库，改了 src/ 才用 build.sh 重编（MinGW-w64；Windows 上用 llvm-mingw 的
               msvcrt-x86_64 版，github.com/mstorsjo/llvm-mingw，放进 PATH）。缩略图左下角的标记是 badge-preview.png
               里画好的 12 个尺寸，改了它要运行 make-badge.py 生成 src/badge.h
tests/         端到端测试、测试文件生成（make_fixtures.py 只清空 tests/.fixtures）、Windows 组件测试（见 tests/README.md）
```

## 约定

- **界面文字**：在代码里用中文写，并且一律经过 `t('中文', { 变量 })`；新文字要在 `i18n.js` 的 `TEXTS` 补英文和泰文
  （英文的单复数由 t() 处理 "1 pages"）。标记里的静态中文由 translateMarkup() 自动翻译；JS 生成的界面在
  `applyLanguage()` 里重画。主进程的提示用 `mt()` 和 `main.js` 的 `MESSAGES`。`tests/e2e/test_language.py`
  会抓出英文、泰文界面里残留的中文。
- **速度**：启动路径上不加载 pdf-lib / 文字识别（`ensureLibs()` 按需加载），不在主进程启动时做同步重活。
  大文件（>8 MB）先只读显示第一页需要的字节。改动启动相关代码后用 `GR_PERF=1 npm start` 对比耗时。
- **不引入框架或打包工具**：纯 HTML/CSS/JS。index.html 是普通 script，全局作用域；函数声明只在本 script 内提升。
- **安全**：contextIsolation 打开、nodeIntegration 关闭；页面只能读启动时交给它的文件（main.js 的 `allowed`），
  写文件只有 `pdf:save-beside`（原名_N.pdf，绝不覆盖）、`pdf:replace`（先写临时文件再替换）、页面转图片的
  `export:folder` / `export:image`（只在文档旁边或「转换」里用文件夹窗口选的文件夹里写 png/jpg，同名加「 (2)」，
  绝不覆盖），以及图片转 PDF 的 `convert:write-pdf`（只写到 Windows 保存窗口里选的那个路径）；`export:show` 只在
  资源管理器里显示它刚存的文件。测试用 `GR_TEST_DIALOGS`（一个 JSON 文件）代替保存窗口和文件夹窗口的回答。
- **代码风格**：两个空格缩进；注释用英文、说明「为什么」；改动只碰需要的地方。
- **安装程序**（build/installer.nsi）：PDFium 组件放在 `thumbs\<版本>`（资源管理器会占用旧的 DLL）；旧版本目录
  用 `/REBOOTOK` 删除，并定义了 `MUI_FINISHPAGE_NOREBOOTSUPPORT`（否则完成页会默认「立即重启」）；组件用
  `SetOverwrite try`。缩略图处理程序挂在 ProgID `GRAcrobat.Document` 上，所以只在 GR Acrobat 是默认程序时生效。

## 测试

```
npm test                              # 全部端到端测试（真实程序 + Playwright），Windows 上约 3 分钟
python3 tests/run.py split language   # 只跑相关的
python tests/windows/test_components.py   # 改了 build/thumbs 时（在 Windows 上）
npm run dist                          # 改了安装程序时：能编出来；安装要在虚拟机 / Windows 沙盒里试（见 tests/README.md）
```

改了哪里就至少跑对应的测试；发布前跑全部。GitHub Actions 每次推送都会跑 `npm test`。新功能要加测试
（`tests/e2e/`，用 `helpers.App` 启动程序，`Report.check` 记录结果）。

## 发布

1. `package.json` 的 `version`；`build/release-notes.txt`（中文）、`.en.txt`、`.th.txt` 写这次的更新说明。
2. 提交、推送，然后 `git tag v版本号 && git push origin v版本号`：`.github/workflows/release.yml` 先测试，再打包，
   发布为正式版并设为最新。已安装的程序读 `releases/latest/download/latest.json` 提示更新，所以**绝不能发 pre-release**，
   也不要改安装包文件名的格式。

## 踩过的坑

- **绝不要把项目文件夹当作脚本的输出文件夹**：2026-11-03 一次 `make_fixtures.py` 的输出参数指向了项目根目录，
  它先 `rmtree` 输出文件夹，整个工作副本连 .git 一起被删（GitHub 上只有最初的提交）。跑带路径参数的脚本前先看它
  怎么用这个路径；要经常推送到 GitHub。
- Windows 上结束测试启动的程序要结束整棵进程树（`taskkill /T`），否则残留的子进程会锁住下一次测试的用户数据文件夹。
- 文字识别安装时的进度消息（`ocr`）可能比安装结果晚到：结果出来以后不再显示进度。

- Wine 里中文文件名需要 UTF-8 区域设置（`LANG=C.UTF-8`），否则「卸载 GR Acrobat.exe」等文件建不出来。
- `pkill -f`、`pgrep -f` 的模式会匹配到执行它的 shell 自己，用 `pgrep -f "名[字]"` 这种写法。
- Playwright 的 `page.evaluate('asyncFn()')` 会等 Promise 完成；会弹窗等回答的函数要包成 `() => { fn(); }`。
- 拖放时 dragleave 的 relatedTarget 常为空，用坐标判断是否真的离开。
- Electron 31 起取文件路径用 `webUtils.getPathForFile`（preload 的 `pathOf`），不要用 `File.path`。
- 文字识别：tesseract.js 的 `terminate()` 不会让等待中的任务失败，停止要靠 Promise.race。
