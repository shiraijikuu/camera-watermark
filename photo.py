# -*- coding: utf-8 -*-
"""photo.py - 相机照片水印核心逻辑（不依赖 GUI，可独立测试）"""
import os
import struct
from PIL import Image, ImageDraw, ImageFont, ImageOps
from lang import tr
import piexif

# ---------------- 支持的文件类型 ----------------
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
RAW_EXTS = {'.arw', '.srf', '.sr2', '.nef', '.nrw', '.cr2', '.cr3', '.dng',
            '.orf', '.rw2', '.pef', '.raf', '.srw', '.3fr', '.erf', '.mrw',
            '.kdc', '.dcr', '.raw', '.iiq', '.x3f'}

def ext_of(name):
    return os.path.splitext(name)[1].lower()

def is_raw_name(name):
    return ext_of(name) in RAW_EXTS

def is_image_name(name):
    return ext_of(name) in IMAGE_EXTS

def is_supported_name(name):
    return is_image_name(name) or is_raw_name(name)

# ---------------- RAW 内嵌 JPEG 提取 ----------------

def _u16(data, off, le):
    return struct.unpack_from('<H' if le else '>H', data, off)[0]

def _u32(data, off, le):
    return struct.unpack_from('<I' if le else '>I', data, off)[0]

MAX_IFD_COUNT = 2000

def _tiff_preview(data):
    """TIFF 结构解析：支持 SubIFDs（n=1 直接偏移 / n>1 偏移数组）、
    Compression=6 的 strips、以及 0x0201/0x0202 JPEGInterchangeFormat。"""
    if len(data) < 8:
        return None
    le = data[0] == 0x49 and data[1] == 0x49
    be = data[0] == 0x4D and data[1] == 0x4D
    if not (le or be):
        return None
    try:
        if _u16(data, 2, le) != 42:
            return None
    except Exception:
        return None

    candidates = []
    visited = set()
    queue = [_u32(data, 4, le)]

    def parse_ifd(start):
        if start < 8 or start + 2 > len(data) or start in visited:
            return
        visited.add(start)
        count = _u16(data, start, le)
        if count <= 0 or count > MAX_IFD_COUNT:
            return
        if start + 2 + count * 12 > len(data):
            return
        sub = []
        comp = 0
        offsets = []
        counts = []
        jpeg_ptr = None
        jpeg_len = None
        for i in range(count):
            e = start + 2 + i * 12
            tag = _u16(data, e, le)
            typ = _u16(data, e + 2, le)
            n = _u32(data, e + 4, le)
            vo = e + 8
            if tag == 0x014A:  # SubIFDs
                if n == 1:
                    sub.append(_u32(data, vo, le) if typ == 4 else _u16(data, vo, le))
                elif typ == 4:
                    arr = _u32(data, vo, le)
                    for j in range(min(n, MAX_IFD_COUNT)):
                        pp = arr + j * 4
                        if pp + 4 <= len(data):
                            sub.append(_u32(data, pp, le))
            elif tag == 0x0103:  # Compression
                if typ == 3 and n == 1:
                    comp = _u16(data, vo, le)
                elif typ == 4 and n == 1:
                    comp = _u32(data, vo, le)
                else:
                    comp = data[vo]
            elif tag == 0x0111:  # StripOffsets
                if n == 1:
                    offsets.append(_u32(data, vo, le) if typ == 4 else _u16(data, vo, le))
                elif typ == 4:
                    arr = _u32(data, vo, le)
                    for j in range(min(n, 100000)):
                        pp = arr + j * 4
                        if pp + 4 <= len(data):
                            offsets.append(_u32(data, pp, le))
            elif tag == 0x0117:  # StripByteCounts
                if n == 1:
                    counts.append(_u32(data, vo, le) if typ == 4 else _u16(data, vo, le))
                elif typ == 4:
                    arr = _u32(data, vo, le)
                    for j in range(min(n, 100000)):
                        pp = arr + j * 4
                        if pp + 4 <= len(data):
                            counts.append(_u32(data, pp, le))
            elif tag == 0x0201:  # JPEGInterchangeFormat
                jpeg_ptr = _u32(data, vo, le) if typ == 4 else _u16(data, vo, le)
            elif tag == 0x0202:  # JPEGInterchangeFormatLength
                jpeg_len = _u32(data, vo, le) if typ == 4 else _u16(data, vo, le)
        for off in sub:
            parse_ifd(off)
        if comp == 6 and offsets and counts:
            candidates.append((offsets[:], counts[:], sum(counts), start))
        if jpeg_ptr is not None and jpeg_len:
            candidates.append(([jpeg_ptr], [jpeg_len], jpeg_len, start))
        nxt = _u32(data, start + 2 + count * 12, le)
        if nxt:
            queue.append(nxt)

    while queue:
        parse_ifd(queue.pop(0))

    candidates.sort(key=lambda c: -c[2])
    for offs, cnts, total, start in candidates:
        if total < 128 or total > len(data):
            continue
        parts = []
        ok = True
        for o, c in zip(offs, cnts):
            if o < 8 or o + c > len(data):
                ok = False
                break
            parts.append(data[o:o + c])
        if not ok:
            continue
        jpg = b''.join(parts)
        if len(jpg) > 4 and jpg[0] == 0xFF and jpg[1] == 0xD8:
            return jpg
    return None

