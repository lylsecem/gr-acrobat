# 测试

所有测试都驱动**真实的程序**（Electron 窗口，通过调试端口用 Playwright 操作），不是模拟。

## 端到端测试（Windows、Linux、macOS 都能跑）

```
npm ci
pip install -r tests/requirements.txt
npm test                         # = python3 tests/run.py
python3 tests/run.py split       # 只跑文件名含 split 的
python3 tests/run.py --skip ocr  # 跳过文字识别（第一次要从 jsDelivr 下载约 17 MB 组件，存在 tests/.cache/）
```

测试文件由 `tests/make_fixtures.py` 生成到 `tests/.fixtures/`（它只会清空这个文件夹），测试过程中的文件、截图在
`tests/.out/`（都不进 git）。生成测试文件要用中文、泰文字体：Windows 自带；Linux 上装
`fonts-wqy-zenhei fonts-noto-cjk fonts-thai-tlwg`，另外需要 `xvfb`（没有显示器时自动开一个）。

| 文件 | 内容 |
|---|---|
| `e2e/test_viewer.py` | 鼠标滚轮 / 触控板翻页、↑↓ 键、Ctrl+滚轮和双指缩放、页面边缘的处理 |
| `e2e/test_tabs_images.py` | 同时打开多个文档（标签页）：再打开不关旧的、同一文件不重复、切换记住页码缩放、×/中键/Ctrl+W/右键菜单关闭、Ctrl+Tab；直接打开图片；「导出为图片」直接存成图片文件（不覆盖、只写在原文档旁边）；图片加入合并拆分 |
| `e2e/test_print_all.py` | 右键「合并打印」：多个 PDF 按文件名顺序进入打印（不论传来的顺序）、不开标签页、有密码的先问密码、打不开的跳过并说明 |
| `e2e/test_convert.py` | 转换：图片转 PDF（马上弹出保存窗口、按文件名顺序、页面大小、取消、坏图片、生成后打开）；PDF 转图片（选择窗口：格式、清晰度、页码、保存位置；多页进新文件夹、一页直接存；有密码的 PDF）；两个框和资源管理器右键菜单两种入口。保存窗口和文件夹窗口由 `GR_TEST_DIALOGS` 回答 |
| `e2e/test_password_hand_tool.py` | 有密码的 PDF：输错重输、取消、中文/泰文密码、只限打印的 PDF、导出与合并走无密码副本、大文件分块读取只问一次；放大后左键拖动 |
| `e2e/test_merge_split.py` | 合并拆分：拖到文档栏拆分、`原名_N.pdf` 取第一个空号、删除/保留原文档页面（打开着的标签跟着更新）、旋转保留、有密码的原文档、第二次启动加入文件、撤销、合并下载 |
| `e2e/test_language.py` | 中文 / English / ไทย：英文、泰文下每个界面、弹窗、菜单都没有中文残留；选择被记住；主进程消息跟随 |
| `e2e/test_top_bar_print.py` | 右上角打印按钮、Ctrl+O、打印窗口（到系统打印窗口为止）；深浅两种主题截图 |
| `e2e/test_update.py` | 自动更新：本地服务器代替 GitHub，提示、校验不对的下载、找不到的下载、同版本 / 旧版本不提示 |
| `e2e/test_ocr.py` | 文字识别：首次提示、从本地镜像安装（逐个校验，坏文件不装）、生成可搜索 PDF / 文字、泰文、旋转和偏移的页面、有密码的 PDF、移除 |

有密码的 PDF 导出时要用 `GRAcrobatUnlock.exe`。Windows 上测试直接用 `build/thumbs/x64` 里真正的 exe；
Linux 上有 Wine 时用 Wine 运行它，否则用 `tools/unlock_stand_in.py`（pikepdf）做同样的事、返回同样的退出码。

更新测试在 Windows 上不会走到「安装」这一步（那会真的请求管理员权限运行下载的文件），这一步只在 Linux 上测
（程序会回答「只能在 Windows 上安装」）。

## Windows 组件（在 Windows 上）

```
python tests/windows/test_components.py
```

按资源管理器的方式调用 `GRAcrobatThumbs.dll`（`windows/thumbs.py`，64 位；多线程同时要缩略图），按程序的方式运行
`GRAcrobatUnlock.exe`（64 位和 32 位，各种密码和出错情况）。32 位的缩略图组件要 32 位的调用者：PATH 里有
`i686-w64-mingw32-gcc` 时自动编译 `windows/thumbtest.c` 来测，否则跳过。

安装包（`npm run dist` 生成）没有自动测试：它会改写这台电脑的注册表和已安装的 GR Acrobat。要测就在虚拟机或
Windows 沙盒里安装，检查：右键菜单、「打开方式」里的 PDF 和图片、默认应用里能选 GR Acrobat、缩略图、覆盖安装、卸载。
