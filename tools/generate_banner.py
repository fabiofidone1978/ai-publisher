"""
Genera il banner 1280x720 per il canale Telegram AI Prompt Lab.
"""
from PIL import Image, ImageDraw, ImageFont
import os

W, H = 1280, 720
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "telegram_banner.png")

# Palette ispirata a fabiofidone.it: dark + accento cyan
BG_TOP    = (10, 14, 26)
BG_BOTTOM = (18, 24, 48)
ACCENT    = (0, 200, 180)
WHITE     = (255, 255, 255)
LIGHT     = (180, 190, 210)
DIM       = (80, 95, 130)

def get_font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/segoeui.ttf"    if not bold else "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/calibri.ttf"    if not bold else "C:/Windows/Fonts/calibrib.ttf",
        "C:/Windows/Fonts/arial.ttf"      if not bold else "C:/Windows/Fonts/arialbd.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

def draw_gradient(draw, w, h):
    for y in range(h):
        t = y / h
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

def centered_text(draw, text, y, font, color):
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (W - (bbox[2] - bbox[0])) // 2
    draw.text((x, y), text, font=font, fill=color)
    return bbox[3] - bbox[1]

img  = Image.new("RGB", (W, H))
draw = ImageDraw.Draw(img)

# Sfondo gradiente
draw_gradient(draw, W, H)

# Griglia di punti decorativi
for gx in range(60, W, 80):
    for gy in range(60, H, 80):
        draw.ellipse([gx-1, gy-1, gx+1, gy+1], fill=DIM)

# Linea accent sinistra verticale
draw.rectangle([72, 160, 76, 560], fill=ACCENT)

# Etichetta canale in alto
f_tag = get_font(22)
draw.text((100, 168), "CANALE TELEGRAM", font=f_tag, fill=ACCENT)

# Titolo principale
f_title = get_font(110, bold=True)
draw.text((100, 210), "AI", font=f_title, fill=WHITE)
bbox_ai = draw.textbbox((100, 210), "AI", font=f_title)
draw.text((bbox_ai[2] + 18, 210), "Prompt", font=f_title, fill=ACCENT)
bbox_prompt = draw.textbbox((bbox_ai[2] + 18, 210), "Prompt", font=f_title)
draw.text((100, 330), "Lab", font=f_title, fill=WHITE)

# Sottotitolo
f_sub = get_font(32)
draw.text((100, 470), "Prompt, idee e strumenti per l'intelligenza artificiale", font=f_sub, fill=LIGHT)

# Separatore
draw.rectangle([100, 530, 700, 532], fill=DIM)

# Footer
f_footer = get_font(26)
draw.text((100, 548), "by Fabio Fidone", font=f_footer, fill=LIGHT)
f_url = get_font(24)
draw.text((100, 584), "fabiofidone.it", font=f_url, fill=ACCENT)

# Decorazione angolo destra — cerchi concentrici
cx, cy = 1100, 360
for r, alpha in [(180, 15), (140, 25), (100, 40), (60, 60), (28, 90)]:
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.ellipse([cx-r, cy-r, cx+r, cy+r], outline=(*ACCENT, alpha), width=1)
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay)
    img = img.convert("RGB")
    draw = ImageDraw.Draw(img)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
img.save(OUT, "PNG")
print(f"Banner salvato: {OUT}")
