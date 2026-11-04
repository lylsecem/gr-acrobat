# Makes the test files in tests/.fixtures/ (and only there: the folder is emptied first). Run by tests/run.py when
# they are missing, or by hand: python3 tests/make_fixtures.py
#   doc1.pdf          10 text pages, "DOC1 PAGE n" under a blue band
#   doc2.pdf          3 text pages, "DOC2 PAGE n" under a green band
#   broken.pdf        the first 600 bytes of doc1.pdf;  notpdf.pdf  text with a .pdf name
#   landscape.pdf     2 landscape pages
#   scan_*.pdf        pictures of printed Chinese, English and Thai text, for text recognition (one stored turned,
#                     one with its page box away from 0,0)
#   pw/               the same 3 pages with different protections (password 1234 unless noted), see protected()
#   locked.pdf        a copy of pw/pw_aes256.pdf
#   img/              pictures: photo.jpg, diagram.png (transparent), small.gif, pic.bmp, pic.webp, bad.png (not one)
# Needs Pillow, reportlab, pypdf, pikepdf, and a Chinese and a Thai font (fonts-wqy-zenhei, fonts-noto-cjk,
# fonts-thai-tlwg on Debian / Ubuntu; Windows has its own).
import os, random, shutil, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import pikepdf
from pypdf import PdfWriter, Transformation
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

OUT = Path(__file__).resolve().parent / '.fixtures'
assert OUT.name == '.fixtures' and OUT.parent.name == 'tests'      # the only folder this script empties


def font_file(*names, lang=None):
    """The first of these font files found; failing that (lang given), any font fontconfig says covers that language."""
    roots = ['/usr/share/fonts', '/usr/local/share/fonts', os.path.expanduser('~/.fonts'), 'C:/Windows/Fonts']
    for name in names:
        for root in roots:
            for dirpath, _, files in os.walk(root):
                if name in files:
                    return os.path.join(dirpath, name)
    if lang and shutil.which('fc-list'):             # Linux font packages name their files differently over time
        listed = subprocess.run(['fc-list', f':lang={lang}', 'file'], capture_output=True, text=True).stdout
        found = sorted(l.strip().rstrip(':') for l in listed.splitlines() if l.strip().rstrip(':').endswith(('.ttf', '.otf')))
        if found:
            return found[0]
    raise SystemExit(f'font not found: {names}')


CJK_TTF = font_file('wqy-zenhei.ttc', 'simsun.ttc')                    # TrueType outlines, for reportlab
CJK = font_file('msyh.ttc', 'wqy-zenhei.ttc', 'NotoSansCJK-Regular.ttc')   # Chinese shapes (Noto's first face is the Japanese one)
THAI = font_file('Loma.otf', 'Loma.ttf', 'NotoSansThai-Regular.ttf', 'LeelawUI.ttf', 'tahoma.ttf', lang='th')
SANS = font_file('DejaVuSans.ttf', 'arial.ttf')
pdfmetrics.registerFont(TTFont('CJK', CJK_TTF, subfontIndex=0))


def text_pdf(path, label, n, band, size=A4):
    c = canvas.Canvas(str(path), pagesize=size)
    w, h = size
    for i in range(1, n + 1):
        c.setFillColor(HexColor(band))
        c.rect(0, h - 90, w, 90, stroke=0, fill=1)
        c.setFillColor(HexColor('#111111'))
        c.setFont('Helvetica-Bold', 40)
        c.drawString(60, h - 200, f'{label} PAGE {i}')
        c.setFont('Helvetica', 14)
        for k in range(30):                          # body lines, so the page is not empty below
            c.drawString(60, h - 260 - k * 18, f'{label} line {k + 1} of page {i}.')
        c.showPage()
    c.save()


def scan_page(lines, font, size=(1240, 1754)):
    """A page as a scanner would give it: black print on a slightly grey sheet, 150 dpi."""
    im = Image.new('RGB', size, (246, 246, 244))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(font, 64)
    y = 200
    for line in lines:
        d.text((120, y), line, font=f, fill=(20, 20, 20))
        y += 130
    return im


def save_images(images, path):
    images[0].save(path, save_all=True, append_images=images[1:], resolution=150)


def scans(out):
    zh = scan_page(['文字识别测试', '扫描版文件', '龙禹良制作'], CJK)
    en = scan_page(['Text recognition test', 'Scanned document', 'Hello world'], SANS)
    th = scan_page(['ทดสอบการอ่านข้อความ', 'เอกสารสแกน'], THAI)
    save_images([zh, en], out / 'scan_zh_en.pdf')
    save_images([th], out / 'scan_th.pdf')
    # stored sideways and shown upright by /Rotate 90, as some scanners save pages
    save_images([zh.rotate(90, expand=True)], out / 'rot_tmp.pdf')
    w = PdfWriter(clone_from=str(out / 'rot_tmp.pdf')); w.pages[0].rotate(90); w.write(str(out / 'scan_rot.pdf'))
    (out / 'rot_tmp.pdf').unlink()
    # the page box starts at (100, 100), not (0, 0): text laid over the page has to follow it
    w = PdfWriter(clone_from=str(out / 'scan_zh_en.pdf'))
    for page in w.pages:
        page.add_transformation(Transformation().translate(100, 100))
        x0, y0, x1, y1 = [float(v) for v in page.mediabox]
        page.mediabox.lower_left = (x0 + 100, y0 + 100)
        page.mediabox.upper_right = (x1 + 100, y1 + 100)
    w.write(str(out / 'scan_offset.pdf'))


