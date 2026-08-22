"""
生成 TabBar 图标的脚本
使用 Python 生成简单的 PNG 图标
"""
import struct
import zlib
import os

OUTPUT_DIR = r"d:\ANDRIOD\天商便捷助手\app\static\tab"

def create_png(width, height, rgba_data):
    """Create a minimal PNG from RGBA pixel data"""
    def chunk(chunk_type, data):
        c = chunk_type + data
        crc = struct.pack('>I', zlib.crc32(c) & 0xffffffff)
        return struct.pack('>I', len(data)) + c + crc
    
    # PNG signature
    sig = b'\x89PNG\r\n\x1a\n'
    
    # IHDR
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)  # 8bit RGBA
    
    # IDAT - raw pixel rows with filter byte
    raw = b''
    for y in range(height):
        raw += b'\x00'  # filter: none
        for x in range(width):
            idx = (y * width + x) * 4
            raw += bytes(rgba_data[idx:idx+4])
    
    compressed = zlib.compress(raw)
    
    return sig + chunk(b'IHDR', ihdr) + chunk(b'IDAT', compressed) + chunk(b'IEND', b'')


def draw_circle(pixels, w, h, cx, cy, r, color):
    """Draw filled circle"""
    for y in range(h):
        for x in range(w):
            if (x - cx)**2 + (y - cy)**2 <= r**2:
                idx = (y * w + x) * 4
                pixels[idx:idx+4] = color


def draw_rect(pixels, w, h, x1, y1, x2, y2, color):
    """Draw filled rectangle"""
    for y in range(max(0, y1), min(h, y2)):
        for x in range(max(0, x1), min(w, x2)):
            idx = (y * w + x) * 4
            pixels[idx:idx+4] = color


def draw_line_h(pixels, w, h, x1, x2, y, thickness, color):
    """Draw horizontal line"""
    draw_rect(pixels, w, h, x1, y, x2, y + thickness, color)


def draw_line_v(pixels, w, h, x, y1, y2, thickness, color):
    """Draw vertical line"""
    draw_rect(pixels, w, h, x, y1, x + thickness, y2, color)


def create_home_icon(active=False):
    """Home icon - simple house shape"""
    s = 48
    p = bytearray(s * s * 4)
    c = [91, 115, 232, 255] if active else [138, 138, 154, 255]
    
    # Roof (triangle approximation)
    for y in range(8, 24):
        half = (y - 8) * 12 // 16
        x1 = 24 - half
        x2 = 24 + half
        draw_rect(p, s, s, x1, y, x2, y+1, c)
    
    # Body
    draw_rect(p, s, s, 12, 24, 36, 40, c)
    # Door
    dc = [15, 15, 35, 255] if active else [15, 15, 35, 255]
    draw_rect(p, s, s, 20, 30, 28, 40, dc)
    
    return create_png(s, s, p)


def create_signin_icon(active=False):
    """Signin icon - checkmark in circle"""
    s = 48
    p = bytearray(s * s * 4)
    c = [91, 115, 232, 255] if active else [138, 138, 154, 255]
    
    # Circle outline
    for y in range(s):
        for x in range(s):
            dist = ((x - 24)**2 + (y - 24)**2) ** 0.5
            if 18 <= dist <= 21:
                idx = (y * s + x) * 4
                p[idx:idx+4] = c
    
    # Checkmark
    for i in range(8):
        draw_rect(p, s, s, 14+i, 22+i, 16+i, 24+i, c)
    for i in range(14):
        draw_rect(p, s, s, 22+i, 30-i, 24+i, 32-i, c)
    
    return create_png(s, s, p)


