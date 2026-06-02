
import os
from flask import Flask, jsonify, request
from supabase import create_client

app = Flask(__name__)
supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

@app.route("/")
def health():
    return jsonify({"status": "ok", "app": "OnePieceItem API"})

@app.route("/api/cards")
def get_cards():
    name = request.args.get("name")
    set_id = request.args.get("set_id")
    rarity = request.args.get("rarity")
    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 50))
    offset = (page - 1) * limit
    q = supabase.table("cards").select("*", count="exact")
    if name: q = q.ilike("name", f"%{name}%")
    if set_id: q = q.eq("set_id", set_id)
    if rarity: q = q.eq("rarity", rarity)
    res = q.range(offset, offset + limit - 1).execute()
    return jsonify({"cards": res.data, "total": res.count})

@app.route("/api/cards/<card_id>")
def get_card(card_id):
    res = supabase.table("cards").select("*").eq("id", card_id).single().execute()
    return jsonify(res.data)

@app.route("/api/sets")
def get_sets():
    res = supabase.table("sets").select("*").order("id").execute()
    return jsonify(res.data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 3000)))
