import os
import json
import csv
import time
import textwrap
from uuid import uuid4
from dotenv import load_dotenv

# --- CORE CONFIGURATION & SETUP ---
load_dotenv()
import argparse

API_KEY = os.getenv("OPENAI_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
TARGET_MODEL = "gpt-4o-mini"
BUDGET_USD = float(os.getenv("OPENAI_BUDGET_USD", "10.0"))
EST_COST_PER_CALL = 0.015     # tiny JSON calls
RATE_LIMIT_S = 0.6

if not API_KEY:
    print("[FATAL ERROR] OPENAI_API_KEY not found. Put it in .env")
    raise SystemExit(1)

try:
    import openai
    client = openai.OpenAI(api_key=API_KEY)
except Exception as e:
    print(f"[FATAL ERROR] OpenAI SDK not available: {e}")
    raise SystemExit(1)

# --- Simple budget guard ---
class BudgetGuard:
    def __init__(self, total_usd: float, est_per_call: float):
        self.total = total_usd
        self.spent = 0.0
        self.est = est_per_call
    def book(self, n=1):
        nxt = self.spent + self.est * n
        if nxt > self.total:
            raise RuntimeError(f"Budget cap hit (spent≈${self.spent:.2f} / cap ${self.total:.2f})")
        self.spent = nxt

BUDGET = new_budget = BudgetGuard(BUDGET_USD, EST_COST_PER_CALL)

def llm_json(system_prompt: str, user_prompt: str, max_tokens: int = 900, temperature: float = 0.6):
    BUDGET.book(1)
    time.sleep(RATE_LIMIT_S)
    resp = client.chat.completions.create(
        model=TARGET_MODEL,
        messages=[{"role":"system","content":system_prompt},
                  {"role":"user","content":user_prompt}],
        response_format={"type":"json_object"},
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return json.loads(resp.choices[0].message.content)

def load_kit(path: str) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Kit not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def seed_products_from_kit(kit_path: str, out_csv: str, max_items: int = 10, vendor: str = "Aceru Studio"):
    kit = load_kit(kit_path)
    ideas = kit.get("product_ideas", [])[:max_items]
    if not ideas:
        raise RuntimeError("No product_ideas found in kit JSON.")

    sys = "You expand product ideas into Shopify-ready row primitives for later copywriting."
    user = f"""
Product ideas (array of strings):
{json.dumps(ideas, ensure_ascii=False)}

Return strict JSON with key "rows": an array of objects.
Each object must include:
- "title": short, concrete product name with key attributes (<= 70 chars)
- "features": 4-6 comma-separated bullets (concise)
- "materials": 1-2 lines of materials/specs
- "use_cases": 2-3 concise use cases/benefits, comma-separated
- "price": numeric string like "19.99"
- "tags": 5-10 lowercase tags, comma-separated (e.g., "desk-mat, minimalist, office")
- "sku": short code (e.g., prefix + unique bits)
Do not add extra keys. No markdown, no commentary.
"""
    try:
        data = llm_json(sys, user, max_tokens=1100, temperature=0.55)
        rows = data.get("rows", [])
    except Exception as e:
        print(f"[FATAL ERROR] LLM expansion failed: {e}")
        raise

    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["title","features","materials","use_cases","price","tags","sku"])
        for r in rows:
            title = str(r.get("title","")).strip()[:70]
            features = str(r.get("features","")).strip()
            materials = str(r.get("materials","")).strip()
            uses = str(r.get("use_cases","")).strip()
            price = str(r.get("price","19.99")).strip()
            tags = str(r.get("tags","")).strip()
            sku = str(r.get("sku", f"SKU-{uuid4().hex[:6].upper()}")).strip()
            w.writerow([title, features, materials, uses, price, tags, sku])

    print(f"[OK] Seeded {len(rows)} products → {out_csv}")

# --- Execution Block ---
if __name__ == "__main__":
    try:
        ap = argparse.ArgumentParser(description="Seed inputs/products.csv from a niche kit JSON")
        ap.add_argument("--kit", default="outputs/desk_niche.json")
        ap.add_argument("--out", default="inputs/products.csv")
        ap.add_argument("--max-items", type=int, default=10)
        ap.add_argument("--vendor", default="Aceru Studio")
        args = ap.parse_args()

        os.makedirs("inputs", exist_ok=True)
        seed_products_from_kit(args.kit, args.out, args.max_items, args.vendor)
        print(f"[SUCCESS] Seed complete. Budget≈${BUDGET.spent:.2f}/{BUDGET.total:.2f}")

    except Exception as e:
        print(f"[FATAL ERROR] {e}")