def create_quiz_icon(active=False):
    """Quiz icon - document with lines"""
    s = 48
    p = bytearray(s * s * 4)
    c = [91, 115, 232, 255] if active else [138, 138, 154, 255]
    
    # Document body
    draw_rect(p, s, s, 10, 6, 38, 42, c)
    # Inner white area
    inner = [15, 15, 35, 255]
    draw_rect(p, s, s, 13, 9, 35, 39, inner)
    # Lines
    draw_line_h(p, s, s, 16, 32, 15, 2, c)
    draw_line_h(p, s, s, 16, 32, 22, 2, c)
    draw_line_h(p, s, s, 16, 28, 29, 2, c)
    
    return create_png(s, s, p)


def create_settings_icon(active=False):
    """Settings icon - gear shape (simplified)"""
    s = 48
    p = bytearray(s * s * 4)
    c = [91, 115, 232, 255] if active else [138, 138, 154, 255]
    
    # Outer circle
    for y in range(s):
        for x in range(s):
            dist = ((x - 24)**2 + (y - 24)**2) ** 0.5
            if 16 <= dist <= 20:
                idx = (y * s + x) * 4
                p[idx:idx+4] = c
    
    # Inner circle
    for y in range(s):
        for x in range(s):
            dist = ((x - 24)**2 + (y - 24)**2) ** 0.5
            if dist <= 8:
                idx = (y * s + x) * 4
                p[idx:idx+4] = c
    
    # Clear inner
    inner = [15, 15, 35, 255]
    for y in range(s):
        for x in range(s):
            dist = ((x - 24)**2 + (y - 24)**2) ** 0.5
            if dist <= 5:
                idx = (y * s + x) * 4
                p[idx:idx+4] = inner
    
    # Gear teeth (4 directions)
    draw_rect(p, s, s, 22, 2, 26, 8, c)   # top
    draw_rect(p, s, s, 22, 40, 26, 46, c)  # bottom
    draw_rect(p, s, s, 2, 22, 8, 26, c)    # left
    draw_rect(p, s, s, 40, 22, 46, 26, c)  # right
    
    return create_png(s, s, p)


os.makedirs(OUTPUT_DIR, exist_ok=True)

icons = {
    'home': create_home_icon,
    'signin': create_signin_icon,
    'quiz': create_quiz_icon,
    'settings': create_settings_icon,
}

for name, func in icons.items():
    # Normal
    with open(os.path.join(OUTPUT_DIR, f'{name}.png'), 'wb') as f:
        f.write(func(active=False))
    # Active
    with open(os.path.join(OUTPUT_DIR, f'{name}_active.png'), 'wb') as f:
        f.write(func(active=True))

print(f"Generated {len(icons) * 2} icons in {OUTPUT_DIR}")

# Also create a simple logo
logo_dir = r"d:\ANDRIOD\天商便捷助手\app\static"
s = 128
p = bytearray(s * s * 4)

# Blue gradient circle
for y in range(s):
    for x in range(s):
        dist = ((x - 64)**2 + (y - 64)**2) ** 0.5
        if dist <= 56:
            ratio = y / s
            r = int(91 * (1 - ratio) + 108 * ratio)
            g = int(115 * (1 - ratio) + 92 * ratio)
            b = int(232 * (1 - ratio) + 231 * ratio)
            idx = (y * s + x) * 4
            p[idx:idx+4] = [r, g, b, 255]

# Letter "T" in center
tc = [255, 255, 255, 255]
draw_rect(p, s, s, 34, 36, 94, 44, tc)  # top bar
draw_rect(p, s, s, 58, 44, 70, 92, tc)  # vertical bar

with open(os.path.join(logo_dir, 'logo.png'), 'wb') as f:
    f.write(create_png(s, s, p))

# Default avatar
s = 64
p = bytearray(s * s * 4)
bg = [60, 60, 80, 255]
draw_circle(p, s, s, 32, 32, 30, bg)
head = [120, 120, 150, 255]
draw_circle(p, s, s, 32, 24, 10, head)
draw_circle(p, s, s, 32, 50, 16, head)

with open(os.path.join(logo_dir, 'avatar_default.png'), 'wb') as f:
    f.write(create_png(s, s, p))

print("Generated logo.png and avatar_default.png")
