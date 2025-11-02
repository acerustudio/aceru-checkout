import os
import csv
import json
import textwrap
from dotenv import load_dotenv

# --- CORE CONFIGURATION & SETUP ---
load_dotenv()
PROJECT = "Landing Page Generator"
KIT_PATH = "outputs/desk_niche.json"
PRODUCT_CSV = "outputs/product_copy.csv"
OUT_HERO = "outputs/landing_hero.html"
OUT_GRID = "outputs/product_grid.html"

# --- Helpers ---
def load_kit(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing kit: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_products(csv_path: str) -> list[dict]:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Missing product csv: {csv_path}")
    out = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out.append(row)
    return out

def build_hero_html(kit: dict) -> str:
    lo = kit.get("landing_outline", {})
    hero = lo.get("hero", "Minimalist Tools for Maximum Focus")
    promise = lo.get("promise", "Refine your workspace. Focus on what matters.")
    bullets = lo.get("3_bullets", ["Clutter-free", "Durable materials", "Ships fast"])
    proof = lo.get("social_proof", "Trusted by remote pros in 20+ countries")

    bullets_li = "".join(f"<li>• {b}</li>" for b in bullets[:3])

    html = f"""<section style="font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif; padding:48px 16px; max-width:1100px; margin:0 auto;">
  <div style="display:flex; flex-wrap:wrap; gap:24px; align-items:center;">
    <div style="flex:1; min-width:280px;">
      <h1 style="font-size:44px; line-height:1.1; margin:0 0 12px; font-weight:800;">{hero}</h1>
      <p style="font-size:18px; color:#444; margin:8px 0 16px;">{promise}</p>
      <ul style="list-style:none; padding:0; margin:0 0 16px; color:#222; font-size:16px;">
        {bullets_li}
      </ul>
      <div style="display:flex; gap:12px; margin-top:10px;">
        <a href="/collections/all" style="background:#111; color:#fff; padding:12px 18px; border-radius:8px; text-decoration:none;">Shop Collection</a>
        <a href="#featured" style="border:1px solid #111; color:#111; padding:12px 18px; border-radius:8px; text-decoration:none;">See Bestsellers</a>
      </div>
      <p style="margin-top:12px; color:#666; font-size:14px;">{proof}</p>
    </div>
    <div style="flex:1; min-width:280px; background:#f6f6f6; border-radius:16px; height:320px; display:flex; align-items:center; justify-content:center; color:#666;">
      <span>Hero Image Placeholder (upload in theme)</span>
    </div>
  </div>
</section>"""
    return html

def build_grid_html(products: list[dict], limit: int = 8) -> str:
    cards = []
    for row in products[:limit]:
        title = row.get("Title","").strip()
        price = row.get("Variant Price","").strip() or "19.99"
        handle = "-".join(title.lower().split())
        img = (row.get("Image Src") or "").strip()
        img_tag = f'<img src="{img}" alt="{title}" style="width:100%; height:200px; object-fit:cover; border-radius:10px; background:#eee;">' if img else '<div style="width:100%; height:200px; background:#eee; border-radius:10px;"></div>'
        cards.append(f"""
      <a href="/products/{handle}" style="text-decoration:none; color:inherit;">
        <div style="border:1px solid #eee; border-radius:12px; padding:12px; background:#fff; transition:transform .1s;">
          {img_tag}
          <div style="margin-top:10px;">
            <div style="font-weight:600; font-size:15px; line-height:1.3; color:#111;">{title}</div>
            <div style="color:#444; margin-top:6px;">${price}</div>
          </div>
        </div>
      </a>""")
    grid = "\n".join(f"<div>{c}</div>" for c in cards)

    html = f"""<section id="featured" style="font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif; padding:24px 16px; max-width:1100px; margin:0 auto;">
  <h2 style="font-size:28px; font-weight:800; margin:8px 0 20px;">Featured Picks</h2>
  <div style="display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:16px;">
    {grid}
  </div>
</section>"""
    return html

def main():
    kit = load_kit(KIT_PATH)
    products = load_products(PRODUCT_CSV)

    hero = build_hero_html(kit)
    grid = build_grid_html(products, limit=8)

    os.makedirs("outputs", exist_ok=True)
    with open(OUT_HERO, "w", encoding="utf-8") as f: f.write(hero)
    with open(OUT_GRID, "w", encoding="utf-8") as f: f.write(grid)

    print(f"[OK] Wrote {OUT_HERO}")
    print(f"[OK] Wrote {OUT_GRID}")
    print("[SUCCESS] Landing sections ready. Paste into Shopify > Online Store > Themes > Customize > Add section > Custom liquid (or a new page).")

# --- Execution Block ---
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[FATAL ERROR] {e}")