def _scan_jpeg_blob(data):
    """快速扫描最大的连续 JPEG 块（C 级 find）。覆盖 ARW 独立预览、CR3/RAF 等容器。"""
    best = None
    pos = 0
    n = len(data)
    while True:
        s = data.find(b'\xff\xd8', pos)
        if s < 0 or s + 4 >= n:
            break
        e = data.find(b'\xff\xd9', s + 2)
        if e < 0:
            break
        length = e - s + 2
        if best is None or length > best[1]:
            best = (s, length)
        pos = e + 2
    if best and best[1] >= 128:
        return data[best[0]:best[0] + best[1]]
    return None

def extract_embedded_jpeg(data):
    """从 RAW 中提取全尺寸内嵌 JPEG 预览：先按 TIFF 结构解析，失败则快速扫描最大 JPEG 块。"""
    if data is None or len(data) < 8:
        return None
    jpg = _tiff_preview(data)
    if jpg:
        return jpg
    return _scan_jpeg_blob(data)

# ---------------- EXIF 方向转换 ----------------
_ORIENT_METHODS = {
    2: Image.FLIP_LEFT_RIGHT,
    3: Image.ROTATE_180,
    4: Image.FLIP_TOP_BOTTOM,
    5: Image.TRANSPOSE,
    6: Image.ROTATE_270,
    7: Image.TRANSVERSE,
    8: Image.ROTATE_90,
}

def apply_orientation(img, orientation):
    """按 EXIF Orientation(1-8) 把图片转正。orientation 为空或 1 时原样返回。"""
    try:
        orientation = int(orientation)
    except (TypeError, ValueError):
        return img
    method = _ORIENT_METHODS.get(orientation)
    if method is None:
        return img
    return img.transpose(method)


# ---------------- 格式化 ----------------
def _trim_num(n, decimals=2):
    if n is None:
        return ''
    try:
        n = float(n)
    except (TypeError, ValueError):
        return ''
    if n <= 0:
        return ''
    return ('%.*f' % (decimals, n)).rstrip('0').rstrip('.')

def format_shutter(t):
    if t is None:
        return ''
    try:
        t = float(t)
    except (TypeError, ValueError):
        return ''
    if t <= 0:
        return ''
    if t >= 1:
        return _trim_num(t) + 's'
    inv = 1.0 / t
    rounded = round(inv)
    if abs(rounded - inv) / inv < 0.05:
        return '1/%ds' % rounded
    return _trim_num(t) + 's'

def format_aperture(f):
    if f is None:
        return ''
    try:
        f = float(f)
    except (TypeError, ValueError):
        return ''
    if f <= 0:
        return ''
    return 'F' + _trim_num(f)

def format_iso(iso):
    if iso is None:
        return ''
    try:
        iso = float(iso)
    except (TypeError, ValueError):
        return ''
    if iso <= 0:
        return ''
    return 'ISO %d' % round(iso)

