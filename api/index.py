import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Error initializing Supabase client: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/data?table=<name>
# General-purpose table fetch used by all frontend pages on load.
# Allowed tables are explicitly whitelisted for security.
# ─────────────────────────────────────────────────────────────────────────────

ALLOWED_TABLES = {"products", "contacts", "categories", "inquiries"}


@app.route("/api/data")
def get_data():
    if not supabase:
        return jsonify({
            "error": "Supabase client not configured. Set SUPABASE_URL and SUPABASE_KEY."
        }), 503

    table_name = request.args.get("table", "products")

    if table_name not in ALLOWED_TABLES:
        return jsonify({"error": f"Table '{table_name}' is not accessible."}), 400

    try:
        response = supabase.table(table_name).select("*").execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/products
# Fetch products, with optional ?category=<name> filter.
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/products")
def get_products():
    if not supabase:
        return jsonify({"error": "Supabase client not configured."}), 503

    try:
        category = request.args.get("category")
        query = supabase.table("products").select("*").order("created_at", desc=True)
        if category:
            query = query.eq("category", category)
        response = query.execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/contact
# Save a contact form submission to the `contacts` Supabase table.
# Expected JSON body: { name, company, email, message }
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/contact", methods=["POST"])
def submit_contact():
    data = request.get_json(silent=True) or {}

    name = data.get("name", "").strip()
    company = data.get("company", "").strip()
    email = data.get("email", "").strip()
    message = data.get("message", "").strip()

    if not name or not email or not message:
        return jsonify({"error": "name, email, and message are required."}), 400

    if not supabase:
        return jsonify({
            "success": True,
            "note": "Supabase not configured — message not persisted."
        })

    try:
        response = supabase.table("contacts").insert({
            "name": name,
            "company": company,
            "email": email,
            "message": message,
        }).execute()

        record_id = response.data[0].get("id") if response.data else None
        return jsonify({"success": True, "id": record_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/healthz
# Simple health check — useful for Vercel deployment verification.
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/api/healthz")
def healthz():
    return jsonify({
        "status": "ok",
        "supabase_connected": supabase is not None,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Local dev entrypoint (not used by Vercel — Vercel imports `app` directly)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
