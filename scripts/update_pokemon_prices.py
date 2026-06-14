import requests, time, os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from supabase import create_client

SB_URL = os.environ['SB_URL']
SB_KEY = os.environ['SB_KEY']
sb = create_client(SB_URL, SB_KEY)

# Session avec retry automatique sur les erreurs réseau
session = requests.Session()
retry = Retry(total=3, backoff_factor=3, status_forcelist=[500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retry))

print("Demarrage mise a jour prix Pokemon...")

all_cards = []
page = 1
while True:
    for attempt in range(5):
        try:
            r = session.get("https://api.pokemontcg.io/v2/cards", params={
                'page': page, 'pageSize': 250,
                'select': 'id,tcgplayer,cardmarket'
            }, timeout=90)
            data = r.json()
            break
        except Exception as e:
            wait = 10 * (attempt + 1)
            print(f"Retry page {page} attempt {attempt+1} - wait {wait}s - {str(e)[:60]}")
            time.sleep(wait)
    else:
        print("Page", page, "failed after 5 attempts, stopping")
        break
    cards = data.get('data', [])
    if not cards:
        break
    all_cards.extend(cards)
    total = data.get('totalCount', 0)
    print("Page", page, "-", len(all_cards), "/", total)
    if len(all_cards) >= total:
        break
    page += 1
    time.sleep(0.3)

print("Total cartes:", len(all_cards))

injected = 0
no_price = 0

for i in range(0, len(all_cards), 100):
    batch = all_cards[i:i+100]
    rows = []
    for c in batch:
        tcg = c.get('tcgplayer', {}).get('prices', {})
        cm  = c.get('cardmarket', {}).get('prices', {})
        prices = (tcg.get('normal') or tcg.get('holofoil') or
                  tcg.get('reverseHolofoil') or tcg.get('1stEditionHolofoil') or {})
        low    = prices.get('low')
        mid    = prices.get('mid')
        market = prices.get('market')
        cm_avg = cm.get('averageSellPrice') or cm.get('avg1')

        if low or mid or market:
            rows.append({
                'card_id':          c['id'],
                'price_usd':        market,
                'price_eur':        round(cm_avg, 2) if cm_avg else None,
                'price_low_usd':    low,
                'price_mid_usd':    mid,
                'price_market_usd': market,
            })
            injected += 1
        else:
            no_price += 1

    if rows:
        try:
            sb.table('prices').upsert(rows, on_conflict='card_id').execute()
        except Exception as e:
            print("Erreur batch", i, str(e)[:80])

    if (i // 100 + 1) % 20 == 0:
        print(injected, "injectes |", no_price, "sans prix")

print("TERMINE:", injected, "injectes |", no_price, "sans prix")
