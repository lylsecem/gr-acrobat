; GR Acrobat — Windows 安装程序（Windows 10 / 11，64 位与 32 位）。龙禹良制作
; 由 build/make-installer.js 编译：-DARCH=x64|ia32 -DAPPDIR=... -DOUTFILE=... -DVERSION=...
Unicode true
ManifestDPIAware true
SetCompressor /SOLID lzma
RequestExecutionLevel admin

!ifndef VERSION
  !define VERSION "2.0.0"
!endif
!ifndef ARCH
  !define ARCH "x64"
!endif
!ifndef APPDIR
  !define APPDIR "..\dist\win-unpacked"
!endif
!ifndef OUTFILE
  !define OUTFILE "..\dist\GR-Acrobat-Setup-${VERSION}-${ARCH}.exe"
!endif

!define APPNAME   "GR Acrobat"
!define EXENAME   "GR Acrobat.exe"
!define PUBLISHER "龙禹良制作"
!define PROGID    "GRAcrobat.Document"
!define IMGPROGID "GRAcrobat.Image"
!define REGBASE   "Software\LongYuliang\GRAcrobat"
!define UNINSTKEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\GRAcrobat"
!define OLDKEY    "Software\Microsoft\Windows\CurrentVersion\Uninstall\PDFWorkbench"
!define PDFMENU   "SystemFileAssociations\.pdf\shell\GRAcrobat"
!define IMGMENU   "SystemFileAssociations\image\shell\GRAcrobat.ToPdf"
!define RUNKEY    "Software\Microsoft\Windows\CurrentVersion\Run"
!define THUMBCLSID "{80FC8DA7-5504-4437-AF79-D37C756234E6}"                 ; build/thumbs/src/thumbs.c
!define THUMBKEY   "ShellEx\{e357fccd-a995-4576-b01f-234630154e96}"          ; IThumbnailProvider
!define APPROVED   "Software\Microsoft\Windows\CurrentVersion\Shell Extensions\Approved"
!ifndef THUMBDIR
  !define THUMBDIR "thumbs\${ARCH}"
!endif

Name "${APPNAME}"
OutFile "${OUTFILE}"
!if ${ARCH} == "x64"
  InstallDir "$PROGRAMFILES64\${APPNAME}"
!else
  InstallDir "$PROGRAMFILES\${APPNAME}"
!endif
InstallDirRegKey HKLM "${REGBASE}" "InstallDir"
BrandingText "${PUBLISHER}"

VIProductVersion "${VERSION}.0"
VIAddVersionKey /LANG=2052 "ProductName" "${APPNAME}"
VIAddVersionKey /LANG=2052 "FileDescription" "${APPNAME} 安装程序"
VIAddVersionKey /LANG=2052 "CompanyName" "${PUBLISHER}"
VIAddVersionKey /LANG=2052 "LegalCopyright" "© 2026 ${PUBLISHER}"
VIAddVersionKey /LANG=2052 "FileVersion" "${VERSION}"
VIAddVersionKey /LANG=2052 "ProductVersion" "${VERSION}"

!include "MUI2.nsh"
!include "x64.nsh"
!include "LogicLib.nsh"
!include "WinVer.nsh"
!include "FileFunc.nsh"
!include "Sections.nsh"

