import os
import csv
import itertools
import pandas as pd
from dotenv import load_dotenv

# --- CORE CONFIGURATION & SETUP ---
load_dotenv()
INPUT_CSV = "outputs/product_copy.csv"
OUT_CSV = "outputs/shopify_import_pod.csv"

# Configure your POD matrices here
SIZES = ["S","M","L","XL","2XL"]
COLORS = ["black","white","navy"]
PRICE_BY_SIZE = {"S":"24.90","M":"24.90","L":"24.90","XL":"26.90","2XL":"26.90"}
SKU_PREFIX = "TEE"

def slug(s): return "-".join(str(s).lower().strip().split())

def main():
    if not os.path.exists(INPUT_CSV):
        raise FileNotFoundError(f"Missing {INPUT_CSV}. Run product_copy first.")
    base = pd.read_csv(INPUT_CSV)

    rows = []
    for _, r in base.iterrows():
        title = str(r["Title"])
        handle = slug(title)
        body = r["Body (HTML)"]
        vendor = r.get("Vendor","Aceru Studio")
        tags = r.get("Tags","")
        status = r.get("Status","active")

        first = True
        for color, size in itertools.product(COLORS, SIZES):
            sku = f"{SKU_PREFIX}-{color[:1].upper()}{size}"
            price = PRICE_BY_SIZE.get(size, r.get("Variant Price","24.90"))
            rows.append({
                "Handle": handle if first else "",
                "Title": title if first else "",
                "Body (HTML)": body if first else "",
                "Vendor": vendor if first else "",
                "Type": "t-shirt" if first else "",
                "Tags": tags if first else "",
                "Published": True if first else "",
                "Option1 Name": "Color",
                "Option1 Value": color,
                "Option2 Name": "Size",
                "Option2 Value": size,
                "Variant SKU": sku,
                "Variant Grams": "",
                "Variant Inventory Tracker": "",
                "Variant Inventory Qty": 20,
                "Variant Inventory Policy": "deny",
                "Variant Fulfillment Service": "manual",
                "Variant Price": price,
                "Variant Compare At Price": "",
                "Variant Requires Shipping": True,
                "Variant Taxable": True,
                "Image Src": "",
                "Image Position": "",
                "Gift Card": "FALSE",
                "SEO Title": title[:70] if first else "",
                "SEO Description": ("High-quality " + title)[:140] if first else "",
                "Status": status if first else "active"
            })
            first = False

    out = pd.DataFrame(rows)
    out.to_csv(OUT_CSV, index=False)
    print(f"[OK] Wrote POD Shopify CSV → {OUT_CSV}")
    print("Import: Shopify Admin → Products → Import → Upload CSV.")

# --- Execution Block ---
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[FATAL ERROR] {e}")
