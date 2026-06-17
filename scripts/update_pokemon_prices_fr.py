import requests, time, os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from supabase import create_client

SB_URL = os.environ['SB_URL']
SB_SERVICE_KEY = os.environ['SB_SERVICE_KEY']
sb = create_client(SB_URL, SB_SERVICE_KEY)

session = requests.Session()
retry = Retry(total=3, backoff_factor=2, status_forcelist=[500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retry))

print("Fetch sets TCGdex FR pour les prix...")
r = session.get("https://api.tcgdex.net/v2/fr/sets", timeout=60)
sets = r.json()
print(f"Sets: {len(sets)}")

all_rows = []

for s in sets:
    set_id = s.get('id')
    if not set_id:
        continue
    try:
        r = session.get(f"https://api.tcgdex.net/v2/fr/sets/{set_id}", timeout=60)
        if r.status_code != 200:
            continue
        data = r.json()
        cards = data.get('cards', [])

        for c in cards:
            cid = c.get('id')
            if not cid:
                continue
            pricing = c.get('pricing', {})
            cm = pricing.get('cardmarket', {}) if pricing else {}
            tcg = pricing.get('tcgplayer', {}) if pricing else {}

            price_eur = cm.get('avg')
            price_low_eur = cm.get('low')
            price_trend_eur = cm.get('trend')
            price_avg30_eur = cm.get('avg30')
            price_market_usd = tcg.get('marketPrice')

            if any([price_eur, price_low_eur, price_trend_eur, price_avg30_eur]):
                all_rows.append({
                    'id': cid,
                    'price_eur': round(price_eur, 2) if price_eur else None,
                    'price_low_eur': round(price_low_eur, 2) if price_low_eur else None,
                    'price_trend_eur': round(price_trend_eur, 2) if price_trend_eur else None,
                    'price_avg30_eur': round(price_avg30_eur, 2) if price_avg30_eur else None,
                    'price_market_usd': round(price_market_usd, 2) if price_market_usd else None,
                })

        time.sleep(0.1)
        print(f"Set {set_id}: {len(cards)} cartes | total collecté: {len(all_rows)}")

    except Exception as e:
        print(f"Erreur set {set_id}: {str(e)[:60]}")

print(f"\nTotal avec prix FR: {len(all_rows)}")

# Update via fonction PostgreSQL
BATCH = 500
updated = 0
errors = 0

# Créer une fonction SQL pour update les prix FR
for i in range(0, len(all_rows), BATCH):
    batch = all_rows[i:i+BATCH]
    try:
        # Update via REST PATCH par carte (on a pas d'autre choix sans RPC custom)
        rows_supabase = [{
            'card_id': r['id'],
            'price_eur': r['price_eur'],
            'price_low_eur': r['price_low_eur'],
            'price_trend_eur': r['price_trend_eur'],
            'price_avg30_eur': r['price_avg30_eur'],
            'price_market_usd': r['price_market_usd'],
        } for r in batch if r.get('price_eur') or r.get('price_market_usd')]

        if rows_supabase:
            sb.table('prices').upsert(rows_supabase, on_conflict='card_id').execute()
            updated += len(rows_supabase)
        print(f"Batch {i//BATCH+1}: {updated} prix FR injectés")
    except Exception as e:
        print(f"Erreur batch {i//BATCH+1}: {str(e)[:80]}")
        errors += 1

print(f"\nTERMINE: {updated} prix FR injectés | {errors} erreurs")