; 右键菜单和文件类型名称的文字跟随 Windows 的显示语言：中文、泰文，其余都用英文。
; 每次安装（包括自动更新）重新判断一次；测试时可以用 /MENULANG=zh|en|th 指定。
Var MenuLang
Var TxtOpen
Var TxtMerge
Var TxtSplit
Var TxtImages
Var TxtPrint
Var TxtPrintAll
Var TxtToPdf
Var TxtPdfType
Var TxtImgType
Function PickMenuTexts
  ${GetParameters} $0
  ClearErrors
  ${GetOptions} $0 "/MENULANG=" $MenuLang
  ${If} ${Errors}
  ${OrIf} $MenuLang == ""
    System::Call 'kernel32::GetUserDefaultUILanguage() i .r1'
    IntOp $1 $1 & 0x3FF                            ; the language without its country
    ${If} $1 = 0x04
      StrCpy $MenuLang "zh"
    ${ElseIf} $1 = 0x1E
      StrCpy $MenuLang "th"
    ${Else}
      StrCpy $MenuLang "en"
    ${EndIf}
  ${EndIf}
  ${If} $MenuLang == "zh"
    StrCpy $TxtOpen "打开"
    StrCpy $TxtMerge "合并所选文件"
    StrCpy $TxtSplit "拆分页面"
    StrCpy $TxtImages "转为图片"
    StrCpy $TxtPrint "打印"
    StrCpy $TxtPrintAll "合并打印"
    StrCpy $TxtToPdf "用 GR Acrobat 转为 PDF"
    StrCpy $TxtPdfType "PDF 文档"
    StrCpy $TxtImgType "图片"
  ${ElseIf} $MenuLang == "th"
    StrCpy $TxtOpen "เปิด"
    StrCpy $TxtMerge "รวมไฟล์ที่เลือก"
    StrCpy $TxtSplit "แยกหน้า"
    StrCpy $TxtImages "แปลงเป็นรูปภาพ"
    StrCpy $TxtPrint "พิมพ์"
    StrCpy $TxtPrintAll "รวมแล้วพิมพ์"
    StrCpy $TxtToPdf "แปลงเป็น PDF ด้วย GR Acrobat"
    StrCpy $TxtPdfType "เอกสาร PDF"
    StrCpy $TxtImgType "รูปภาพ"
  ${Else}
    StrCpy $TxtOpen "Open"
    StrCpy $TxtMerge "Merge selected files"
    StrCpy $TxtSplit "Split pages"
    StrCpy $TxtImages "Convert to images"
    StrCpy $TxtPrint "Print"
    StrCpy $TxtPrintAll "Merge and print"
    StrCpy $TxtToPdf "Convert to PDF with GR Acrobat"
    StrCpy $TxtPdfType "PDF Document"
    StrCpy $TxtImgType "Image"
  ${EndIf}
FunctionEnd

!define MUI_ICON   "..\icon.ico"
!define MUI_UNICON "..\icon.ico"
!define MUI_ABORTWARNING
!define MUI_COMPONENTSPAGE_NODESC

!define MUI_WELCOMEPAGE_TITLE "安装 ${APPNAME}"
!define MUI_WELCOMEPAGE_TEXT "${APPNAME} 是一个离线 PDF 软件：查看 PDF 和图片、转换（PDF 转图片、图片转 PDF）、合并拆分、打印。$\r$\n$\r$\n如果电脑上装过「PDF 工作台」，安装时会自动把它卸载。$\r$\n$\r$\n${PUBLISHER}"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

!define MUI_FINISHPAGE_TEXT "${APPNAME} 已安装完成。$\r$\n$\r$\n右键 PDF 文件可以看到「GR Acrobat」菜单（Windows 11 在「显示更多选项」里）。$\r$\n$\r$\n想双击 PDF 就用它打开：在接下来的「默认应用」设置里，把 .pdf 的打开方式选为「${APPNAME}」（也可以把 .jpg、.png 等图片设为用它打开）。Windows 要求这一步由你亲自确认。"
!define MUI_FINISHPAGE_RUN
!define MUI_FINISHPAGE_RUN_TEXT "启动 ${APPNAME}"
!define MUI_FINISHPAGE_RUN_FUNCTION LaunchApp
!define MUI_FINISHPAGE_SHOWREADME ""
!define MUI_FINISHPAGE_SHOWREADME_TEXT "打开「默认应用」设置，把它设为默认 PDF 程序"
!define MUI_FINISHPAGE_SHOWREADME_FUNCTION OpenDefaultApps
!define MUI_FINISHPAGE_NOREBOOTSUPPORT   ; 正被占用的旧缩略图组件会在下次开机时自动删除，不为此提示「立即重启」
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "SimpChinese"

