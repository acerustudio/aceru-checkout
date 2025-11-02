import os
import csv
import argparse
import pandas as pd

# --- CORE CONFIGURATION & SETUP ---
PRODUCTS_CSV = "outputs/shopify_import.csv"         # base products (or shopify_import_pod.csv)
IMAGES_CSV = "outputs/shopify_images.csv"           # from image_seo_prep.py
FILE_URLS_CSV = "outputs/file_urls.csv"             # optional: mapping {new_filename,url}
OUT_CSV = "outputs/shopify_import_with_images.csv"

REQUIRED_PRODUCT_COLS = {"Handle","Title","Body (HTML)","Vendor","Status"}
IMAGE_COLS = {"Handle","Image Src","Image Alt Text","Image Position"}

def load_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing file: {path}")
    return pd.read_csv(path)

def ensure_cols(df: pd.DataFrame, cols: set, name: str):
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"{name} missing required columns: {missing}")

def main():
    ap = argparse.ArgumentParser(description="Merge images into Shopify product CSV")
    ap.add_argument("--products", default=PRODUCTS_CSV, help="Path to base Shopify product CSV")
    ap.add_argument("--images", default=IMAGES_CSV, help="Path to image rows CSV (Handle, Image Src, Image Alt Text, Image Position)")
    ap.add_argument("--file-urls", default=FILE_URLS_CSV, help="Optional mapping CSV with columns: new_filename,url")
    ap.add_argument("--out", default=OUT_CSV, help="Output merged CSV")
    args = ap.parse_args()

    prod = load_csv(args.products)
    ensure_cols(prod, REQUIRED_PRODUCT_COLS, "Products CSV")

    imgs = load_csv(args.images)
    ensure_cols(imgs, IMAGE_COLS, "Images CSV")

    # Optional: filename -> URL mapping (after you upload files to Shopify > Settings > Files)
    filemap = {}
    if os.path.exists(args.file_urls):
        m = load_csv(args.file_urls)
        # Expect columns: new_filename, url   (case-insensitive tolerated)
        cols = {c.lower(): c for c in m.columns}
        if "new_filename" in cols and "url" in cols:
            for _, row in m.iterrows():
                fn = str(row[cols["new_filename"]]).strip()
                url = str(row[cols["url"]]).strip()
                if fn and url:
                    filemap[fn] = url

    # Replace Image Src with URL if mapping present; otherwise keep filenames
    if filemap:
        imgs["Image Src"] = imgs["Image Src"].apply(lambda x: filemap.get(str(x).strip(), x))

    # Build merged output:
    #  - Keep all product rows as-is.
    #  - Append one image row per image with only Handle + Image columns set (Shopify merges by Handle).
    out_cols = list(prod.columns)
    # Ensure image columns exist in output schema
    for col in ["Image Src","Image Alt Text","Image Position"]:
        if col not in out_cols:
            out_cols.append(col)

    merged_rows = []

    # 1) Add all product rows
    for _, r in prod.iterrows():
        row = {c: r[c] if c in r else "" for c in out_cols}
        merged_rows.append(row)

    # 2) Append image rows (blank non-image fields)
    blank_template = {c: "" for c in out_cols}
    for _, r in imgs.iterrows():
        row = blank_template.copy()
        row["Handle"] = r["Handle"]
        row["Image Src"] = r.get("Image Src","")
        row["Image Alt Text"] = r.get("Image Alt Text","")
        row["Image Position"] = r.get("Image Position","")
        merged_rows.append(row)

    out_df = pd.DataFrame(merged_rows, columns=out_cols)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    out_df.to_csv(args.out, index=False)
    print(f"[OK] Merged CSV → {args.out}")
    if filemap:
        print("[INFO] Image Src values replaced with Shopify file URLs from mapping.")
    else:
        print("[INFO] Image Src left as filenames. Upload to Shopify Files and replace later if needed.")

# --- Execution Block ---
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[FATAL ERROR] {e}")
