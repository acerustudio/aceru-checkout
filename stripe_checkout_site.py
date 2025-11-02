import os
import pandas as pd
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template_string, send_from_directory

# --- CORE CONFIGURATION & SETUP ---
load_dotenv()
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")

if not STRIPE_PUBLISHABLE_KEY or not STRIPE_SECRET_KEY:
    print("[FATAL ERROR] Missing STRIPE_PUBLISHABLE_KEY or STRIPE_SECRET_KEY in .env")
    raise SystemExit(1)

import stripe
stripe.api_key = STRIPE_SECRET_KEY

CURRENCY = "gbp"                         # change to 'usd' if needed
PRODUCTS_CSV = "outputs/product_copy.csv"
STORE_NAME = "Aceru Studio"

# Use localhost for now. When you deploy, change to your live domain:
BASE_URL = "http://localhost:5000"
SUCCESS_URL = f"{BASE_URL}/success?session_id={{CHECKOUT_SESSION_ID}}"
CANCEL_URL = f"{BASE_URL}/cancel"

# --- Load a simple catalog from CSV ---
def load_catalog(path: str):
    if not os.path.exists(path):
        print(f"[FATAL ERROR] Missing {path}. Generate it with ecom_agents.py product_copy")
        raise SystemExit(1)
    df = pd.read_csv(path)
    catalog = []
    for _, r in df.iterrows():
        title = str(r.get("Title", "")).strip()
        price_str = str(r.get("Variant Price", "19.99")).strip()
        try:
            unit_amount = int(round(float(price_str) * 100))
        except Exception:
            unit_amount = 1999
        handle = "-".join(title.lower().split())
        catalog.append({
            "handle": handle,
            "title": title[:70],
            "unit_amount": unit_amount,
        })
    return catalog[:8]  # keep page tidy

CATALOG = load_catalog(PRODUCTS_CSV)

# --- Flask app ---
app = Flask(__name__)

INDEX_HTML = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>{{ store_name }} — Checkout</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
      body{font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:0;background:#f6f7f9;color:#111}
      .wrap{max-width:1100px;margin:0 auto;padding:24px}
      .hero{background:#fff;border-radius:16px;padding:24px;margin:16px 0;border:1px solid #eee}
      h1{font-size:28px;margin:0 0 8px}
      .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px;margin-top:16px}
      .card{background:#fff;border:1px solid #eee;border-radius:12px;padding:14px}
      .title{font-weight:700;font-size:15px;line-height:1.3;margin-bottom:8px}
      .price{color:#333;margin:6px 0 12px}
      button{appearance:none;border:0;background:#111;color:#fff;padding:10px 14px;border-radius:8px;cursor:pointer}
      button:disabled{opacity:.5;cursor:not-allowed}
      .foot{color:#666;margin-top:12px;font-size:13px}
      a{color:#111}
    </style>
    <script>
      async function buy(handle){
        const res = await fetch("/create-checkout-session",{
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body: JSON.stringify({handle})
        });
        const data = await res.json();
        if(data.url){ window.location = data.url; } else { alert(data.error || "Checkout error"); }
      }
    </script>
  </head>
  <body>
    <div class="wrap">
      <div class="hero">
        <h1>{{ store_name }}</h1>
        <div>Minimalist workspace goods. Secure payments by Stripe.</div>
        <div class="foot">Live mode — place a small test order to verify.</div>
      </div>

      <div class="grid">
        {% for p in catalog %}
        <div class="card">
          <div class="title">{{ p.title }}</div>
          <div class="price">£{{ '%.2f' % (p.unit_amount/100) }}</div>
          <button onclick="buy('{{ p.handle }}')">Buy now</button>
        </div>
        {% endfor %}
      </div>

      <div class="foot">Questions? <a href="mailto:sales@acerustudio.com">sales@acerustudio.com</a></div>
    </div>
  </body>
</html>
"""

@app.route("/favicon.ico")
def favicon():
    # quiet the 404s; you can replace with a real favicon file later
    return ("", 204)

@app.route("/")
def index():
    return render_template_string(INDEX_HTML, store_name=STORE_NAME, catalog=CATALOG)

@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    data = request.get_json(silent=True) or {}
    handle = (data.get("handle") or "").strip().lower()
    product = next((p for p in CATALOG if p["handle"] == handle), None)
    if not product:
        return jsonify({"error":"Product not found"}), 404

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": CURRENCY,
                    "unit_amount": product["unit_amount"],
                    "product_data": { "name": product["title"] },
                },
                "quantity": 1,
            }],
            success_url=SUCCESS_URL,
            cancel_url=CANCEL_URL,

            # Collect details
            billing_address_collection="auto",
            shipping_address_collection={"allowed_countries": [
                "GB","IE","US","CA","AU","NZ","DE","FR","ES","NL","SE","DK","NO","IT"
            ]},
            phone_number_collection={"enabled": True},
            customer_creation="always",

            # Show promo code input on Stripe Checkout
            allow_promotion_codes=True,

            # --- Flat shipping option (£3.49) ---
            shipping_options=[{
                "shipping_rate_data": {
                    "display_name": "Standard Shipping",
                    "type": "fixed_amount",
                    "fixed_amount": {"amount": 349, "currency": CURRENCY},
                    "delivery_estimate": {
                        "minimum": {"unit": "business_day", "value": 2},
                        "maximum": {"unit": "business_day", "value": 5}
                    }
                }
            }],
        )
        return jsonify({"url": session.url})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/success")
def success():
    # Show simple order summary using the session_id
    import html
    session_id = request.args.get("session_id", "")
    email = amount_total = ""
    try:
        if session_id:
            session = stripe.checkout.Session.retrieve(session_id, expand=["customer_details"])
            email = (session.customer_details.email if session.customer_details else "") or ""
            amount_total = f"£{session.amount_total/100:.2f}"
    except Exception:
        pass
    body = f"""
    <h2>✅ Payment successful. Thank you!</h2>
    <p>Amount: <strong>{html.escape(amount_total or '—')}</strong></p>
    <p>Receipt will be sent to: <strong>{html.escape(email or 'your email')}</strong></p>
    <p><a href="/">Return to store</a></p>
    """
    return body

@app.route("/cancel")
def cancel():
    return "<h2>❌ Payment cancelled. You were not charged.</h2><p><a href='/'>Return to store</a></p>"

# --- Execution Block ---
if __name__ == "__main__":
    try:
        print("\n[INFO] Starting Stripe checkout site at http://localhost:5000")
        print("[INFO] Using LIVE keys. Place a small order to verify.")
        app.run(host="0.0.0.0", port=5000, debug=False)
    except Exception as e:
        print(f"[FATAL ERROR] {e}")