Function .onInit
  ${IfNot} ${AtLeastWin10}
    MessageBox MB_ICONSTOP "${APPNAME} 需要 Windows 10 或 Windows 11。"
    Abort
  ${EndIf}
  !if ${ARCH} == "x64"
    ${IfNot} ${RunningX64}
      MessageBox MB_ICONSTOP "这是 64 位版本，这台电脑是 32 位 Windows。$\r$\n请改用 GR-Acrobat-Setup-${VERSION}-ia32.exe。"
      Abort
    ${EndIf}
  !endif
  ${If} ${RunningX64}
    SetRegView 64
  ${EndIf}
  Call KeepResidentChoice
FunctionEnd

Function un.onInit
  ${If} ${RunningX64}
    SetRegView 64
  ${EndIf}
FunctionEnd

Function OpenDefaultApps
  ExecShell "open" "ms-settings:defaultapps"
FunctionEnd

; Started through Explorer, so the program runs as the signed-in user, not as administrator
; (a program running as administrator can't take files dragged in from Explorer).
Function LaunchApp
  Exec '"$WINDIR\explorer.exe" "$INSTDIR\${EXENAME}"'
FunctionEnd

; An update started from inside the program (/S /UPDATE) starts the program again when done.
Function .onInstSuccess
  ${GetParameters} $0
  ClearErrors
  ${GetOptions} $0 "/UPDATE" $1
  ${IfNot} ${Errors}
    Call LaunchApp
  ${EndIf}
FunctionEnd

; 一个右键子菜单项：键名决定排序，$1 = 文字，$2 = 命令行参数（空则直接打开）
!macro MenuItem KEY LABEL FLAG MULTI
  WriteRegStr HKCR "${PDFMENU}\shell\${KEY}" "MUIVerb" "${LABEL}"
  !if "${MULTI}" == "1"
    WriteRegStr HKCR "${PDFMENU}\shell\${KEY}" "MultiSelectModel" "Player"
  !endif
  !if "${FLAG}" == ""
    WriteRegStr HKCR "${PDFMENU}\shell\${KEY}\command" "" '"$INSTDIR\${EXENAME}" "%1"'
  !else
    WriteRegStr HKCR "${PDFMENU}\shell\${KEY}\command" "" '"$INSTDIR\${EXENAME}" ${FLAG} "%1"'
  !endif
!macroend

; 一种图片：「打开方式」里有 GR Acrobat，「默认应用」里也能把它设为这种图片的打开程序
; （图片的缩略图由 Windows 按「图片」这一类画，不管默认程序是谁）
!macro ImageType EXT
  WriteRegStr HKCR "${EXT}\OpenWithProgids" "${IMGPROGID}" ""
  WriteRegStr HKCR "Applications\${EXENAME}\SupportedTypes" "${EXT}" ""
  WriteRegStr HKLM "${REGBASE}\Capabilities\FileAssociations" "${EXT}" "${IMGPROGID}"
!macroend
!macro un.ImageType EXT
  DeleteRegValue HKCR "${EXT}\OpenWithProgids" "${IMGPROGID}"
!macroend

Section "GR Acrobat（必需）" SecMain
  SectionIn RO
  Call PickMenuTexts

  ; 先卸载旧版「PDF 工作台」，避免两个程序同时登记 .pdf
  ReadRegStr $1 HKLM "${OLDKEY}" "UninstallString"
  ReadRegStr $2 HKLM "${OLDKEY}" "InstallLocation"
  ${If} $1 != ""
  ${AndIf} $2 != ""
    DetailPrint "正在卸载旧版「PDF 工作台」…"
    ExecWait '$1 /S _?=$2'
    RMDir /r "$2"
  ${EndIf}

  ; 如果程序正在运行（包括后台预加载），先关掉它，否则文件无法覆盖
  nsExec::Exec 'taskkill /f /im "${EXENAME}"'
  Pop $0
  ${If} $0 == 0
    Sleep 1000                     ; 等 Windows 释放刚关掉的程序文件
  ${EndIf}

  SetOutPath "$INSTDIR"
  File /r "${APPDIR}\*.*"
  WriteUninstaller "$INSTDIR\卸载 ${APPNAME}.exe"

  CreateShortcut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\${EXENAME}"
  CreateShortcut "$SMPROGRAMS\${APPNAME}.lnk" "$INSTDIR\${EXENAME}"

  ; 登记为可以打开 .pdf 的程序（出现在「打开方式」和「默认应用」里）
  WriteRegStr HKCR "${PROGID}" "" "$TxtPdfType"
  WriteRegStr HKCR "${PROGID}" "FriendlyTypeName" "$TxtPdfType"
  WriteRegStr HKCR "${PROGID}\DefaultIcon" "" "$INSTDIR\${EXENAME},0"
  WriteRegStr HKCR "${PROGID}\shell" "" "open"
  WriteRegStr HKCR "${PROGID}\shell\open" "FriendlyAppName" "${APPNAME}"
  WriteRegStr HKCR "${PROGID}\shell\open\command" "" '"$INSTDIR\${EXENAME}" "%1"'
  WriteRegStr HKCR "${PROGID}\shell\print\command" "" '"$INSTDIR\${EXENAME}" --print "%1"'
  WriteRegStr HKCR ".pdf\OpenWithProgids" "${PROGID}" ""
  WriteRegStr HKCR "Applications\${EXENAME}" "FriendlyAppName" "${APPNAME}"
  WriteRegStr HKCR "Applications\${EXENAME}\SupportedTypes" ".pdf" ""
  WriteRegStr HKCR "Applications\${EXENAME}\shell\open\command" "" '"$INSTDIR\${EXENAME}" "%1"'

  ; PDFium（Chrome 的 PDF 引擎）和用它的两个小组件：GRAcrobatThumbs.dll 给资源管理器画 PDF 缩略图，
  ; GRAcrobatUnlock.exe 在从有密码的 PDF 里导出页面时，生成一份不带密码的副本。
  ; Windows 显示过缩略图后会把组件留在内存里一阵子，所以每个版本放在自己的文件夹，更新时不用覆盖正在用的文件。
  SetOutPath "$INSTDIR\thumbs\${VERSION}"
  SetOverwrite try                   ; 重装同一版本时组件可能正被资源管理器使用：跳过（内容一样），不弹出错误
  File "${THUMBDIR}\GRAcrobatThumbs.dll"
  File "${THUMBDIR}\GRAcrobatUnlock.exe"
  File "${THUMBDIR}\pdfium.dll"
  SetOverwrite on
  File "thumbs\PDFium-licenses.txt"
  SetOutPath "$INSTDIR"
  ; 旧版本的组件文件夹：能删的现在删，正被占用的重启后删
  FindFirst $0 $1 "$INSTDIR\thumbs\*"
  ${DoWhile} $1 != ""
    ${If} $1 != "."
    ${AndIf} $1 != ".."
    ${AndIf} $1 != "${VERSION}"
      RMDir /r /REBOOTOK "$INSTDIR\thumbs\$1"
    ${EndIf}
    FindNext $0 $1
  ${Loop}
  FindClose $0

  ; 资源管理器里 PDF 的缩略图：显示首页，左下角带 GR Acrobat 标记（GR Acrobat 是默认 PDF 程序时）。
  ; 32 位版本装在 64 位 Windows 上时不注册：资源管理器是 64 位的，用不了 32 位组件。
  !if ${ARCH} == "ia32"
  ${IfNot} ${RunningX64}
  !endif
    WriteRegStr HKCR "CLSID\${THUMBCLSID}" "" "GR Acrobat PDF 缩略图"
    WriteRegStr HKCR "CLSID\${THUMBCLSID}\InprocServer32" "" "$INSTDIR\thumbs\${VERSION}\GRAcrobatThumbs.dll"
    WriteRegStr HKCR "CLSID\${THUMBCLSID}\InprocServer32" "ThreadingModel" "Apartment"
    WriteRegStr HKCR "${PROGID}\${THUMBKEY}" "" "${THUMBCLSID}"
    WriteRegStr HKCR "${PROGID}" "TypeOverlay" ""   ; 标记已画在左下角，不要 Windows 再在右下角加图标
    WriteRegStr HKLM "${APPROVED}" "${THUMBCLSID}" "GR Acrobat PDF 缩略图"
  !if ${ARCH} == "ia32"
  ${EndIf}
  !endif

  WriteRegStr HKLM "${REGBASE}" "InstallDir" "$INSTDIR"
  WriteRegStr HKLM "${REGBASE}\Capabilities" "ApplicationName" "${APPNAME}"
  WriteRegStr HKLM "${REGBASE}\Capabilities" "ApplicationDescription" "离线 PDF 软件：查看 PDF 和图片、转换、合并拆分、打印"
  WriteRegStr HKLM "${REGBASE}\Capabilities" "ApplicationIcon" "$INSTDIR\${EXENAME},0"
  WriteRegStr HKLM "${REGBASE}\Capabilities\FileAssociations" ".pdf" "${PROGID}"
  WriteRegStr HKLM "Software\RegisteredApplications" "${APPNAME}" "${REGBASE}\Capabilities"

  ; 也能直接看图片
  WriteRegStr HKCR "${IMGPROGID}" "" "$TxtImgType"
  WriteRegStr HKCR "${IMGPROGID}" "FriendlyTypeName" "$TxtImgType"
  WriteRegStr HKCR "${IMGPROGID}\DefaultIcon" "" "$INSTDIR\${EXENAME},0"
  WriteRegStr HKCR "${IMGPROGID}\shell" "" "open"
  WriteRegStr HKCR "${IMGPROGID}\shell\open" "FriendlyAppName" "${APPNAME}"
  WriteRegStr HKCR "${IMGPROGID}\shell\open\command" "" '"$INSTDIR\${EXENAME}" "%1"'
  !insertmacro ImageType ".jpg"
  !insertmacro ImageType ".jpeg"
  !insertmacro ImageType ".png"
  !insertmacro ImageType ".gif"
  !insertmacro ImageType ".bmp"
  !insertmacro ImageType ".webp"

  ; 右键菜单：任何 PDF 上都有「GR Acrobat」子菜单，不论默认程序是谁
  WriteRegStr HKCR "${PDFMENU}" "MUIVerb" "GR Acrobat"
  WriteRegStr HKCR "${PDFMENU}" "Icon" "$INSTDIR\${EXENAME},0"
  WriteRegStr HKCR "${PDFMENU}" "SubCommands" ""
  WriteRegStr HKCR "${PDFMENU}" "MultiSelectModel" "Player"
  !insertmacro MenuItem "01open"  "$TxtOpen" "" "0"
  !insertmacro MenuItem "02merge" "$TxtMerge" "--merge" "1"
  !insertmacro MenuItem "03split" "$TxtSplit" "--split" "0"
  !insertmacro MenuItem "04image" "$TxtImages" "--pdf2img" "0"
  !insertmacro MenuItem "05print" "$TxtPrint" "--print" "0"
  !insertmacro MenuItem "06printall" "$TxtPrintAll" "--printall" "1"   ; 所选 PDF 按名称顺序一起打印
  ; 图片上：用 GR Acrobat 转为 PDF（多选的图片按顺序合成一个 PDF）
  WriteRegStr HKCR "${IMGMENU}" "MUIVerb" "$TxtToPdf"
  WriteRegStr HKCR "${IMGMENU}" "Icon" "$INSTDIR\${EXENAME},0"
  WriteRegStr HKCR "${IMGMENU}" "MultiSelectModel" "Player"
  WriteRegStr HKCR "${IMGMENU}\command" "" '"$INSTDIR\${EXENAME}" --img2pdf "%1"'

  ; 「设置 → 应用」里的卸载信息
  WriteRegStr HKLM "${UNINSTKEY}" "DisplayName" "${APPNAME}"
  WriteRegStr HKLM "${UNINSTKEY}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKLM "${UNINSTKEY}" "Publisher" "${PUBLISHER}"
  WriteRegStr HKLM "${UNINSTKEY}" "DisplayIcon" "$INSTDIR\${EXENAME},0"
  WriteRegStr HKLM "${UNINSTKEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "${UNINSTKEY}" "UninstallString" '"$INSTDIR\卸载 ${APPNAME}.exe"'
  WriteRegStr HKLM "${UNINSTKEY}" "QuietUninstallString" '"$INSTDIR\卸载 ${APPNAME}.exe" /S'
  WriteRegDWORD HKLM "${UNINSTKEY}" "NoModify" 1
  WriteRegDWORD HKLM "${UNINSTKEY}" "NoRepair" 1
  WriteRegDWORD HKLM "${UNINSTKEY}" "EstimatedSize" 270000

  System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0, p 0, p 0)'
