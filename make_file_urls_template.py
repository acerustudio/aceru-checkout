import os
import csv
from dotenv import load_dotenv

# --- CORE CONFIGURATION & SETUP ---
load_dotenv()
IMAGES_DIR = "outputs"  # where image_seo_prep put the renamed images
OUT_CSV = "outputs/file_urls.csv"
EXTS = {".png", ".jpg", ".jpeg", ".webp"}

def main():
    os.makedirs("outputs", exist_ok=True)
    files = [f for f in os.listdir(IMAGES_DIR) if os.path.splitext(f)[1].lower() in EXTS]
    files.sort()
    if not files:
        print("[NOTICE] No images found in outputs/. Run image_seo_prep.py first.")
        return

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["new_filename", "url"])  # leave url blank for now
        for fn in files:
            w.writerow([fn, ""])

    print(f"[OK] Wrote template → {OUT_CSV}")
    print("Next: open it and paste each Shopify File URL in the 'url' column for the matching filename.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[FATAL ERROR] {e}")
