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

# Récupérer tous les IDs Pokémon depuis Supabase
print("Fetch IDs Pokémon depuis Supabase...")
all_ids = []
offset = 0
while True:
    res = sb.table('cards').select('id').eq('game', 'pokemon').range(offset, offset+999).execute()
    batch = [r['id'] for r in res.data]
    all_ids.extend(batch)
    if len(batch) < 1000:
        break
    offset += 1000

print(f"Total IDs: {len(all_ids)}")

rows = []
errors = 0

for i, cid in enumerate(all_ids):
    try:
        r = session.get(f"https://api.tcgdex.net/v2/fr/cards/{cid}", timeout=15)
        if r.status_code != 200:
            continue
        data = r.json()
        pricing = data.get('pricing', {})
        cm = pricing.get('cardmarket', {}) if pricing else {}
        tcg = pricing.get('tcgplayer', {}) if pricing else {}

        price_eur = cm.get('avg')
        price_low_eur = cm.get('low')
        price_trend_eur = cm.get('trend')
        price_avg30_eur = cm.get('avg30')
        price_market_usd = tcg.get('marketPrice')

        if any([price_eur, price_low_eur, price_trend_eur, price_market_usd]):
            rows.append({
                'card_id': cid,
                'price_eur': round(price_eur, 2) if price_eur else None,
                'price_low_eur': round(price_low_eur, 2) if price_low_eur else None,
                'price_trend_eur': round(price_trend_eur, 2) if price_trend_eur else None,
                'price_avg30_eur': round(price_avg30_eur, 2) if price_avg30_eur else None,
                'price_market_usd': round(price_market_usd, 2) if price_market_usd else None,
            })

        if (i+1) % 500 == 0:
            print(f"{i+1}/{len(all_ids)} | {len(rows)} avec prix FR")
        time.sleep(0.05)  # 50ms entre requêtes

    except Exception as e:
        errors += 1
        if errors % 100 == 0:
            print(f"Erreurs: {errors}")

print(f"\nTotal avec prix FR: {len(rows)}")

# Upsert par batch de 500
updated = 0
for i in range(0, len(rows), 500):
    batch = rows[i:i+500]
    try:
        sb.table('prices').upsert(batch, on_conflict='card_id').execute()
        updated += len(batch)
        print(f"Batch {i//500+1}: {updated} injectés")
    except Exception as e:
        print(f"Erreur batch: {str(e)[:80]}")

print(f"\nTERMINE: {updated} prix FR | {errors} erreurs fetch")
