// GR Acrobat — the program's texts in English and Thai. 龙禹良制作
// The page is written in Chinese; each Chinese text maps to [English, ไทย], and {name} marks a value filled in.
// Loaded in <head>, before the page: it picks the language and keeps the page hidden until its markup is shown
// in that language (translateMarkup, called first thing by the page's script).
const LANGS = ['zh', 'en', 'th'];
let LANG = (() => {
  const asked = new URLSearchParams(location.search).get('lang');     // the desktop program passes its setting
  if (LANGS.includes(asked)) return asked;
  try { const kept = localStorage.getItem('lang'); if (LANGS.includes(kept)) return kept; } catch {}
  const n = (navigator.language || '').toLowerCase();
  return n.startsWith('zh') ? 'zh' : n.startsWith('th') ? 'th' : 'en';
})();
document.documentElement.lang = { zh: 'zh-CN', en: 'en', th: 'th' }[LANG];
if (LANG !== 'zh') {
  document.documentElement.classList.add('i18n-pending');
  setTimeout(() => document.documentElement.classList.remove('i18n-pending'), 3000);   // never stays hidden
}

const TEXTS = {
  // ---- side bar and top bar
  '龙禹良制作': ['Made by 龙禹良', 'สร้างโดย 龙禹良'],
  '功能': ['Features', 'ฟังก์ชัน'],
  '查看': ['View', 'ดู'],
  '合并拆分': ['Merge & split', 'รวมและแยก'],
  '图片转 PDF': ['Images to PDF', 'รูปภาพเป็น PDF'],
  '文字识别': ['Text recognition', 'อ่านข้อความ (OCR)'],
  '开机后台预加载': ['Preload at startup', 'โหลดล่วงหน้าตอนเปิดเครื่อง'],
  '旧电脑、机械硬盘打开更快': ['Opens faster on old PCs and hard drives', 'เปิดเร็วขึ้นบนคอมพิวเตอร์เก่าและฮาร์ดดิสก์'],
  'Ctrl+O 打开文件': ['Ctrl+O  Open a file', 'Ctrl+O  เปิดไฟล์'],
  'Ctrl+P 打印': ['Ctrl+P  Print', 'Ctrl+P  พิมพ์'],
  '版本 {v}': ['Version {v}', 'เวอร์ชัน {v}'],
  '语言': ['Language', 'ภาษา'],
  '打开菜单': ['Open menu', 'เปิดเมนู'],
  '打印': ['Print', 'พิมพ์'],
  '打印（Ctrl+P）': ['Print (Ctrl+P)', 'พิมพ์ (Ctrl+P)'],
  '已安装': ['installed', 'ติดตั้งแล้ว'],
  '未安装': ['not installed', 'ยังไม่ได้ติดตั้ง'],
  '安装': ['Install', 'ติดตั้ง'],
  '移除': ['Remove', 'นำออก'],

  // ---- viewer
  '共 {n} 页': ['{n} pages', 'ทั้งหมด {n} หน้า'],
  '全选': ['Select all', 'เลือกทั้งหมด'],
  '清除': ['Clear', 'ล้าง'],
  '反选': ['Invert', 'สลับการเลือก'],
  '页码范围': ['Pages', 'ช่วงหน้า'],
  '如 1-3,5,8': ['e.g. 1-3,5,8', 'เช่น 1-3,5,8'],
  '应用': ['Apply', 'ใช้'],
  '已选 0 页': ['0 selected', 'เลือก 0 หน้า'],
  '已选 {n} 页': ['{n} selected', 'เลือก {n} หน้า'],
  '上一页': ['Previous page', 'หน้าก่อนหน้า'],
  '下一页': ['Next page', 'หน้าถัดไป'],
  '缩小': ['Zoom out', 'ย่อ'],
  '放大': ['Zoom in', 'ขยาย'],
  '适合页面': ['Fit page', 'พอดีหน้า'],
  '适合宽度': ['Fit width', 'พอดีความกว้าง'],
  '还没有打开文件': ['No file is open', 'ยังไม่ได้เปิดไฟล์'],
  '把 PDF 或图片拖进窗口，或者从电脑里选择': ['Drag PDFs or pictures into the window, or choose them on this computer', 'ลากไฟล์ PDF หรือรูปภาพมาวางในหน้าต่าง หรือเลือกจากคอมพิวเตอร์'],
  '打开文件': ['Open files', 'เปิดไฟล์'],
  '无法打开': ["Can't open", 'เปิดไม่ได้'],
  '「{name}」已损坏或不是 PDF。': ['“{name}” is damaged or is not a PDF.', '“{name}” เสียหายหรือไม่ใช่ไฟล์ PDF'],
  '「{name}」无法显示：图片可能已损坏，或者是不支持的格式。': ['“{name}” can’t be shown: the picture may be damaged, or its format isn’t supported.', 'แสดง “{name}” ไม่ได้ รูปภาพอาจเสียหาย หรือเป็นรูปแบบที่ไม่รองรับ'],
  '无法加载组件': ["A component couldn't be loaded", 'โหลดส่วนประกอบไม่ได้'],
  '导出没有完成': ["The export didn't finish", 'ส่งออกไม่สำเร็จ'],
  '已导出 {n} 张图片': ['{n} images exported', 'ส่งออกรูปภาพแล้ว {n} รูป'],
  '打开文件夹': ['Open folder', 'เปิดโฟลเดอร์'],
  '_第{n}页': ['_page{n}', '_หน้า{n}'],
  '_节选': ['_pages', '_บางหน้า'],
  '_图片': ['_images', '_รูปภาพ'],

  // ---- 转换: pictures to a PDF, a PDF to pictures
  '转换': ['Convert', 'แปลงไฟล์'],
  'PDF 转图片': ['PDF to images', 'PDF เป็นรูปภาพ'],
  '把图片拖到这里，或点击选择': ['Drag pictures here, or click to choose', 'ลากรูปภาพมาวางที่นี่ หรือคลิกเพื่อเลือก'],
  'JPG、PNG、GIF、BMP、WebP，按文件名顺序每张一页': ['JPG, PNG, GIF, BMP, WebP: one page each, in file name order', 'JPG, PNG, GIF, BMP, WebP หน้าละรูป เรียงตามชื่อไฟล์'],
  '页面大小': ['Page size', 'ขนาดหน้า'],
  '把 PDF 拖到这里，或点击选择': ['Drag a PDF here, or click to choose', 'ลากไฟล์ PDF มาวางที่นี่ หรือคลิกเพื่อเลือก'],
  '每页直接存成一张图片（PNG 或 JPEG）': ['Each page is saved as an image (PNG or JPEG)', 'แต่ละหน้าบันทึกเป็นรูปภาพหนึ่งรูป (PNG หรือ JPEG)'],
  '图片格式': ['Image format', 'รูปแบบรูปภาพ'],
  'PNG（文字、线条清楚）': ['PNG (sharp text and lines)', 'PNG (ตัวอักษรและเส้นคมชัด)'],
  'JPEG（照片多时文件小）': ['JPEG (smaller files for photos)', 'JPEG (ไฟล์เล็กกว่าเมื่อมีภาพถ่ายมาก)'],
  '1x（和页面一样大）': ['1x (the size of the page)', '1x (ขนาดเท่าหน้า)'],
  '2x（推荐）': ['2x (recommended)', '2x (แนะนำ)'],
  '4x（最清楚，文件大）': ['4x (sharpest, large files)', '4x (คมชัดที่สุด ไฟล์ใหญ่)'],
  '页面': ['Pages', 'หน้า'],
  '保存位置': ['Save in', 'บันทึกที่'],
  '更改…': ['Change…', 'เปลี่ยน…'],
  '选了多页时，会在这里新建「{folder}」文件夹。': ['With several pages, a new folder “{folder}” is made here.', 'ถ้าเลือกหลายหน้า จะสร้างโฟลเดอร์ใหม่ “{folder}” ที่นี่'],
  '开始转换': ['Convert', 'เริ่มแปลง'],
  '正在转换第 {i} / {n} 页…': ['Converting page {i} of {n}…', 'กำลังแปลงหน้า {i} / {n}…'],
  '正在生成第 {i} / {n} 页…': ['Making page {i} of {n}…', 'กำลังสร้างหน้า {i} / {n}…'],
  '已生成 PDF': ['PDF made', 'สร้าง PDF แล้ว'],
  '共 {n} 页，保存为：{path}': ['{n} pages, saved as: {path}', 'ทั้งหมด {n} หน้า บันทึกเป็น: {path}'],
  '保存在新建的文件夹里：{path}': ['Saved in a new folder: {path}', 'บันทึกไว้ในโฟลเดอร์ใหม่: {path}'],
  '保存为：{path}': ['Saved as: {path}', 'บันทึกเป็น: {path}'],
  '转换没有完成': ["The conversion didn't finish", 'แปลงไม่สำเร็จ'],
  '这里放图片': ['Pictures go here', 'ที่นี่สำหรับรูปภาพ'],
  'PDF 请拖到右边的「PDF 转图片」。': ['Drag PDFs to “PDF to images” on the right.', 'ลากไฟล์ PDF ไปที่ “PDF เป็นรูปภาพ” ทางขวา'],
  '这里放 PDF': ['PDFs go here', 'ที่นี่สำหรับ PDF'],
  '图片请拖到左边的「图片转 PDF」。': ['Drag pictures to “Images to PDF” on the left.', 'ลากรูปภาพไปที่ “รูปภาพเป็น PDF” ทางซ้าย'],

  // ---- open documents (tabs above the page)
  '打开的文档': ['Open documents', 'เอกสารที่เปิดอยู่'],
  '打开文件（Ctrl+O）': ['Open files (Ctrl+O)', 'เปิดไฟล์ (Ctrl+O)'],
  '关闭其他文档': ['Close other documents', 'ปิดเอกสารอื่น'],
  '全部关闭': ['Close all', 'ปิดทั้งหมด'],

  // ---- password-protected PDFs
  '这个 PDF 有密码保护': ['This PDF is password-protected', 'PDF นี้มีรหัสผ่าน'],
  '输入打开密码': ['Enter the password', 'ใส่รหัสผ่าน'],
  '密码': ['Password', 'รหัสผ่าน'],
  '密码不对，请重新输入。': ['Wrong password. Please try again.', 'รหัสผ่านไม่ถูกต้อง โปรดลองอีกครั้ง'],
  '取消': ['Cancel', 'ยกเลิก'],
  '打开': ['Open', 'เปิด'],
  '知道了': ['OK', 'ตกลง'],
  '这个 PDF 有密码保护，网页版不能导出它的页面。': ["This PDF is password-protected; the web version can't export its pages.", 'PDF นี้มีรหัสผ่าน เวอร์ชันเว็บส่งออกหน้าของไฟล์นี้ไม่ได้'],

  // ---- text recognition
  '中文': ['Chinese', 'จีน'],
  '英文': ['English', 'อังกฤษ'],
  '泰文': ['Thai', 'ไทย'],
  '生成可搜索 PDF': ['Searchable PDF', 'PDF ที่ค้นหาได้'],
  '导出文字（TXT）': ['Text (TXT)', 'ข้อความ (TXT)'],
  '没有选择页面时，识别全部页面': ['With no pages selected, every page is read', 'ถ้าไม่ได้เลือกหน้า จะอ่านทุกหน้า'],
  '开始识别': ['Start', 'เริ่มอ่าน'],
  '请至少选择一种语言': ['Choose at least one language', 'เลือกอย่างน้อยหนึ่งภาษา'],
  '正在识别第 {i} / {n} 页': ['Reading page {i} of {n}', 'กำลังอ่านหน้า {i} จาก {n}'],
  '停止': ['Stop', 'หยุด'],
  '正在加载文字识别': ['Loading text recognition', 'กำลังโหลดการอ่านข้อความ'],
  '第一次识别需要几秒钟。': ['The first time takes a few seconds.', 'ครั้งแรกใช้เวลาสักครู่'],
  '—— 第 {n} 页 ——': ['—— Page {n} ——', '—— หน้า {n} ——'],
  '_可搜索': ['_searchable', '_ค้นหาได้'],
  '_文字': ['_text', '_ข้อความ'],
  '识别完成': ['Done', 'อ่านเสร็จแล้ว'],
  '已识别 {n} 页。': ['{n} pages read.', 'อ่านแล้ว {n} หน้า'],
  '识别没有完成': ["Text recognition didn't finish", 'อ่านข้อความไม่สำเร็จ'],
  '新功能：文字识别（OCR）': ['New: text recognition (OCR)', 'ใหม่: อ่านข้อความ (OCR)'],
  '把扫描版 PDF 变成能搜索、能复制文字的 PDF，或导出文字。支持简体中文、英文和泰文。\n需要下载约 17 MB；只在识别时加载，不影响打开速度。': [
    'Turns scanned PDFs into PDFs whose text can be searched and copied, or exports the text. Reads Simplified Chinese, English and Thai.\nA download of about 17 MB, loaded only while reading, so opening files stays fast.',
    'เปลี่ยน PDF ที่สแกนให้ค้นหาและคัดลอกข้อความได้ หรือส่งออกเป็นข้อความ รองรับภาษาจีนตัวย่อ อังกฤษ และไทย\nต้องดาวน์โหลดประมาณ 17 MB และโหลดเฉพาะตอนอ่านข้อความ จึงไม่ทำให้เปิดไฟล์ช้าลง'],
  '不用了': ['No thanks', 'ไม่เป็นไร'],
  '正在下载文字识别组件': ['Downloading text recognition', 'กำลังดาวน์โหลดการอ่านข้อความ'],
  '文字识别已安装': ['Text recognition is installed', 'ติดตั้งการอ่านข้อความแล้ว'],
  '左边多了「文字识别」，打开扫描版 PDF 后就能用。': ['“Text recognition” is now on the left. Open a scanned PDF to use it.', 'มีเมนู “อ่านข้อความ (OCR)” ทางซ้ายแล้ว เปิด PDF ที่สแกนเพื่อใช้งาน'],
  '文字识别没有装好': ["Text recognition wasn't installed", 'ติดตั้งการอ่านข้อความไม่สำเร็จ'],
  '以后再说': ['Later', 'ไว้ทีหลัง'],
  '重试': ['Retry', 'ลองอีกครั้ง'],
  '移除文字识别？需要时可以重新安装。': ['Remove text recognition? You can install it again any time.', 'นำการอ่านข้อความออกหรือไม่? ติดตั้งใหม่ได้ทุกเมื่อ'],

  // ---- merge & split
  '文档': ['Documents', 'เอกสาร'],
  '添加文件': ['Add files', 'เพิ่มไฟล์'],
  '添加正在查看的文件': ['Add the file being viewed', 'เพิ่มไฟล์ที่กำลังดู'],
  '放到这里，拆分成新文档': ['Drop here to split into a new document', 'วางที่นี่เพื่อแยกเป็นเอกสารใหม่'],
  '保存在原文档所在的文件夹': ["Saved in the original document's folder", 'บันทึกในโฟลเดอร์เดียวกับเอกสารต้นฉบับ'],
  'Ctrl 或 Shift 点选多页': ['Ctrl or Shift + click selects several pages', 'กด Ctrl หรือ Shift ค้างแล้วคลิกเพื่อเลือกหลายหน้า'],
  '选中的页面拖到这一栏，拆分成新文档': ['Drag selected pages here to split them into a new document', 'ลากหน้าที่เลือกมาที่แถบนี้เพื่อแยกเป็นเอกสารใหม่'],
  'Delete 删除所选，Ctrl+Z 撤销': ['Delete removes the selection, Ctrl+Z undoes', 'Delete ลบหน้าที่เลือก, Ctrl+Z เลิกทำ'],
  '双击页面放大查看': ['Double-click a page to see it large', 'ดับเบิลคลิกที่หน้าเพื่อดูขนาดใหญ่'],
  '撤销': ['Undo', 'เลิกทำ'],
  '全部展开': ['Expand all', 'ขยายทั้งหมด'],
  '全部收起': ['Collapse all', 'ยุบทั้งหมด'],
  '向左旋转': ['Rotate left', 'หมุนซ้าย'],
  '向右旋转': ['Rotate right', 'หมุนขวา'],
  '删除所选': ['Delete selected', 'ลบที่เลือก'],
  '缩略图': ['Thumbnails', 'ภาพย่อ'],
  '把 PDF 拖到这里': ['Drag PDFs here', 'ลากไฟล์ PDF มาที่นี่'],
  '每份文档先叠成一摞，展开后可以删除、旋转、拖动单页，再合并成一个文件；': ['Each document arrives as a stack. Expand it to delete, rotate or drag single pages, then merge everything into one file;', 'เอกสารแต่ละไฟล์จะซ้อนเป็นตั้ง ขยายออกเพื่อลบ หมุน หรือลากทีละหน้า แล้วรวมเป็นไฟล์เดียว'],
  '选中页面拖到左边的文档栏，就拆分成一份新文档': ['drag selected pages onto the document list on the left to split them into a new document', 'ลากหน้าที่เลือกไปที่รายการเอกสารทางซ้ายเพื่อแยกเป็นเอกสารใหม่'],
  '也可以': ['or', 'หรือ'],
  '选择文件': ['choose files', 'เลือกไฟล์'],
  '0 页': ['0 pages', '0 หน้า'],
  '文件名': ['File name', 'ชื่อไฟล์'],
  '仅导出所选': ['Export selected', 'ส่งออกที่เลือก'],
  '合并并下载': ['Merge and save', 'รวมและบันทึก'],
  '合并结果': ['Merged', 'ไฟล์รวม'],
  '删除此页': ['Delete this page', 'ลบหน้านี้'],
  '关闭': ['Close', 'ปิด'],
  '未命名': ['Untitled', 'ไม่มีชื่อ'],
  '正在载入 {n} 个文件…': ['Loading {n} files…', 'กำลังโหลด {n} ไฟล์…'],
  '「{name}」无法读取': ['“{name}” can’t be read', 'อ่าน “{name}” ไม่ได้'],
  '；': ['; ', ' ; '],
  '只能添加 PDF 文件': ['Only PDF files can be added', 'เพิ่มได้เฉพาะไฟล์ PDF'],
  '第 {n} 页': ['Page {n}', 'หน้า {n}'],
  '第{n}页': ['Page {n}', 'หน้า {n}'],
  '把「{name}」的所有页面收起叠在一起': ['Stack all pages of “{name}” together', 'ยุบทุกหน้าของ “{name}” รวมเป็นตั้ง'],
  '收起': ['Collapse', 'ยุบ'],
  '展开': ['Expand', 'ขยาย'],
  '整份向左旋转': ['Rotate the document left', 'หมุนทั้งเอกสารไปทางซ้าย'],
  '整份向右旋转': ['Rotate the document right', 'หมุนทั้งเอกสารไปทางขวา'],
  '移除这份文档': ['Remove this document', 'นำเอกสารนี้ออก'],
  '{n} 页': ['{n} pages', '{n} หน้า'],
  '展开 {n} 页': ['Expand {n} pages', 'ขยาย {n} หน้า'],
  '点击选中这份文档的全部页面；拖到右侧可整份移动': ['Click to select all its pages; drag it to the right to move the whole document', 'คลิกเพื่อเลือกทุกหน้าของเอกสารนี้ ลากไปทางขวาเพื่อย้ายทั้งเอกสาร'],
  '移除这份文档的全部页面': ['Remove all pages of this document', 'นำทุกหน้าของเอกสารนี้ออก'],
  '共 {n} 页，{d} 份文档': ['{n} pages, {d} documents', 'ทั้งหมด {n} หน้า {d} เอกสาร'],
  '移动 {n} 页': ['Move {n} pages', 'ย้าย {n} หน้า'],
  '第 {i} / {n} 页': ['Page {i} of {n}', 'หน้า {i} จาก {n}'],
  '正在生成 PDF…': ['Creating the PDF…', 'กำลังสร้าง PDF…'],
  '已导出 {n} 页（{size}）': ['Exported {n} pages ({size})', 'ส่งออกแล้ว {n} หน้า ({size})'],
  '导出失败：': ['Export failed: ', 'ส่งออกไม่สำเร็จ: '],
  '不用拆分': ['Nothing to split', 'ไม่ต้องแยก'],
  '选中的就是「{name}」的全部页面。': ['The selection is every page of “{name}”.', 'หน้าที่เลือกคือทุกหน้าของ “{name}” อยู่แล้ว'],
  '正在拆分…': ['Splitting…', 'กำลังแยก…'],
  '拆分没有完成': ["Splitting didn't finish", 'แยกไม่สำเร็จ'],
  '已拆分出「{name}」，共 {n} 页': ['Split off “{name}”, {n} pages', 'แยกเป็น “{name}” แล้ว {n} หน้า'],
  '已拆分出「{name}」': ['Split off “{name}”', 'แยกเป็น “{name}” แล้ว'],
  '新文档共 {n} 页，已保存在原文档所在的文件夹。': ["The new document has {n} pages and is saved in the original document's folder.", 'เอกสารใหม่มี {n} หน้า บันทึกไว้ในโฟลเดอร์เดียวกับเอกสารต้นฉบับแล้ว'],
  '原文档{names}里的这 {n} 页，要删除还是保留？': ['Delete these {n} pages from the original {names}, or keep them?', 'จะลบ {n} หน้านี้ออกจากเอกสารต้นฉบับ {names} หรือเก็บไว้?'],
  '删除：原文件只留下其余的页面。保留：原文件不变。': ['Delete: the original file keeps only its other pages. Keep: the original file stays as it is.', 'ลบ: ไฟล์ต้นฉบับจะเหลือเฉพาะหน้าอื่น  เก็บไว้: ไฟล์ต้นฉบับไม่เปลี่ยนแปลง'],
  '删除后，原文档不再有密码保护。': ['After deleting, the original is no longer password-protected.', 'หลังจากลบ เอกสารต้นฉบับจะไม่มีรหัสผ่านอีกต่อไป'],
  '删除这 {n} 页': ['Delete these {n} pages', 'ลบ {n} หน้านี้'],
  '保留': ['Keep', 'เก็บไว้'],
  '「{name}」': ['“{name}”', '“{name}”'],
  '正在从原文档删除这些页…': ['Deleting the pages from the original…', 'กำลังลบหน้าเหล่านี้ออกจากเอกสารต้นฉบับ…'],
  '「{name}」：{msg}': ['“{name}”: {msg}', '“{name}”: {msg}'],
  '原文档没有改动': ["The original wasn't changed", 'เอกสารต้นฉบับไม่ได้เปลี่ยนแปลง'],
  '已拆分出「{name}」，并从原文档删除了这 {n} 页': ['Split off “{name}” and deleted the {n} pages from the original', 'แยกเป็น “{name}” และลบ {n} หน้าออกจากต้นฉบับแล้ว'],

  // ---- right-click menus
  '取消选择此页': ['Deselect this page', 'ยกเลิกการเลือกหน้านี้'],
  '选择此页': ['Select this page', 'เลือกหน้านี้'],
  '只选择此页': ['Select only this page', 'เลือกเฉพาะหน้านี้'],
  '把第 {n} 页导出为 PDF': ['Export page {n} as PDF', 'ส่งออกหน้า {n} เป็น PDF'],
  '把第 {n} 页导出为图片': ['Export page {n} as an image', 'ส่งออกหน้า {n} เป็นรูปภาพ'],
  '转到此页': ['Go to this page', 'ไปที่หน้านี้'],
  '打印第 {n} 页': ['Print page {n}', 'พิมพ์หน้า {n}'],
  '打印…': ['Print…', 'พิมพ์…'],
  '加入合并拆分': ['Add to Merge & split', 'เพิ่มไปที่รวมและแยก'],
  '展开「{name}」': ['Expand “{name}”', 'ขยาย “{name}”'],
  '收起「{name}」': ['Collapse “{name}”', 'ยุบ “{name}”'],
  '预览': ['Preview', 'ดูตัวอย่าง'],
  '只导出这份文档': ['Export only this document', 'ส่งออกเฉพาะเอกสารนี้'],
  '打印这份文档': ['Print this document', 'พิมพ์เอกสารนี้'],
  '选中它的全部页面': ['Select all its pages', 'เลือกทุกหน้าของเอกสารนี้'],
  '向左旋转此页': ['Rotate this page left', 'หมุนหน้านี้ไปทางซ้าย'],
  '向左旋转所选 {n} 页': ['Rotate the {n} selected pages left', 'หมุน {n} หน้าที่เลือกไปทางซ้าย'],
  '向右旋转此页': ['Rotate this page right', 'หมุนหน้านี้ไปทางขวา'],
  '向右旋转所选 {n} 页': ['Rotate the {n} selected pages right', 'หมุน {n} หน้าที่เลือกไปทางขวา'],
  '只导出此页': ['Export only this page', 'ส่งออกเฉพาะหน้านี้'],
  '只导出所选 {n} 页': ['Export only the {n} selected pages', 'ส่งออกเฉพาะ {n} หน้าที่เลือก'],
  '把此页拆分成新文档': ['Split this page into a new document', 'แยกหน้านี้เป็นเอกสารใหม่'],
  '把所选 {n} 页拆分成新文档': ['Split the {n} selected pages into a new document', 'แยก {n} หน้าที่เลือกเป็นเอกสารใหม่'],
  '打印此页': ['Print this page', 'พิมพ์หน้านี้'],
  '打印所选 {n} 页': ['Print the {n} selected pages', 'พิมพ์ {n} หน้าที่เลือก'],
  '删除所选 {n} 页': ['Delete the {n} selected pages', 'ลบ {n} หน้าที่เลือก'],

  // ---- images to PDF
  '贴合图片尺寸': ['Same as the image', 'เท่ากับขนาดรูปภาพ'],
  'A4 竖向（图片居中缩放）': ['A4 portrait (image centred)', 'A4 แนวตั้ง (รูปอยู่กึ่งกลาง)'],
  'A4 横向（图片居中缩放）': ['A4 landscape (image centred)', 'A4 แนวนอน (รูปอยู่กึ่งกลาง)'],

  // ---- printing
  '打印范围': ['Pages to print', 'ช่วงที่จะพิมพ์'],
  '全部': ['All', 'ทั้งหมด'],
  '自定义': ['Custom', 'กำหนดเอง'],
  '（{n} 页）': ['({n} pages)', '({n} หน้า)'],
  '所选页面（{n} 页）': ['Selected pages ({n})', 'หน้าที่เลือก ({n} หน้า)'],
  '所选页面（未选择）': ['Selected pages (none)', 'หน้าที่เลือก (ยังไม่ได้เลือก)'],
  '当前页（第 {n} 页）': ['Current page (page {n})', 'หน้าปัจจุบัน (หน้า {n})'],
  '清晰度': ['Quality', 'ความคมชัด'],
  '标准 150 dpi（文件大时更快）': ['Standard 150 dpi (faster for big files)', 'มาตรฐาน 150 dpi (เร็วกว่าสำหรับไฟล์ใหญ่)'],
  '清晰 200 dpi': ['Sharp 200 dpi', 'คมชัด 200 dpi'],
  '高清 300 dpi（小字、图纸）': ['High 300 dpi (small print, drawings)', 'ละเอียด 300 dpi (ตัวอักษรเล็ก แบบแปลน)'],
  '横向页面自动旋转，铺满纸张': ['Turn landscape pages to fill the paper', 'หมุนหน้าแนวนอนให้เต็มกระดาษอัตโนมัติ'],
  '打印机、纸张大小、份数和双面打印，在下一步的系统打印窗口里选择。': ['Printer, paper size, copies and two-sided printing are chosen in the Windows print window that follows.', 'เลือกเครื่องพิมพ์ ขนาดกระดาษ จำนวนชุด และการพิมพ์สองหน้าได้ในหน้าต่างพิมพ์ของ Windows ขั้นถัดไป'],
  '请输入有效的页码，例如 1-3,5': ['Enter valid page numbers, e.g. 1-3,5', 'ใส่เลขหน้าที่ถูกต้อง เช่น 1-3,5'],
  '正在准备第 {i} / {n} 页…': ['Preparing page {i} of {n}…', 'กำลังเตรียมหน้า {i} จาก {n}…'],
  '正在打开打印窗口…': ['Opening the print window…', 'กำลังเปิดหน้าต่างพิมพ์…'],
  '打印失败：': ['Printing failed: ', 'พิมพ์ไม่สำเร็จ: '],

  // ---- 合并打印 (Explorer's right-click menu)
  '合并打印 {n} 个文件': ['Merge and print: {n} files', 'รวมแล้วพิมพ์ {n} ไฟล์'],
  '有 {n} 个文件没有打印': ["{n} files weren't printed", 'มี {n} ไฟล์ที่ไม่ได้พิมพ์'],
  '这些文件打不开，或者没有输入密码：': ["These files couldn't be opened, or their password wasn't given:", 'ไฟล์เหล่านี้เปิดไม่ได้ หรือไม่ได้ใส่รหัสผ่าน:'],

  // ---- updates
  '立即更新': ['Update now', 'อัปเดตเลย'],
  '发现新版本 {v}': ['New version {v}', 'มีเวอร์ชันใหม่ {v}'],
  '正在下载新版本 {v}': ['Downloading version {v}', 'กำลังดาวน์โหลดเวอร์ชัน {v}'],
  '正在安装新版本 {v}': ['Installing version {v}', 'กำลังติดตั้งเวอร์ชัน {v}'],
  '更新没有完成': ["The update didn't finish", 'อัปเดตไม่สำเร็จ'],
  '请在 Windows 弹出的确认窗口里点「是」。程序会自动关闭，装好后重新打开。': ['Click “Yes” in the window Windows shows. The program closes, and opens again once the update is installed.', 'คลิก “ใช่” ในหน้าต่างยืนยันของ Windows โปรแกรมจะปิดเองและเปิดใหม่เมื่อติดตั้งเสร็จ'],
};

