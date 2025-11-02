import os
import re
import csv
import json
import argparse
import textwrap
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# --- CORE CONFIGURATION & SETUP ---
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")  # Optional for fancy ALT text
TARGET_MODEL = "gpt-4o-mini"

# Try OpenAI client if key present
client = None
if API_KEY:
    try:
        import openai
        client = openai.OpenAI(api_key=API_KEY)
    except Exception:
        client = None

INPUT_PRODUCTS = "outputs/product_copy.csv"
IMAGES_DIR = "images_in"          # put your raw images here
OUTPUT_DIR = "outputs"
OUT_MAPPING = os.path.join(OUTPUT_DIR, "image_mapping.csv")      # mapping of handle->image paths + ALT
OUT_SHOPIFY = os.path.join(OUTPUT_DIR, "shopify_images.csv")     # Shopify-compatible image import CSV

# --- Helpers ---
def slug(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "item"

def smart_alt_from_title(title: str, tags: str = "") -> str:
    base = title.strip()
    extra = ", ".join([t for t in (tags or "").split(",") if t.strip()][:3])
    if extra:
        return f"{base} — {extra}"
    return base

def llm_alt_text(title: str, tags: str = "") -> str:
    if client is None:
        return smart_alt_from_title(title, tags)
    try:
        prompt = (
            "Write a concise, descriptive ALT text (max 12 words) for an e-commerce product image. "
            "No emojis, no promotional fluff. Include 1–2 key attributes.\n"
            f"TITLE: {title}\nTAGS: {tags}"
        )
        resp = client.chat.completions.create(
            model=TARGET_MODEL,
            messages=[
                {"role": "system", "content": "You write concise, descriptive ALT text for product images."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=60,
        )
        out = resp.choices[0].message.content.strip()
        return out[:120]
    except Exception:
        return smart_alt_from_title(title, tags)

def load_products(csv_path: str) -> pd.DataFrame:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Missing product copy CSV: {csv_path}")
    return pd.read_csv(csv_path)

def discover_images(images_dir: str) -> list[Path]:
    exts = {".jpg", ".jpeg", ".png", ".webp"}
    p = Path(images_dir)
    if not p.exists():
        os.makedirs(p, exist_ok=True)
        return []
    return [f for f in p.iterdir() if f.suffix.lower() in exts and f.is_file()]

def main():
    parser = argparse.ArgumentParser(description="Rename product images + generate ALT text + Shopify image CSV")
    parser.add_argument("--products", default=INPUT_PRODUCTS, help="Path to outputs/product_copy.csv")
    parser.add_argument("--images", default=IMAGES_DIR, help="Folder of raw images to process")
    parser.add_argument("--out-mapping", default=OUT_MAPPING)
    parser.add_argument("--out-shopify", default=OUT_SHOPIFY)
    parser.add_argument("--per-product", type=int, default=3, help="Max images to assign per product")
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    df = load_products(args.products)
    imgs = discover_images(args.images)

    if not len(imgs):
        print(f"[NOTICE] No images found in '{args.images}'. Put files there and rerun.")
        return

    # Prepare rows
    mapping_rows = []
    shopify_rows = []

    # Simple round-robin assignment of images to products
    i = 0
    for idx, row in df.iterrows():
        title = str(row.get("Title","")).strip()
        tags = str(row.get("Tags","")).strip()
        handle = "-".join(title.lower().split())
        alt = llm_alt_text(title, tags)

        assigned = 0
        while assigned < args.per_product and i < len(imgs):
            src = imgs[i]
            i += 1
            assigned += 1

            # Build SEO filename
            stem = slug(f"{title}-{assigned}")
            new_name = f"{stem}{src.suffix.lower()}"
            new_path = Path(OUTPUT_DIR) / new_name

            # Copy (rename) into outputs so you have clean filenames to upload
            with open(src, "rb") as r, open(new_path, "wb") as w:
                w.write(r.read())

            mapping_rows.append({
                "handle": handle,
                "title": title,
                "orig_path": str(src),
                "new_filename": new_name,
                "new_path": str(new_path),
                "alt": alt
            })

            # Shopify image import row (append images to existing products by Handle)
            shopify_rows.append({
                "Handle": handle,
                "Image Src": new_name,           # upload these files in Shopify > Files, then paste full URL later if needed
                "Image Alt Text": alt,
                "Image Position": assigned
            })

        if i >= len(imgs):
            break

    # Write mapping CSV (for your reference)
    pd.DataFrame(mapping_rows).to_csv(args.out_mapping, index=False)
    print(f"[OK] Wrote mapping → {args.out_mapping}")

    # Write Shopify image CSV (can be merged with your product import)
    pd.DataFrame(shopify_rows).to_csv(args.out_shopify, index=False)
    print(f"[OK] Wrote Shopify image CSV → {args.out_shopify}")

    print("\nNEXT STEPS:")
    print("1) Upload the renamed files from 'outputs/' to Shopify: Settings > Files (copy each file URL).")
    print("2) Open outputs/shopify_image.csv and replace 'Image Src' with the full file URLs (bulk replace by filename).")
    print("3) Import images: Products > Import and use a CSV that includes Handle + Image Src + Image Alt Text.")
    print("   (Or merge these columns into your existing outputs/shopify_import.csv by Handle.)")
    if client is None:
        print("[NOTE] Using heuristic ALT text (no OpenAI). Add OPENAI_API_KEY in .env for richer ALT generation.")

# --- Execution Block ---
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[FATAL ERROR] {e}")