SectionEnd

Section "开机后台预加载（旧电脑、机械硬盘推荐：打开 PDF 不再等待程序启动）" SecResident
  ; 登录后在后台静默启动并停在托盘，约占 100 MB 内存；以后可在程序左下角关闭
  WriteRegStr HKCU "${RUNKEY}" "${APPNAME}" '"$INSTDIR\${EXENAME}" --background'
SectionEnd

; 覆盖安装旧版本时沿用原来的「开机后台预加载」设置（静默更新也一样）
Function KeepResidentChoice
  ReadRegStr $0 HKLM "${REGBASE}" "InstallDir"
  ReadRegStr $1 HKCU "${RUNKEY}" "${APPNAME}"
  ${If} $0 != ""
  ${AndIf} $1 == ""
    !insertmacro UnselectSection ${SecResident}
  ${EndIf}
FunctionEnd

Section "Uninstall"
  nsExec::Exec 'taskkill /f /im "${EXENAME}"'
  Pop $0
  ${If} $0 == 0
    Sleep 1000
  ${EndIf}

  Delete "$DESKTOP\${APPNAME}.lnk"
  Delete "$SMPROGRAMS\${APPNAME}.lnk"
  RMDir /r /REBOOTOK "$INSTDIR"                  ; 缩略图组件若正被资源管理器占用，重启后删除
  DeleteRegKey HKCR "CLSID\${THUMBCLSID}"
  DeleteRegValue HKLM "${APPROVED}" "${THUMBCLSID}"

  DeleteRegValue HKCU "${RUNKEY}" "${APPNAME}"
  RMDir /r "$APPDATA\gr-acrobat\ocr"            ; 文字识别附加功能（程序自己的组件，不是用户资料），在程序的数据文件夹里
  DeleteRegKey HKCR "${PDFMENU}"
  DeleteRegKey HKCR "${IMGMENU}"
  DeleteRegValue HKCR ".pdf\OpenWithProgids" "${PROGID}"
  DeleteRegKey HKCR "${PROGID}"
  !insertmacro un.ImageType ".jpg"
  !insertmacro un.ImageType ".jpeg"
  !insertmacro un.ImageType ".png"
  !insertmacro un.ImageType ".gif"
  !insertmacro un.ImageType ".bmp"
  !insertmacro un.ImageType ".webp"
  DeleteRegKey HKCR "${IMGPROGID}"
  DeleteRegKey HKCR "Applications\${EXENAME}"
  DeleteRegValue HKLM "Software\RegisteredApplications" "${APPNAME}"
  DeleteRegKey HKLM "${REGBASE}"
  DeleteRegKey /ifempty HKLM "Software\LongYuliang"
  DeleteRegKey HKLM "${UNINSTKEY}"

  System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0, p 0, p 0)'
SectionEnd
