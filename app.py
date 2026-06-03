import os
import requests as req
from flask import Flask, jsonify, request

app = Flask(__name__)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def supabase_get(table, params=""):
    url = f"{SUPABASE_URL}/rest/v1/{table}?{params}"
    r = req.get(url, headers=HEADERS)
    return r.json()

@app.route("/")
def health():
    return jsonify({"status": "ok", "app": "OnePieceItem API"})

@app.route("/api/cards")
def get_cards():
    params = []
    name = request.args.get("name")
    set_id = request.args.get("set_id")
    rarity = request.args.get("rarity")
    limit = request.args.get("limit", "50")
    offset = request.args.get("offse
