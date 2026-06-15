import os, time
from datetime import date
from supabase import create_client

SB_URL = os.environ['SB_URL']
SB_SERVICE_KEY = os.environ['SB_SERVICE_KEY']
sb = create_client(SB_URL, SB_SERVICE_KEY)

today = date.today().isoformat()
print(f"Snapshot prix Pokémon — {today}")

offset = 0
batch_size = 1000
inserted = 0
skipped = 0

while True:
    res = sb.table('prices').select('card_id,price_market_usd,price_eur').range(offset, offset + batch_size - 1).execute()
    rows = res.data
    if not rows:
        break

    snapshot_rows = []
    for r in rows:
        if r.get('price_market_usd') or r.get('price_eur'):
            snapshot_rows.append({
                'card_id': r['card_id'],
                'recorded_at': today,
                'price_market_usd': r.get('price_market_usd'),
                'price_eur': r.get('price_eur'),
            })
            inserted += 1
        else:
            skipped += 1

    if snapshot_rows:
        for i in range(0, len(snapshot_rows), 500):
            batch = snapshot_rows[i:i+500]
            try:
                sb.table('price_history').upsert(batch, on_conflict='card_id,recorded_at').execute()
            except Exception as e:
                print(f"Erreur batch {i}: {str(e)[:80]}")

    print(f"Offset {offset}: {len(rows)} prix traités")
    offset += batch_size
    if len(rows) < batch_size:
        break

print(f"TERMINE: {inserted} snapshots insérés | {skipped} sans prix")
