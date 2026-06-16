import requests, time, os, json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from supabase import create_client

SB_URL = os.environ['SB_URL']
SB_SERVICE_KEY = os.environ['SB_SERVICE_KEY']
sb = create_client(SB_URL, SB_SERVICE_KEY)

session = requests.Session()
retry = Retry(total=3, backoff_factor=2, status_forcelist=[500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retry))

print("Fetch sets TCGdex FR...")
r = session.get("https://api.tcgdex.net/v2/fr/sets", timeout=60)
sets = r.json()
print(f"Sets trouvés: {len(sets)}")

# Collecter toutes les données FR en mémoire
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
            image = c.get('image')
            all_rows.append({
                'id': cid,
                'name_fr': c.get('name'),
                'image_url_fr': (image + "/high.webp") if image else None,
            })
        time.sleep(0.1)
    except Exception as e:
        print(f"Erreur set {set_id}: {str(e)[:60]}")

print(f"Total cartes FR collectées: {len(all_rows)}")

# Update via la fonction PostgreSQL par batch de 1000
BATCH = 1000
updated = 0
errors = 0

for i in range(0, len(all_rows), BATCH):
    batch = all_rows[i:i+BATCH]
    try:
        sb.rpc('update_cards_fr', {'data': batch}).execute()
        updated += len(batch)
        print(f"Batch {i//BATCH + 1}: {len(batch)} cartes | total: {updated}")
    except Exception as e:
        print(f"Erreur batch {i//BATCH + 1}: {str(e)[:80]}")
        errors += len(batch)

print(f"\nTERMINE: {updated} cartes FR mises à jour | {errors} erreurs")
