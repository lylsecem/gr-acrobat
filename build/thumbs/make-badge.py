# Turns badge-preview.png into src/badge.h for thumbs.c. The picture holds the GR Acrobat mark that thumbnails carry in
# their bottom left corner (a teal rounded square with a white page, inside a white rim so it shows on dark pages
# too), drawn at each size it is used at: SIZES below, left to right, GAP pixels apart, along the top edge. Each size
# is drawn by hand for its pixel grid rather than scaled at run time, so the small ones stay crisp.
# Run it after changing the picture: python3 build/thumbs/make-badge.py
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
SIZES = [9, 12, 16, 20, 24, 32, 40, 48, 64, 96, 128, 192]
GAP = 8
# The thumbnail size (Explorer's cx) from which each size is used: about 5¼ times the mark. Below 45 there is none.
FROM = [45, 61, 82, 103, 124, 166, 208, 250, 335, 503, 672, 1008]

im = Image.open(HERE / 'badge-preview.png').convert('RGBA')
assert im.size == (sum(SIZES) + GAP * (len(SIZES) - 1), max(SIZES)), im.size
data, offsets, x = bytearray(), [], 0
for size in SIZES:
    offsets.append(len(data))
    px = im.crop((x, 0, x + size, size)).tobytes()
    for i in range(0, len(px), 4):
        r, g, b, a = px[i:i + 4]
        data += bytes((c * a + 127) // 255 for c in (b, g, r)) + bytes([a])   # BGRA, premultiplied
    x += size + GAP
rows = [', '.join(f'0x{v:02x}' for v in data[i:i + 24]) for i in range(0, len(data), 24)]
join = lambda values: ', '.join(map(str, values))
(HERE / 'src' / 'badge.h').write_text(
    '// The GR Acrobat mark for thumbnails, made by build/thumbs/make-badge.py from badge-preview.png: do not edit.\n'
    '// BADGE_COUNT sizes; size i is BADGE_SIZES[i] square, used from thumbnail size BADGE_FROM[i] on, its pixels at\n'
    '// BADGE + BADGE_OFFSET[i]: BGRA, colours premultiplied by alpha.\n'
    f'#define BADGE_COUNT {len(SIZES)}\n'
    f'static const int BADGE_SIZES[BADGE_COUNT] = {{ {join(SIZES)} }};\n'
    f'static const int BADGE_FROM[BADGE_COUNT] = {{ {join(FROM)} }};\n'
    f'static const int BADGE_OFFSET[BADGE_COUNT] = {{ {join(offsets)} }};\n'
    f'static const unsigned char BADGE[{len(data)}] = {{\n  ' + ',\n  '.join(rows) + '\n};\n',
    encoding='ascii', newline='\n')
print('src/badge.h:', len(SIZES), 'sizes,', len(data), 'bytes')
