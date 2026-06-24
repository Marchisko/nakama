import requests, time, os
from datetime import datetime, timezone, timedelta
from supabase import create_client

SB_URL = os.environ['SB_URL']
SB_KEY = os.environ['SB_KEY']
PC_TOKEN = os.environ['PC_TOKEN']
sb = create_client(SB_URL, SB_KEY)

# ── Config ──────────────────────────────────────────────────────────────────
MAX_RUNTIME_MINUTES = 150   # Stop propre à 2h30 (avant le timeout de 3h)
STALE_DAYS = 7              # Ne re-fetcher que si prix > 7 jours
BATCH_SIZE = 50             # Cartes par batch Supabase upsert
SLEEP_BETWEEN = 0.4         # Secondes entre chaque carte
# ────────────────────────────────────────────────────────────────────────────

start_time = datetime.now(timezone.utc)
deadline = start_time + timedelta(minutes=MAX_RUNTIME_MINUTES)

print(f"Demarrage mise a jour prix One Piece — deadline {deadline.strftime('%H:%M')} UTC")

# 1. Toutes les cartes OP
all_cards = []
offset = 0
while True:
    batch = sb.table('cards').select('id,name,set_id').eq('game','onepiece').range(offset, offset+999).execute()
    if not batch.data: break
    all_cards.extend(batch.data)
    if len(batch.data) < 1000: break
    offset += 1000

print(f"Total cartes: {len(all_cards)}")

# 2. Prix existants — on ne re-fetche que si stale ou absent
stale_cutoff = (datetime.now(timezone.utc) - timedelta(days=STALE_DAYS)).isoformat()
existing = {}
for offset in range(0, len(all_cards), 1000):
    ids = [c['id'] for c in all_cards[offset:offset+1000]]
    rows = sb.table('prices').select('card_id,last_updated').in_('card_id', ids).execute()
    for row in (rows.data or []):
        existing[row['card_id']] = row.get('last_updated') or ''

# Cartes à mettre à jour : absentes ou stale
to_update = [
    c for c in all_cards
    if c['id'] not in existing or existing[c['id']] < stale_cutoff
]

print(f"A mettre a jour: {len(to_update)} / {len(all_cards)} (stale > {STALE_DAYS}j ou absent)")

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
        time.sleep(0.2)
        def c(v): return round(v/100, 2) if v and v > 0 else None
        result[f'price_{key}_usd'] = c(detail.get('loose-price'))
        result[f'price_{key}_graded_usd'] = c(detail.get('condition-17-price'))

    return result if result else None

updated = 0
errors = 0
skipped_timeout = 0
batch_upsert = []

for i, card in enumerate(to_update):
    # Stop propre avant le timeout GitHub
    if datetime.now(timezone.utc) >= deadline:
        skipped_timeout = len(to_update) - i
        print(f"Deadline atteinte — {skipped_timeout} cartes reportees au prochain run")
        break

    prices = get_prices(card['id'], card['name'] or '')
    time.sleep(SLEEP_BETWEEN)

    if prices:
        prices['card_id'] = card['id']
        prices['last_updated'] = datetime.now(timezone.utc).isoformat()
        batch_upsert.append(prices)
        updated += 1
    else:
        errors += 1

    # Upsert par batch
    if len(batch_upsert) >= BATCH_SIZE:
        try:
            sb.table('prices').upsert(batch_upsert, on_conflict='card_id').execute()
        except Exception as e:
            print(f"Erreur batch upsert: {str(e)[:80]}")
        batch_upsert = []

    if (i+1) % 100 == 0:
        elapsed = (datetime.now(timezone.utc) - start_time).seconds // 60
        print(f"{i+1}/{len(to_update)} — {updated} mis a jour | {errors} erreurs | {elapsed}min ecoulees")

# Flush dernier batch
if batch_upsert:
    try:
        sb.table('prices').upsert(batch_upsert, on_conflict='card_id').execute()
    except Exception as e:
        print(f"Erreur flush final: {str(e)[:80]}")

elapsed_total = (datetime.now(timezone.utc) - start_time).seconds // 60
print(f"TERMINE: {updated} mis a jour | {errors} erreurs | {skipped_timeout} reportees | {elapsed_total}min")
