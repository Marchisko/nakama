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

print("Fetch sets TCGdex FR...")
r = session.get("https://api.tcgdex.net/v2/fr/sets", timeout=60)
sets = r.json()
print(f"Sets trouvés: {len(sets)}")

# Debug: affiche les 3 premiers sets et leurs cartes
for s in sets[:3]:
    set_id = s.get('id')
    print(f"\nTest set: {set_id}")
    r2 = session.get(f"https://api.tcgdex.net/v2/fr/sets/{set_id}", timeout=60)
    data = r2.json()
    cards = data.get('cards', [])
    print(f"Cartes dans set: {len(cards)}")
    if cards:
        print(f"Exemple carte: {cards[0]}")
        # Test upsert direct
        c = cards[0]
        cid = c.get('id')
        name_fr = c.get('name')
        image = c.get('image')
        image_url_fr = (image + "/high.webp") if image else None
        print(f"ID: {cid}, name_fr: {name_fr}, image_url_fr: {image_url_fr}")
        try:
            res = sb.table('cards').upsert({'id': cid, 'name_fr': name_fr, 'image_url_fr': image_url_fr}, on_conflict='id').execute()
            print(f"Upsert result: {res}")
        except Exception as e:
            print(f"Erreur upsert: {e}")
    time.sleep(0.5)

print("\nDEBUG TERMINE")