def protected(out):
    pw = out / 'pw'
    pw.mkdir()
    plain = pw / 'plain.pdf'
    c = canvas.Canvas(str(plain), pagesize=A4)
    for i in range(1, 4):
        c.setFont('CJK', 36)
        c.drawString(60, 700, f'密码保护测试 {i}')
        c.setFont('Helvetica', 18)
        c.drawString(60, 640, f'PROTECTED PAGE {i}')
        c.showPage()
    c.save()

    def encrypt(src, dst, user='1234', owner='own', R=6, aes=True, allow=None):
        enc = pikepdf.Encryption(user=user, owner=owner, R=R, allow=allow or pikepdf.Permissions(),
                                 metadata=R >= 4, aes=aes if R == 4 else R >= 5)
        with pikepdf.open(src) as pdf:
            pdf.save(dst, encryption=enc, object_stream_mode=pikepdf.ObjectStreamMode.generate if R >= 4 else pikepdf.ObjectStreamMode.disable)

    encrypt(plain, pw / 'pw_rc4_40.pdf', R=2)
    encrypt(plain, pw / 'pw_rc4_128.pdf', R=3)
    encrypt(plain, pw / 'pw_aes128.pdf', R=4)
    encrypt(plain, pw / 'pw_aes256.pdf')
    encrypt(plain, pw / 'pw_utf8.pdf', user='密码ไทย1')
    encrypt(plain, pw / 'pw_owner_only.pdf', user='', owner='owner',
            allow=pikepdf.Permissions(print_lowres=False, print_highres=False, extract=False))
    # over 8 MB, so the program reads it in pieces: the 3 pages, then pages of noise that do not compress
    rnd = random.Random(7)
    noise = [Image.frombytes('RGB', (1400, 1400), rnd.randbytes(1400 * 1400 * 3)) for _ in range(5)]
    noise[0].save(pw / 'noise.pdf', save_all=True, append_images=noise[1:], resolution=150, quality=95)
    w = PdfWriter(clone_from=str(plain))
    w.append(str(pw / 'noise.pdf'))
    w.write(str(pw / 'big_src.pdf'))
    encrypt(pw / 'big_src.pdf', pw / 'pw_big.pdf')
    (pw / 'noise.pdf').unlink()
    (pw / 'big_src.pdf').unlink()
    assert (pw / 'pw_big.pdf').stat().st_size > 8 * 1024 * 1024, 'pw_big.pdf must be over 8 MB'


def pictures(out):
    img = out / 'img'
    img.mkdir()
    # a photo: smooth colours (JPEG), 1200 × 800
    photo = Image.new('RGB', (1200, 800))
    px = photo.load()
    for y in range(800):
        for x in range(0, 1200):
            px[x, y] = (x * 255 // 1200, y * 255 // 800, 160)
    d = ImageDraw.Draw(photo)
    d.ellipse((450, 250, 750, 550), fill=(250, 220, 40))
    d.text((60, 60), 'PHOTO', font=ImageFont.truetype(SANS, 90), fill=(255, 255, 255))
    photo.save(img / 'photo.jpg', quality=92)
    # a diagram: sharp lines on a transparent background (PNG), 640 × 480
    dia = Image.new('RGBA', (640, 480), (0, 0, 0, 0))
    d = ImageDraw.Draw(dia)
    d.rectangle((40, 40, 600, 440), outline=(200, 30, 30, 255), width=8)
    d.line((40, 40, 600, 440), fill=(30, 30, 200, 255), width=6)
    d.text((240, 200), 'PNG', font=ImageFont.truetype(SANS, 72), fill=(0, 0, 0, 255))
    dia.save(img / 'diagram.png')
    small = Image.new('RGB', (120, 90), (40, 160, 90))
    small.save(img / 'small.gif')
    small.save(img / 'pic.bmp')
    small.save(img / 'pic.webp')
    (img / 'bad.png').write_bytes(b'not a picture\n' * 20)


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    text_pdf(OUT / 'doc1.pdf', 'DOC1', 10, '#1f5fbf')
    text_pdf(OUT / 'doc2.pdf', 'DOC2', 3, '#1f9f5f')
    (OUT / 'broken.pdf').write_bytes((OUT / 'doc1.pdf').read_bytes()[:600])
    (OUT / 'notpdf.pdf').write_text('This is not a PDF.\n' * 20)
    text_pdf(OUT / 'landscape.pdf', 'LANDSCAPE', 2, '#bf5f1f', landscape(A4))
    scans(OUT)
    protected(OUT)
    shutil.copy(OUT / 'pw' / 'pw_aes256.pdf', OUT / 'locked.pdf')
    pictures(OUT)
    for p in sorted(OUT.rglob('*.*')):
        print(f'{p.relative_to(OUT)}  {p.stat().st_size:,} bytes')


if __name__ == '__main__':
    main()
