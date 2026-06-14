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

TCGDEX_BASE = "https://api.tcgdex.net/v2/fr/cards"

print("Fetch toutes les cartes FR depuis TCGdex...")

# Fetch toutes les cartes FR en une seule requête (liste légère)
r = session.get(TCGDEX_BASE, timeout=60)
all_fr = r.json()
print(f"Total cartes TCGdex FR: {len(all_fr)}")

# Construire un dict id -> {name, image}
fr_data = {}
for c in all_fr:
    cid = c.get('id')
    if not cid:
        continue
    name = c.get('name')
    img = c.get('image')
    if img:
        img = img + "/high.webp"
    fr_data[cid] = {'name_fr': name, 'image_url_fr': img}

print(f"Cartes avec données FR: {len(fr_data)}")

# Fetch les card_ids Pokémon depuis Supabase par batch
offset = 0
batch_size = 1000
updated = 0
no_match = 0

while True:
    res = sb.table('cards').select('id').eq('game', 'pokemon').range(offset, offset + batch_size - 1).execute()
    rows = res.data
    if not rows:
        break

    upsert_rows = []
    for row in rows:
        cid = row['id']
        if cid in fr_data:
            upsert_rows.append({
                'id': cid,
                'name_fr': fr_data[cid]['name_fr'],
                'image_url_fr': fr_data[cid]['image_url_fr'],
            })
            updated += 1
        else:
            no_match += 1

    if upsert_rows:
        # Update par batch de 100
        for i in range(0, len(upsert_rows), 100):
            batch = upsert_rows[i:i+100]
            try:
                sb.table('cards').upsert(batch, on_conflict='id').execute()
            except Exception as e:
                print(f"Erreur batch {i}: {str(e)[:80]}")

    print(f"Offset {offset}: {len(rows)} cartes traitées | {updated} mises à jour | {no_match} sans match")
    offset += batch_size
    if len(rows) < batch_size:
        break

print(f"TERMINE: {updated} cartes FR injectées | {no_match} sans correspondance TCGdex")