def format_focal(mm):
    if mm is None:
        return ''
    try:
        mm = float(mm)
    except (TypeError, ValueError):
        return ''
    if mm <= 0:
        return ''
    return _trim_num(mm) + 'mm'

MAKE_MAP = {
    'SONY': 'Sony',
    'NIKON CORPORATION': 'Nikon',
    'NIKON': 'Nikon',
    'CANON': 'Canon',
    'FUJIFILM': 'Fujifilm',
    'PANASONIC': 'Panasonic',
    'OLYMPUS IMAGING CORP.': 'Olympus',
    'OLYMPUS': 'Olympus',
    'OM Digital Solutions': 'OM System',
    'PENTAX': 'Pentax',
    'RICOH': 'Ricoh',
    'RICOH IMAGING COMPANY, LTD.': 'Ricoh',
    'LEICA': 'Leica',
    'HASSELBLAD': 'Hasselblad',
    'APPLE': 'Apple',
    'GOOGLE': 'Google',
    'SAMSUNG': 'Samsung',
    'HUAWEI': 'Huawei',
    'XIAOMI': 'Xiaomi',
    'HONOR': 'Honor',
    'ONEPLUS': 'OnePlus',
    'OPPO': 'OPPO',
    'VIVO': 'vivo',
    'DJI': 'DJI',
    'Canon': 'Canon',
}

SONY_MODEL_MAP = {
    'ILCE-7CM2': 'A7C II', 'ILCE-7CM3': 'A7C III', 'ILCE-7C': 'A7C',
    'ILCE-7CR': 'A7CR', 'ILCE-1': 'Alpha 1', 'ILCE-9M3': 'A9 III',
    'ILCE-9M2': 'A9 II', 'ILCE-9': 'A9', 'ILCE-7RM5': 'A7R V',
    'ILCE-7RM4A': 'A7R IV', 'ILCE-7RM4': 'A7R IV', 'ILCE-7RM3': 'A7R III',
    'ILCE-7RM2': 'A7R II', 'ILCE-7RM': 'A7R', 'ILCE-7M4': 'A7 IV',
    'ILCE-7M3': 'A7 III', 'ILCE-7M2': 'A7 II', 'ILCE-7': 'A7',
    'ILCE-7SM3': 'A7S III', 'ILCE-7SM2': 'A7S II', 'ILCE-7S': 'A7S',
    'ILCE-6700': 'A6700', 'ILCE-6600': 'A6600', 'ILCE-6500': 'A6500',
    'ILCE-6400': 'A6400', 'ILCE-6300': 'A6300', 'ILCE-6100': 'A6100',
    'ILCE-6000': 'A6000', 'ILCE-5100': 'A5100', 'ILCE-5000': 'A5000',
    'DSC-RX100M7': 'RX100 VII', 'DSC-RX100M6': 'RX100 VI', 'DSC-RX100M5A': 'RX100 V',
    'DSC-RX100M5': 'RX100 V', 'DSC-RX100M4': 'RX100 IV', 'DSC-RX100M3': 'RX100 III',
    'DSC-RX100M2': 'RX100 II', 'DSC-RX100': 'RX100', 'DSC-RX10M4': 'RX10 IV',
    'DSC-RX1RM2': 'RX1R II', 'ZV-E10II': 'ZV-E10 II', 'ZV-E10': 'ZV-E10',
    'ZV-E1': 'ZV-E1', 'ZV-1F': 'ZV-1F', 'ZV-1': 'ZV-1',
}

def friendly_camera_name(make, model):
    m = (make or '').strip()
    mo = (model or '').strip()
    clean_make = MAKE_MAP.get(m.upper()) or MAKE_MAP.get(m) or m
    if m.upper() == 'SONY' and mo in SONY_MODEL_MAP:
        return 'Sony ' + SONY_MODEL_MAP[mo]
    if mo:
        return (clean_make + ' ' + mo) if clean_make else mo
    return clean_make

def format_datetime(s):
    """EXIF 时间字符串 'YYYY:MM:DD HH:MM:SS' -> (date, time)"""
    if not s:
        return '', ''
    try:
        if isinstance(s, bytes):
            s = s.decode('utf-8', 'ignore')
        s = s.strip()
        if ' ' in s:
            d, t = s.split(' ', 1)
            return d.replace(':', '-'), t[:5]
        return s.replace(':', '-'), ''
    except Exception:
        return '', ''

