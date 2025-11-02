import os
import csv
import json
import math
import time
import textwrap
import argparse
import pandas as pd
from dotenv import load_dotenv

# --- CORE CONFIGURATION & SETUP ---
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
TARGET_MODEL = "gpt-4o-mini"   # Low-cost, decent quality for copy
BUDGET_USD = float(os.getenv("OPENAI_BUDGET_USD", "10.0"))  # total spend cap
EST_COST_PER_CALL = 0.01       # rough heuristic per small copy gen call (tunable)
RATE_LIMIT_S = 0.6             # simple throttle between calls

if not API_KEY:
    print("[FATAL ERROR] OPENAI_API_KEY not found. Put it in .env")
    raise SystemExit(1)

try:
    import openai
    client = openai.OpenAI(api_key=API_KEY)
except Exception as e:
    print(f"[FATAL ERROR] OpenAI SDK not available: {e}")
    raise SystemExit(1)

# --- STRATEGIC VARIABLES (The Target) ---
PROJECT_NAME = "Bootstrap Commerce Agents"
DEFAULT_VENDOR = "Aceru Studio"
DEFAULT_CURRENCY = "USD"
DEFAULT_PRICE = "19.99"

# --- Simple budget guard (heuristic) ---
class BudgetGuard:
    def __init__(self, total_usd: float, est_per_call: float):
        self.total = total_usd
        self.spent = 0.0
        self.est = est_per_call
    def check_and_book(self, calls: int = 1):
        projected = self.spent + self.est * calls
        if projected > self.total:
            raise RuntimeError(f"Budget cap hit. Spent≈${self.spent:.2f}, need ${self.est*calls:.2f}, cap ${self.total:.2f}")
        self.spent = projected

BUDGET = BudgetGuard(BUDGET_USD, EST_COST_PER_CALL)

