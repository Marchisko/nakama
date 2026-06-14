import requests, time, os
from supabase import create_client

SB_URL = os.environ['SB_URL']
SB_KEY = os.environ['SB_KEY']
PC_TOKEN = os.environ['PC_TOKEN']
sb = create_client(SB_URL, SB_KEY)

print("Demarrage mise a jour prix One Piece...")

# Recuperer toutes les cartes One Piece
all_cards = []
offset = 0
while True:
    batch = sb.table('cards').select('id,name,set_id').eq('game','onepiece').range(offset, offset+999).execute()
    if not batch.data: break
    all_cards.extend(batch.data)
    offset += 1000
    if len(batch.data) < 1000: break

print("Total cartes One Piece:", len(all_cards))

def safe_get(url):
    for attempt in range(3):
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200 and r.text.strip():
                return r.json()
        except: pass
        time.sleep(2 ** attempt)
    return None

def get_prices(card_id, name):
    base = card_id.split('_')[0]
    keyword = 'Alternate Art' if '_p' in card_id else ''
    query = f"{name} {keyword} {base} One Piece Card Game".strip()
    data = safe_get(f"https://www.pricecharting.com/api/products?q={requests.utils.quote(query)}&t={PC_TOKEN}&status=price")
    if not data: return None
    products = data.get('products', [])
    if not products: return None

    en_prod = next((p for p in products if 'Japanese' not in p.get('console-name','')), None)
    jp_prod = next((p for p in products if 'Japanese' in p.get('console-name','')), None)

    result = {}
    for key, prod in [('en', en_prod), ('jp', jp_prod)]:
        if not prod: continue
        detail = safe_get(f"https://www.pricecharting.com/api/product?id={prod['id']}&t={PC_TOKEN}")
        if not detail: continue
        time.sleep(0.3)
        def c(v): return round(v/100, 2) if v and v > 0 else None
        result[f'price_{key}_usd'] = c(detail.get('loose-price'))
        result[f'price_{key}_graded_usd'] = c(detail.get('condition-17-price'))

    return result if result else None

updated = 0
errors = 0

for i, card in enumerate(all_cards):
    prices = get_prices(card['id'], card['name'] or '')
    time.sleep(0.5)

    if prices:
        prices['card_id'] = card['id']
        try:
            sb.table('prices').upsert(prices, on_conflict='card_id').execute()
            updated += 1
        except Exception as e:
            errors += 1
            print("Erreur", card['id'], str(e)[:60])
    else:
        errors += 1

    if (i+1) % 200 == 0:
        print(i+1, "/", len(all_cards), "--", updated, "mis a jour |", errors, "erreurs")

print("TERMINE:", updated, "mis a jour |", errors, "erreurs")