// A text in the chosen language; {name} in it is replaced by vars.name.
function t(zh, vars) {
  const tr = TEXTS[zh];
  let text = LANG === 'zh' || !tr ? zh : tr[LANG === 'en' ? 0 : 1];
  if (vars) text = text.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? vars[k] : m));
  if (LANG === 'en' && vars) {                     // one page, not "1 pages"
    text = text.replace(/\bthese 1 pages\b/g, 'this page').replace(/\bthe 1 selected pages\b/g, 'the selected page')
      .replace(/(^|[^\d.,])1 (page|document|file|image)s\b/g, (m, before, word) => `${before}1 ${word}`);
  }
  return text;
}

// The page's own markup: every text and title / placeholder / aria-label written in Chinese is noted once,
// then shown in the chosen language, and again whenever it changes. Parts marked data-no-i18n stay as written.
const markupTexts = new Map(), markupAttrs = new Map();
const HAN = /[一-鿿]/;
function noteMarkup() {
  const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n; (n = walk.nextNode());) {
    if (HAN.test(n.nodeValue) && !n.parentElement.closest('script, style, [data-no-i18n]')) markupTexts.set(n, n.nodeValue);
  }
  for (const el of document.body.querySelectorAll('[title], [placeholder], [aria-label]')) {
    if (el.closest('[data-no-i18n]')) continue;
    const zh = {};
    for (const a of ['title', 'placeholder', 'aria-label']) if (HAN.test(el.getAttribute(a) || '')) zh[a] = el.getAttribute(a);
    if (Object.keys(zh).length) markupAttrs.set(el, zh);
  }
}
function translateMarkup() {
  if (!markupTexts.size) noteMarkup();
  for (const [node, zh] of markupTexts) {
    const [, lead, core, trail] = zh.match(/^(\s*)([\s\S]*?)(\s*)$/);
    node.nodeValue = lead + t(core) + trail;
  }
  for (const [el, zh] of markupAttrs) for (const a in zh) el.setAttribute(a, t(zh[a]));
  document.documentElement.lang = { zh: 'zh-CN', en: 'en', th: 'th' }[LANG];
  document.documentElement.classList.remove('i18n-pending');
}