# --- LLM helper ---
def llm_json(system_prompt: str, user_prompt: str, max_tokens: int = 800, temperature: float = 0.7):
    BUDGET.check_and_book(1)
    time.sleep(RATE_LIMIT_S)
    resp = client.chat.completions.create(
        model=TARGET_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return json.loads(resp.choices[0].message.content)

def llm_text(system_prompt: str, user_prompt: str, max_tokens: int = 600, temperature: float = 0.7):
    BUDGET.check_and_book(1)
    time.sleep(RATE_LIMIT_S)
    resp = client.chat.completions.create(
        model=TARGET_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content.strip()

# --- AGENT 1: Niche Kit Generator ---
def generate_niche_kit(niche: str, audience: str, outfile: str):
    print(f"[AGENT:NICHE] Generating kit for niche='{niche}' → {outfile}")
    sys = "You are a lean e-commerce strategist creating profitable micro-brands with minimal budget."
    user = f"""
Return strict JSON with keys:
- "brand_names": array of 10 short brand name ideas for "{niche}".
- "angles": array of 8 value props targeted at "{audience}" (concise, punchy).
- "product_ideas": array of 12 specific product concepts (with a 1-line hook each).
- "seo_keywords": array of ~30 long-tail keywords for product pages/blog.
- "landing_outline": object with keys "hero", "promise", "3_bullets", "social_proof", "faq".
Keep it clean, dupe-free, and execution-ready.
"""
    data = llm_json(sys, user, max_tokens=900, temperature=0.6)
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[OK] Wrote {outfile}")

# --- AGENT 2: Product Copy Factory ---
def generate_product_copy(csv_in: str, csv_out: str, vendor: str = DEFAULT_VENDOR, currency: str = DEFAULT_CURRENCY):
    """
    Input CSV columns expected (flexible but recommended):
      title, features, materials, use_cases, price(optional), tags(optional), sku(optional)
    Output CSV (intermediate): title, body_html, tags, vendor, price, sku
    """
    print(f"[AGENT:COPY] Reading {csv_in}")
    df = pd.read_csv(csv_in)
    rows = []
    for _, r in df.iterrows():
        title = str(r.get("title", "")).strip()
        features = str(r.get("features", "")).strip()
        materials = str(r.get("materials", "")).strip()
        use_cases = str(r.get("use_cases", "")).strip()
        price = str(r.get("price", DEFAULT_PRICE))
        sku = str(r.get("sku", "")).strip()
        base_tags = str(r.get("tags", "")).strip()

        sys = "You write high-converting, clear, skimmable product pages for DTC stores. Keep it honest and concise."
        user = f"""
Product: {title}
Key features: {features}
Materials/specs: {materials}
Use cases / benefits: {use_cases}

Return strict JSON with:
- "title_seo": optimized title <= 70 chars (no clickbait, include key attributes).
- "body_html": HTML with <h3>Highlights</h3><ul>…</ul>, <h3>Details</h3>, <h3>Shipping & Returns</h3>.
- "tags": list of 8-15 SEO tags/keywords (lowercase, hyphenated where useful).
"""
        try:
            data = llm_json(sys, user, max_tokens=900, temperature=0.6)
            out_title = data.get("title_seo", title)[:70]
            body_html = data.get("body_html", "")
            tags = data.get("tags", [])
            tag_str = ", ".join(tags) if isinstance(tags, list) else (base_tags or "")
        except Exception as e:
            print(f"[WARN] LLM fallback for '{title}': {e}")
            out_title = title[:70]
            bullet = "".join(f"<li>{x.strip()}</li>" for x in features.split(",") if x.strip())
            body_html = f"<h3>Highlights</h3><ul>{bullet}</ul><h3>Details</h3><p>{materials}</p><h3>Shipping & Returns</h3><p>30-day returns. Tracked shipping.</p>"
            tag_str = base_tags

        rows.append({
            "Title": out_title,
            "Body (HTML)": body_html,
            "Vendor": vendor,
            "Type": "",
            "Tags": tag_str,
            "Published": True,
            "Option1 Name": "Title",
            "Option1 Value": "Default Title",
            "Variant SKU": sku or "",
            "Variant Price": price,
            "Variant Inventory Qty": 10,
            "Variant Inventory Policy": "deny",
            "Variant Fulfillment Service": "manual",
            "Variant Requires Shipping": True,
            "Variant Taxable": True,
            "Image Src": "",
            "Variant Grams": "",
            "Cost per item": "",
            "Status": "active"
        })

    out_df = pd.DataFrame(rows)
    out_df.to_csv(csv_out, index=False)
    print(f"[OK] Wrote product copy → {csv_out}")

# --- AGENT 3: Shopify CSV Builder (compatible schema) ---
def build_shopify_csv(intermediate_csv: str, shopify_csv: str):
    """
    Takes the intermediate CSV from generate_product_copy and outputs a Shopify-compatible import CSV.
    If the intermediate already matches columns, this just normalizes and writes.
    """
    print(f"[AGENT:SHOPIFY] Building Shopify CSV from {intermediate_csv}")
    df = pd.read_csv(intermediate_csv)
    # Ensure required headers exist; fill if missing
    required = [
        "Handle","Title","Body (HTML)","Vendor","Type","Tags","Published",
        "Option1 Name","Option1 Value","Variant SKU","Variant Grams","Variant Inventory Tracker",
        "Variant Inventory Qty","Variant Inventory Policy","Variant Fulfillment Service",
        "Variant Price","Variant Compare At Price","Variant Requires Shipping","Variant Taxable",
        "Image Src","Image Position","Gift Card","SEO Title","SEO Description","Status"
    ]
    out = pd.DataFrame(columns=required)
    # Map minimal fields; derive handle
    def slug(s): return "-".join(str(s).lower().strip().split())
    out["Title"] = df["Title"]
    out["Handle"] = df["Title"].apply(slug)
    out["Body (HTML)"] = df["Body (HTML)"]
    out["Vendor"] = df.get("Vendor", DEFAULT_VENDOR)
    out["Type"] = df.get("Type", "")
    out["Tags"] = df.get("Tags", "")
    out["Published"] = df.get("Published", True)
    out["Option1 Name"] = df.get("Option1 Name", "Title")
    out["Option1 Value"] = df.get("Option1 Value", "Default Title")
    out["Variant SKU"] = df.get("Variant SKU", "")
    out["Variant Grams"] = df.get("Variant Grams", "")
    out["Variant Inventory Tracker"] = ""
    out["Variant Inventory Qty"] = df.get("Variant Inventory Qty", 10)
    out["Variant Inventory Policy"] = df.get("Variant Inventory Policy", "deny")
    out["Variant Fulfillment Service"] = df.get("Variant Fulfillment Service", "manual")
    out["Variant Price"] = df.get("Variant Price", DEFAULT_PRICE)
    out["Variant Compare At Price"] = ""
    out["Variant Requires Shipping"] = df.get("Variant Requires Shipping", True)
    out["Variant Taxable"] = df.get("Variant Taxable", True)
    out["Image Src"] = df.get("Image Src", "")
    out["Image Position"] = ""
    out["Gift Card"] = "FALSE"
    out["SEO Title"] = out["Title"].str[:70]
    out["SEO Description"] = "High-quality " + out["Title"].str[:140]
    out["Status"] = df.get("Status", "active")

    out.to_csv(shopify_csv, index=False)
    print(f"[OK] Shopify import CSV → {shopify_csv}")

# --- AGENT 4: Ad-Creative Maker (Shorts/TikTok/Meta copy) ---
def generate_ad_creatives(niche: str, offer: str, outfile: str):
    print(f"[AGENT:ADS] Generating hooks & scripts for '{niche}' → {outfile}")
    sys = "You craft high-CTR short-form hooks and simple scripts that sell without hype."
    user = f"""
Offer: {offer}
Niche: {niche}
Return strict JSON with:
- "hooks": array of 20 punchy 5-8 word hooks (no clickbait buzzwords).
- "captions": array of 15 social captions (<=90 chars, with 1 CTA).
- "scripts": array of 8 short video scripts, each ~70–90 words, with [Hook]->[Value]->[CTA].
"""
    data = llm_json(sys, user, max_tokens=1100, temperature=0.7)
    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[OK] Wrote {outfile}")

# --- CLI wiring ---
def main():
    parser = argparse.ArgumentParser(description="Bootstrap Commerce Agents — low-cost ecomm toolkit")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("niche_kit", help="Generate brand names, angles, product ideas, SEO keywords, landing outline")
    p1.add_argument("--niche", required=True)
    p1.add_argument("--audience", required=True)
    p1.add_argument("--out", default="outputs/niche_kit.json")

    p2 = sub.add_parser("product_copy", help="From products.csv → intermediate copy CSV")
    p2.add_argument("--in", dest="csv_in", default="inputs/products.csv")
    p2.add_argument("--out", dest="csv_out", default="outputs/product_copy.csv")
    p2.add_argument("--vendor", default=DEFAULT_VENDOR)
    p2.add_argument("--currency", default=DEFAULT_CURRENCY)

    p3 = sub.add_parser("shopify_csv", help="Intermediate CSV → Shopify import CSV")
    p3.add_argument("--in", dest="intermediate_csv", default="outputs/product_copy.csv")
    p3.add_argument("--out", dest="shopify_csv", default="outputs/shopify_import.csv")

    p4 = sub.add_parser("ad_creatives", help="Hooks, captions, short scripts JSON")
    p4.add_argument("--niche", required=True)
    p4.add_argument("--offer", required=True)
    p4.add_argument("--out", default="outputs/ad_creatives.json")

    args = parser.parse_args()

    os.makedirs("outputs", exist_ok=True)
    os.makedirs("inputs", exist_ok=True)

    if args.cmd == "niche_kit":
        generate_niche_kit(args.niche, args.audience, args.out)

    elif args.cmd == "product_copy":
        if not os.path.exists(args.csv_in):
            # scaffold a sample
            sample = pd.DataFrame([{
                "title": "Minimalist Desk Mat (PU Leather, 90x45cm)",
                "features": "Water-resistant surface, anti-slip base, easy to clean, stitched edges",
                "materials": "PU leather top, microfiber base",
                "use_cases": "Home office, gaming desk, writing surface",
                "price": "24.90",
                "tags": "desk-mat, minimalist, office, gaming, workspace",
                "sku": "MAT-001"
            }])
            sample.to_csv(args.csv_in, index=False)
            print(f"[INFO] Created sample {args.csv_in}. Edit it, then rerun.")
            return
        generate_product_copy(args.csv_in, args.csv_out, args.vendor, args.currency)

    elif args.cmd == "shopify_csv":
        if not os.path.exists(args.intermediate_csv):
            print("[FATAL ERROR] Missing intermediate CSV. Run product_copy first.")
            return
        build_shopify_csv(args.intermediate_csv, args.shopify_csv)

    elif args.cmd == "ad_creatives":
        generate_ad_creatives(args.niche, args.offer, args.out)

if __name__ == "__main__":
    try:
        main()
        print(f"\n[SUCCESS] {PROJECT_NAME} run complete. Budget≈${BUDGET.spent:.2f}/{BUDGET.total:.2f}")
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
