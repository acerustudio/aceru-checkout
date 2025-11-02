import os
import csv
import json
import textwrap
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

# --- CORE CONFIGURATION & SETUP ---
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TARGET_MODEL = os.getenv("OPTIMIZER_MODEL", "gpt-5-turbo")

INPUT_CSV = "outputs/product_copy.csv"
OUT_CSV = "outputs/product_optimized.csv"
LOG_CSV = "outputs/experiments_log.csv"

if not OPENAI_API_KEY:
    print("[FATAL ERROR] OPENAI_API_KEY missing in .env")
    raise SystemExit(1)

try:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
except Exception:
    import openai
    openai.api_key = OPENAI_API_KEY
    client = None

# --- PROMPTS ---
SYSTEM_PROMPT = """
You are an elite ecommerce optimizer. Your job: maximize CTR and conversion.
Rules:
- Titles <= 70 chars, start with the core benefit.
- 3 bullets, tight benefits (<= 90 chars each).
- Meta description 140–155 chars, include primary keyword.
- Generate 3 alternative price points: base (same), +10%, -10%.
- Alt text: 8–12 words, include material/usage if known.
Output strict JSON:
{
 "title": "...",
 "bullets": ["...","...","..."],
 "meta": "...",
 "alt_text": "...",
 "prices": {"base": 0.00, "plus10": 0.00, "minus10": 0.00},
 "notes": "why these changes will convert"
}
"""

USER_TMPL = """
PRODUCT:
Title: {title}
Price: {price}
Context: {context}
Primary keyword: {keyword}
"""

def call_openai_json(system: str, user: str) -> dict:
    if client:
        resp = client.chat.completions.create(
            model=TARGET_MODEL,
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            response_format={"type":"json_object"},
            temperature=0.3,
            max_tokens=800
        )
        content = resp.choices[0].message.content
    else:
        resp = openai.ChatCompletion.create(
            model=TARGET_MODEL,
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            temperature=0.3,
            max_tokens=800
        )
        content = resp["choices"][0]["message"]["content"]

    try:
        return json.loads(content)
    except Exception:
        # best-effort salvage
        content = content.strip()
        s = content.find("{")
        e = content.rfind("}")
        return json.loads(content[s:e+1])

def ensure_outputs():
    os.makedirs("outputs", exist_ok=True)
    if not os.path.exists(LOG_CSV):
        with open(LOG_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                "ts_iso","handle","old_title","new_title","old_price","base","plus10","minus10","notes"
            ])

def make_handle(title: str) -> str:
    return "-".join(str(title).lower().strip().split())

def main():
    ensure_outputs()
    if not os.path.exists(INPUT_CSV):
        print(f"[FATAL ERROR] Missing {INPUT_CSV}")
        return

    df = pd.read_csv(INPUT_CSV)
    required = ["Title","Body (HTML)","Variant Price"]
    for c in required:
        if c not in df.columns:
            print(f"[FATAL ERROR] {INPUT_CSV} missing required column: {c}")
            return

    rows_out = []
    for _, r in df.iterrows():
        title = str(r.get("Title","")).strip()
        price = float(str(r.get("Variant Price","19.99")).strip() or 19.99)
        body  = str(r.get("Body (HTML)","")).strip()

        # naive keyword guess from title (first 2-3 nouns-ish)
        keyword = " ".join(title.split()[:3])

        user = USER_TMPL.format(title=title, price=f"{price:.2f}", context=body[:500], keyword=keyword)
        data = call_openai_json(SYSTEM_PROMPT, user)

        new_title = data.get("title", title)[:70]
        prices = data.get("prices", {})
        base   = float(prices.get("base", price) or price)
        plus10 = float(prices.get("plus10", round(price*1.10,2)))
        minus10 = float(prices.get("minus10", round(price*0.90,2)))

        # build output row (keep original columns, add our optimized ones)
        out_row = dict(r)
        out_row["Handle"] = out_row.get("Handle", make_handle(title))
        out_row["Optimized Title"] = new_title
        out_row["Bullets"] = " | ".join(data.get("bullets", []))
        out_row["SEO Meta"] = data.get("meta","")
        out_row["Image Alt Text"] = data.get("alt_text","")
        out_row["Price Base"] = f"{base:.2f}"
        out_row["Price +10%"] = f"{plus10:.2f}"
        out_row["Price -10%"] = f"{minus10:.2f}"
        rows_out.append(out_row)

        # log experiment
        with open(LOG_CSV, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                datetime.utcnow().isoformat(),
                out_row["Handle"],
                title,
                new_title,
                f"{price:.2f}",
                f"{base:.2f}",
                f"{plus10:.2f}",
                f"{minus10:.2f}",
                data.get("notes","")
            ])

    out_df = pd.DataFrame(rows_out)
    out_df.to_csv(OUT_CSV, index=False, encoding="utf-8")
    print(f"[OK] Optimized products → {OUT_CSV}")
    print(f"[OK] Experiments log → {LOG_CSV}")

# --- Execution Block ---
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[FATAL ERROR] {e}")
