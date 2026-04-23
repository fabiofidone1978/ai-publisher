"""
Genera il banner promo 1280x720 per PromoFinder.it (mostrato su AI Prompt Lab).
"""
from PIL import Image, ImageDraw, ImageFont
import os

W, H = 1280, 720
OUT  = os.path.join(os.path.dirname(__file__), "..", "data", "banner_promo_promofinder.png")

BG_TOP    = (10, 14, 26)
BG_BOTTOM = (20, 18, 40)
ACCENT    = (255, 140, 0)      # arancione PromoFinder
ACCENT2   = (255, 200, 50)     # giallo dorato
WHITE     = (255, 255, 255)
LIGHT     = (200, 195, 220)
DIM       = (70, 65, 100)

def get_font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/segoeui.ttf"  if not bold else "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/calibri.ttf"  if not bold else "C:/Windows/Fonts/calibrib.ttf",
        "C:/Windows/Fonts/arial.ttf"    if not bold else "C:/Windows/Fonts/arialbd.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

img  = Image.new("RGB", (W, H))
draw = ImageDraw.Draw(img)

# Sfondo gradiente
for y in range(H):
    t = y / H
    r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
    g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
    b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
    draw.line([(0, y), (W, y)], fill=(r, g, b))

# Griglia punti
for gx in range(60, W, 80):
    for gy in range(60, H, 80):
        draw.ellipse([gx-1, gy-1, gx+1, gy+1], fill=DIM)

# Linea accent arancione
draw.rectangle([72, 160, 76, 560], fill=ACCENT)

# Etichetta
f_tag = get_font(22)
draw.text((100, 168), "CANALE TELEGRAM", font=f_tag, fill=ACCENT)

# Titolo
f_big = get_font(96, bold=True)
draw.text((100, 215), "Promo", font=f_big, fill=ACCENT)
bbox = draw.textbbox((100, 215), "Promo", font=f_big)
draw.text((bbox[2] + 14, 215), "Finder", font=f_big, fill=ACCENT2)
draw.text((100, 335), ".it", font=get_font(80, bold=True), fill=WHITE)

# Sottotitolo
f_sub = get_font(32)
draw.text((100, 468), "Codici sconto, offerte e cashback ogni giorno", font=f_sub, fill=LIGHT)

# Separatore
draw.rectangle([100, 528, 700, 530], fill=DIM)

# Footer
draw.text((100, 546), "by Fabio Fidone", font=get_font(26), fill=LIGHT)
draw.text((100, 582), "promofinder.it", font=get_font(24), fill=ACCENT)

# Cerchi decorativi destra
cx, cy = 1090, 360
for r, alpha in [(180,12),(140,20),(100,35),(60,55),(28,85)]:
    overlay = Image.new("RGBA", (W, H), (0,0,0,0))
    od = ImageDraw.Draw(overlay)
    od.ellipse([cx-r, cy-r, cx+r, cy+r], outline=(*ACCENT, alpha), width=1)
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
img.save(OUT, "PNG")
print(f"Banner salvato: {OUT}")