def render_template(template, values):
    import re
    if not template:
        return ''
    def repl(m):
        key = m.group(1)
        v = values.get(key)
        return '' if v is None else str(v)
    out = re.sub(r'\{([a-zA-Z]+)\}', repl, template)
    lines = [l.rstrip() for l in out.split('\n')]
    # 保留中间空行（用户用空行控制行间排版间距）；去掉首尾空行
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not any(l.strip() for l in lines):
        return ''
    return '\n'.join(lines)

# ---------------- 元数据读取 ----------------
def _get_exif_value(exif_ifd, tag, default=None):
    v = exif_ifd.get(tag, default)
    if v is None:
        return default
    if isinstance(v, bytes):
        try:
            return v.decode('utf-8', 'ignore').strip()
        except Exception:
            return default
    return v

def read_meta(path):
    """读取照片元数据。JPG/PNG/WebP/BMP 用 Pillow；RAW 用 piexif 解析 + 内嵌预览尺寸。"""
    name = os.path.basename(path)
    raw = is_raw_name(name)
    meta = {
        'path': path, 'name': name, 'ext': ext_of(name), 'raw': raw,
        'size': os.path.getsize(path) if os.path.exists(path) else 0,
        'width': 0, 'height': 0, 'orientation': 1, 'has_preview': True,
        'make': '', 'model': '', 'software': '', 'lens': '',
        'focal': 0.0, 'exposure_time': 0.0, 'f_number': 0.0, 'iso': 0,
        'date_time': '', 'camera_text': '', 'shutter_text': '', 'aperture_text': '',
        'iso_text': '', 'focal_text': '', 'lens_text': '', 'date_text': '', 'time_text': '',
        'error': '',
    }
    try:
        if raw:
            with open(path, 'rb') as f:
                buf = f.read()
            jpg = extract_embedded_jpeg(buf)
            if jpg:
                try:
                    with Image.open(__import__('io').BytesIO(jpg)) as im:
                        meta['width'], meta['height'] = im.size
                except Exception:
                    meta['has_preview'] = False
            else:
                meta['has_preview'] = False
            try:
                d = piexif.load(path)
            except Exception:
                d = {}
            z = d.get('0th', {}) or {}
            e = d.get('Exif', {}) or {}
        else:
            with Image.open(path) as im:
                meta['width'], meta['height'] = im.size
                ex = im.getexif()
                z = dict(ex)
                try:
                    e = dict(ex.get_ifd(0x8769))
                except Exception:
                    e = {}
                if meta['width'] == 0 and z.get(0x100):
                    meta['width'] = z[0x100]
                if meta['height'] == 0 and z.get(0x101):
                    meta['height'] = z[0x101]

        make = _get_exif_value(z, 271, '')
        model = _get_exif_value(z, 272, '')
        orientation = z.get(274, 1)
        try:
            orientation = int(orientation)
        except Exception:
            orientation = 1
        lens = _get_exif_value(e, 42036, '')
        focal = _get_exif_value(e, 37386, 0.0)
        fnum = _get_exif_value(e, 33437, 0.0)
        exp = _get_exif_value(e, 33434, 0.0)
        iso = _get_exif_value(e, 34855, 0)
        dt = _get_exif_value(e, 36867, '') or _get_exif_value(z, 306, '')

        def to_float(v):
            try:
                if isinstance(v, tuple) and len(v) == 2 and v[1]:
                    return float(v[0]) / float(v[1])
                return float(v)
            except Exception:
                return 0.0

        focal = to_float(focal)
        fnum = to_float(fnum)
        exp = to_float(exp)
        try:
            iso = int(iso)
        except Exception:
            iso = 0

        w, h = meta['width'], meta['height']
        if w and h and orientation >= 5:
            w, h = h, w

        meta['make'] = make
        meta['model'] = model
        meta['software'] = _get_exif_value(z, 305, '')
        meta['lens'] = lens
        meta['focal'] = focal
        meta['f_number'] = fnum
        meta['exposure_time'] = exp
        meta['iso'] = iso
        meta['orientation'] = orientation
        meta['width'] = w
        meta['height'] = h
        meta['date_time'] = dt
        meta['camera_text'] = friendly_camera_name(make, model)
        meta['shutter_text'] = format_shutter(exp)
        meta['aperture_text'] = format_aperture(fnum)
        meta['iso_text'] = format_iso(iso)
        meta['focal_text'] = format_focal(focal)
        meta['lens_text'] = lens
        if dt:
            meta['date_text'], meta['time_text'] = format_datetime(dt)
    except Exception as ex:
        meta['error'] = str(ex)
    return meta

