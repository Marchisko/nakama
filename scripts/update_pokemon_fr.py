import requests, time, os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from supabase import create_client

SB_URL = os.environ['SB_URL']
SB_KEY = os.environ['SB_KEY']
sb = create_client(SB_URL, SB_KEY)

session = requests.Session()
retry = Retry(total=3, backoff_factor=2, status_forcelist=[500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retry))

# 1. Récupère tous les sets depuis TCGdex FR
print("Fetch sets TCGdex FR...")
r = session.get("https://api.tcgdex.net/v2/fr/sets", timeout=60)
sets = r.json()
print(f"Sets trouvés: {len(sets)}")

updated = 0
no_img = 0
errors = 0

# 2. Pour chaque set, fetch les cartes FR
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
        if not cards:
            continue

        rows = []
        for c in cards:
            cid = c.get('id')
            name_fr = c.get('name')
            image = c.get('image')
            image_url_fr = (image + "/high.webp") if image else None

            if cid and (name_fr or image_url_fr):
                rows.append({
                    'id': cid,
                    'name_fr': name_fr,
                    'image_url_fr': image_url_fr,
                })

        if rows:
            for i in range(0, len(rows), 100):
                batch = rows[i:i+100]
                try:
                    sb.table('cards').upsert(batch, on_conflict='id').execute()
                    updated += len(batch)
                except Exception as e:
                    print(f"Erreur upsert {set_id}: {str(e)[:80]}")
                    errors += 1

        print(f"Set {set_id}: {len(rows)} cartes FR injectées")
        time.sleep(0.2)

    except Exception as e:
        print(f"Erreur set {set_id}: {str(e)[:80]}")
        errors += 1

print(f"\nTERMINE: {updated} cartes FR injectées | {errors} erreurs")
