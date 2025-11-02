import os
import math
import textwrap
from uuid import uuid4
from dotenv import load_dotenv

# --- CORE CONFIGURATION & SETUP ---
load_dotenv()
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

PRODUCT_CSV = "outputs/product_copy.csv"
OUT_DIR = "images_in"
IMG_SIZE = (1200, 1200)
BG_COLORS = ["#111111", "#1f2937", "#0f766e", "#065f46", "#1d4ed8", "#6d28d9", "#b91c1c", "#6b7280"]

def safe_font(size=52):
    # Try to load a common system font; fallback to PIL default
    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()

def wrap_text(text, max_chars=26):
    return "\n".join(textwrap.wrap(text, max_chars))

def draw_centered(draw, text, font, img_w, img_h, fill="#ffffff"):
    w, h = draw.multiline_textbbox((0,0), text, font=font, align="center")[2:]
    x = (img_w - w) // 2
    y = (img_h - h) // 2
    draw.multiline_text((x, y), text, font=font, fill=fill, align="center", spacing=6)

def slug(s): 
    return "-".join(str(s).lower().strip().split())

def main():
    if not os.path.exists(PRODUCT_CSV):
        print(f"[FATAL ERROR] Missing {PRODUCT_CSV}. Run product_copy first.")
        raise SystemExit(1)

    os.makedirs(OUT_DIR, exist_ok=True)
    df = pd.read_csv(PRODUCT_CSV)

    font_title = safe_font(60)
    font_sub = safe_font(34)

    count = 0
    for idx, row in df.iterrows():
        title = str(row.get("Title","")).strip() or "Product"
        handle = slug(title)
        color = BG_COLORS[idx % len(BG_COLORS)]

        # --- Hero image ---
        img = Image.new("RGB", IMG_SIZE, color)
        draw = ImageDraw.Draw(img)
        draw_centered(draw, wrap_text(title, 22), font_title, IMG_SIZE[0], IMG_SIZE[1]-140)
        # Subline
        sub = "Minimalist • Durable • Fast Shipping"
        w, h = draw.textbbox((0,0), sub, font=font_sub)[2:]
        draw.text(((IMG_SIZE[0]-w)//2, IMG_SIZE[1]-h-60), sub, font=font_sub, fill="#e5e7eb")

        out_path = os.path.join(OUT_DIR, f"{handle}-1.png")
        img.save(out_path, format="PNG")
        count += 1

        # --- Detail image (color variant) ---
        detail = Image.new("RGB", IMG_SIZE, "#f3f4f6")
        d2 = ImageDraw.Draw(detail)
        d2_center = wrap_text(f"{title}\nDetail View", 24)
        draw_centered(d2, d2_center, font_title, IMG_SIZE[0], IMG_SIZE[1])
        detail_out = os.path.join(OUT_DIR, f"{handle}-2.png")
        detail.save(detail_out, format="PNG")
        count += 1

    print(f"[OK] Generated {count} placeholder images → {OUT_DIR}")
    print("Now rerun:  python image_seo_prep.py")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[FATAL ERROR] {e}")