def values_for(meta, settings):
    cam = (settings.get('camera_override') or '').strip() or (meta or {}).get('camera_text', '')
    return {
        'camera': cam,
        'make': (meta or {}).get('make', ''),
        'model': (meta or {}).get('model', ''),
        'shutter': (meta or {}).get('shutter_text', ''),
        'aperture': (meta or {}).get('aperture_text', ''),
        'iso': (meta or {}).get('iso_text', ''),
        'focal': (meta or {}).get('focal_text', ''),
        'lens': (meta or {}).get('lens_text', ''),
        'date': (meta or {}).get('date_text', ''),
        'time': (meta or {}).get('time_text', ''),
    }

# ---------------- 字体 ----------------
FONT_CANDIDATES = [
    ('微软雅黑', [r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\msyhl.ttc']),
    ('微软雅黑 粗体', [r'C:\Windows\Fonts\msyhbd.ttc', r'C:\Windows\Fonts\msyh.ttc']),
    ('等线', [r'C:\Windows\Fonts\Deng.ttf', r'C:\Windows\Fonts\Dengb.ttf']),
    ('宋体', [r'C:\Windows\Fonts\simsun.ttc']),
    ('黑体', [r'C:\Windows\Fonts\simhei.ttf']),
    ('楷体', [r'C:\Windows\Fonts\simkai.ttf']),
    ('仿宋', [r'C:\Windows\Fonts\simfang.ttf']),
    ('Arial', [r'C:\Windows\Fonts\arial.ttf']),
    ('Consolas', [r'C:\Windows\Fonts\consola.ttf']),
    ('Times New Roman', [r'C:\Windows\Fonts\times.ttf']),
]

CUSTOM_FONT_EXTS = ('.ttf', '.otf', '.ttc')

def _scan_custom_fonts(fonts_dir):
    """扫描自定义字体目录（fonts/，含子文件夹），返回 [(显示名, 路径)]"""
    out = []
    if fonts_dir and os.path.isdir(fonts_dir):
        try:
            for root, dirs, files in os.walk(fonts_dir):
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for fn in sorted(files):
                    if fn.startswith('.'):
                        continue
                    ext = os.path.splitext(fn)[1].lower()
                    if ext in CUSTOM_FONT_EXTS:
                        out.append((tr('自定义: ') + os.path.splitext(fn)[0], os.path.join(root, fn)))
        except Exception:
            pass
    return out

def available_fonts(fonts_dir=None):
    fonts = []
    for name, paths in FONT_CANDIDATES:
        for p in paths:
            if os.path.exists(p):
                fonts.append((name, p))
                break
    fonts.extend(_scan_custom_fonts(fonts_dir))
    return fonts

def _font_candidates(family, fonts_dir=None):
    """按优先级产出字体候选路径（只产出已存在的），支持跨平台回退。"""
    seen = set()
    for name, p in available_fonts(fonts_dir):
        if name == family and p not in seen:
            seen.add(p)
            yield p
    for p in (r'C:\Windows\Fonts\msyh.ttc',
              r'C:\Windows\Fonts\arial.ttf',
              '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
              '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
              '/System/Library/Fonts/Helvetica.ttc'):
        if p not in seen and os.path.exists(p):
            seen.add(p)
            yield p


def resolve_font(family, fonts_dir=None):
    for p in _font_candidates(family, fonts_dir):
        return p
    return None

# ---------------- 水印渲染 ----------------
def _watermark_layout(img, settings, values, fonts_dir=None, full_size=None):
    """计算水印布局：返回 (bx, by, inner_w, inner_h, font, lines, line_h, padding, fs)。
    与 render_watermark 共用，保证拖拽换算与最终渲染一致。无文本/字体时返回 None。
    full_size 指定时，布局以全图尺寸为基准（用于裁剪预览图中定位水印）。"""
    W, H = full_size if full_size else img.size
    text = render_template(settings.get('template', ''), values)
    if not text:
        return None
    lines = text.split('\n')
    fs = max(8, int(W * settings.get('font_size_pct', 2.2) / 100))
    font = None
    for p in _font_candidates(settings.get('font_family', '微软雅黑'), fonts_dir):
        try:
            font = ImageFont.truetype(p, fs)
            break
        except Exception:
            continue
    if font is None:
        try:
            font = ImageFont.load_default()
        except Exception:
            return None
    ascent, descent = font.getmetrics()
    line_h = int((ascent + descent) * (1 + settings.get('line_spacing', 0.35)))
    ws = float(settings.get('word_spacing', 0.0))     # 参数间距（×字号），0=仅模板空格
    spacing_px = int(fs * ws) if ws > 0 else 0
    widths = []
    for l in lines:
        if spacing_px > 0:
            # 按 token 拆分：相邻参数间额外拉开 spacing_px
            toks = [t for t in l.split() if t]
            if len(toks) > 1:
                w = sum(max(0, font.getbbox(t)[2] - font.getbbox(t)[0]) for t in toks)
                w += spacing_px * (len(toks) - 1)
            else:
                b = font.getbbox(l)
                w = max(0, b[2] - b[0])
        else:
            b = font.getbbox(l)
            w = max(0, b[2] - b[0])
        widths.append(w)
    block_w = max(widths) if widths else 0
    block_h = line_h * len(lines)
    padding = int(fs * settings.get('bg_padding', 0.6))
    inner_w = max(1, block_w + padding * 2)
    inner_h = max(1, block_h + padding * 2)
    ax = settings.get('anchor', 7) % 3
    ay = settings.get('anchor', 7) // 3
    margin_x = W * settings.get('margin_pct', 3.0) / 100
    margin_y = H * settings.get('margin_pct', 3.0) / 100
    if ax == 0:
        bx = margin_x
    elif ax == 1:
        bx = (W - inner_w) / 2
    else:
        bx = W - margin_x - inner_w
    if ay == 0:
        by = margin_y
    elif ay == 1:
        by = (H - inner_h) / 2
    else:
        by = H - margin_y - inner_h
    bx += W * settings.get('offset_x_pct', 0.0) / 100
    by += H * settings.get('offset_y_pct', 0.0) / 100
    bx = max(-inner_w + 2, min(W - 2, bx))
    by = max(-inner_h + 2, min(H - 2, by))
    return (int(round(bx)), int(round(by)), int(round(inner_w)), int(round(inner_h)),
            font, lines, line_h, padding, fs)


def watermark_rect(img, settings, values, fonts_dir=None):
    """返回水印矩形 (x0, y0, x1, y1)（图像坐标）；无文本/字体返回 None。"""
    r = _watermark_layout(img, settings, values, fonts_dir)
    if r is None:
        return None
    bx, by, inner_w, inner_h = r[:4]
    return (bx, by, bx + inner_w, by + inner_h)



def _hex_to_rgb(h, default=(255, 255, 255)):
    try:
        h = h.lstrip('#')
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    except Exception:
        return default

# -*- coding: utf-8 -*-
def render_watermark(img, settings, values, fonts_dir=None, full_size=None, origin=(0, 0)):
    """在 img（PIL RGB）上绘制水印，返回新图。
    full_size=None 时 img 即全图（现状）；full_size 指定时为"裁剪预览图"，
    origin 是 img 左上角在全图中的坐标——水印按全图布局，只绘制与 img 有交集的区域，
    使放大预览中水印位置与全图一致。只处理水印区域，速度与图片总像素无关。"""
    img = img.convert('RGB')
    r = _watermark_layout(img, settings, values, fonts_dir, full_size=full_size)
    if r is None:
        return img
    bx, by, inner_w, inner_h, font, lines, line_h, padding, fs = r
    W, H = img.size

    # 水印矩形在本图坐标（全图坐标 - 窗口偏移）
    lx = bx - origin[0]
    ly = by - origin[1]
    cx0, cy0 = max(0, lx), max(0, ly)
    cx1, cy1 = min(W, lx + inner_w), min(H, ly + inner_h)
    if cx1 <= cx0 or cy1 <= cy0:
        return img   # 水印完全在可视区外，无需绘制

    # 只处理交集区域；水印矩形左上角相对交集区域的位置 (dx, dy)
    dx = lx - cx0
    dy = ly - cy0
    patch = img.crop((cx0, cy0, cx1, cy1)).convert('RGBA')
    layer = Image.new('RGBA', patch.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(layer)

    if settings.get('bg_enabled') and settings.get('bg_opacity', 0) > 0:
        rr, gg, bb = _hex_to_rgb(settings.get('bg_color', '#000000'), (0, 0, 0))
        aa = int(255 * float(settings.get('bg_opacity', 0.45)))
        radius = max(0, int(fs * 0.25))
        od.rounded_rectangle([dx, dy, dx + inner_w, dy + inner_h], radius=radius, fill=(rr, gg, bb, aa))

    rr, gg, bb = _hex_to_rgb(settings.get('text_color', '#ffffff'), (255, 255, 255))
    alpha = int(255 * float(settings.get('text_opacity', 1.0)))
    tx = padding + dx
    ty = padding + dy

    # 参数间距（×字号）：>0 时按 token 拆分绘制，相邻参数间额外拉开
    _ws = float(settings.get('word_spacing', 0.0))
    _spacing_px = int(fs * _ws) if _ws > 0 else 0

    def _draw_line(od, txt, x, y, fill, stroke_w=0, stroke_fill=None):
        if _spacing_px > 0:
            toks = [t for t in txt.split() if t]
            xx = x
            for t in toks:
                od.text((xx, y), t, font=font, fill=fill,
                        stroke_width=stroke_w, stroke_fill=stroke_fill)
                xx += (font.getbbox(t)[2] - font.getbbox(t)[0]) + _spacing_px
        else:
            od.text((x, y), txt, font=font, fill=fill,
                    stroke_width=stroke_w, stroke_fill=stroke_fill)

    if settings.get('shadow_enabled'):
        blur = max(1, int(fs * float(settings.get('shadow_blur', 0.15))))
        for li, l in enumerate(lines):
            _draw_line(od, l, tx + blur // 2, ty + li * line_h + blur // 2,
                       (0, 0, 0, alpha))

    stroke_w = 0
    stroke_fill = None
    if settings.get('outline_enabled'):
        stroke_w = max(1, int(fs * float(settings.get('outline_width', 0.06))))
        stroke_fill = _hex_to_rgb(settings.get('outline_color', '#000000'), (0, 0, 0))

    for li, l in enumerate(lines):
        _draw_line(od, l, tx, ty + li * line_h, (rr, gg, bb, alpha),
                   stroke_w=stroke_w, stroke_fill=stroke_fill)

    patch = Image.alpha_composite(patch, layer).convert('RGB')
    img.paste(patch, (cx0, cy0))
    return img

# ---------------- EXIF 回写 ----------------
def build_exif_bytes(meta, orig_path, width, height):
    """构造导出 JPG 的 EXIF。优先从原图读取，缺失字段用解析出的元数据补齐。"""
    try:
        d = piexif.load(orig_path)
    except Exception:
        d = {}
    if not isinstance(d, dict):
        d = {}
    d.setdefault('0th', {})
    d.setdefault('Exif', {})
    d.setdefault('GPS', {})
    d.setdefault('Interop', {})
    d['0th'][piexif.ImageIFD.Orientation] = 1
    d['Exif'][piexif.ExifIFD.PixelXDimension] = int(width)
    d['Exif'][piexif.ExifIFD.PixelYDimension] = int(height)
    d['thumbnail'] = None

    def ensure_0th(tag, val):
        if val and not d['0th'].get(tag):
            d['0th'][tag] = str(val).encode('utf-8')

    def ensure_exif_ascii(tag, val):
        if val and not d['Exif'].get(tag):
            d['Exif'][tag] = str(val).encode('utf-8')

    def ensure_exif(tag, val):
        if val and not d['Exif'].get(tag):
            d['Exif'][tag] = val

    if meta:
        ensure_0th(piexif.ImageIFD.Make, meta.get('make'))
        ensure_0th(piexif.ImageIFD.Model, meta.get('model'))
        ensure_0th(piexif.ImageIFD.Software, meta.get('software'))
        if meta.get('lens'):
            ensure_exif_ascii(piexif.ExifIFD.LensModel, meta.get('lens'))
        if meta.get('f_number'):
            f = float(meta['f_number'])
            ensure_exif(piexif.ExifIFD.FNumber, (int(round(f * 100)), 100))
        if meta.get('exposure_time'):
            t = float(meta['exposure_time'])
            ensure_exif(piexif.ExifIFD.ExposureTime, (int(round(t * 1000000)), 1000000))
        if meta.get('iso'):
            ensure_exif(piexif.ExifIFD.ISOSpeedRatings, int(meta['iso']))
        if meta.get('focal'):
            fl = float(meta['focal'])
            ensure_exif(piexif.ExifIFD.FocalLength, (int(round(fl * 100)), 100))
        if meta.get('date_time'):
            s = meta['date_time']
            if isinstance(s, bytes):
                s = s.decode('utf-8', 'ignore')
            d['0th'][piexif.ImageIFD.DateTime] = s
            d['Exif'][piexif.ExifIFD.DateTimeOriginal] = s
            d['Exif'][piexif.ExifIFD.DateTimeDigitized] = s
    return piexif.dump(d)

# ---------------- 保存 ----------------
FORMAT_MIME = {
    'jpg': ('JPEG', '.jpg'),
    'png': ('PNG', '.png'),
    'webp': ('WEBP', '.webp'),
    'bmp': ('BMP', '.bmp'),
}

def save_watermarked(src_path, target_path, img, fmt, quality, meta=None, preserve_exif=False):
    """把已经画好水印的 img 保存到 target_path。fmt: jpg/png/webp/bmp"""
    if fmt == 'jpg':
        kw = {'quality': int(quality)}
        if preserve_exif:
            try:
                exif_bytes = build_exif_bytes(meta, src_path, img.width, img.height)
                kw['exif'] = exif_bytes
            except Exception:
                pass
        img.save(target_path, 'JPEG', **kw)
    elif fmt == 'png':
        img.save(target_path, 'PNG')
    elif fmt == 'webp':
        img.save(target_path, 'WEBP', quality=int(quality))
    elif fmt == 'bmp':
        img.save(target_path, 'BMP')
    else:
        raise ValueError('unsupported format: ' + fmt)
# -*- coding: utf-8 -*-
"""默认设置（GUI 与命令行共用）"""
DEFAULT_SETTINGS = {
    'template': '{make}  {model}   {focal}  {shutter}  {aperture}  {iso}',
    'custom_template': '',
    'update_url': 'https://cdn.jsdelivr.net/gh/shiraijikuu/camera-watermark@main/update.json',
    'plugin_store_url': 'https://cdn.jsdelivr.net/gh/shiraijikuu/camera-watermark@main/plugins.json',
    'language': 'zh',
    'style': 'default',
    'plugin_values': {},
    'camera_override': '',
    'font_family': '微软雅黑',
    'font_size_pct': 2.2,
    'bold': False,
    'text_color': '#ffffff',
    'text_opacity': 1.0,
    'line_spacing': 0.35,
    'word_spacing': 0.0,
    'anchor': 7,
    'offset_x_pct': 0.0,
    'offset_y_pct': 0.0,
    'margin_pct': 0.5,
    'bg_enabled': True,
    'bg_color': '#000000',
    'bg_opacity': 0.45,
    'bg_padding': 0.6,
    'outline_enabled': False,
    'outline_color': '#000000',
    'outline_width': 0.06,
    'shadow_enabled': False,
    'shadow_blur': 0.15,
    'format': 'jpg',
    'jpeg_quality': 95,
    'preserve_exif': True,
    'suffix': '_wm',
    'overwrite': False,
}
