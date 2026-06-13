// api/price.js — Vercel serverless function
// Proxy PriceCharting API pour éviter les restrictions CORS
// Route : GET /api/price?name=Mewtwo&set=base1&game=pokemon

const PC_TOKEN = process.env.PC_TOKEN; // Variable d'environnement Vercel

export default async function handler(req, res) {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET');

  const { name, set, game = 'pokemon' } = req.query;

  if (!name) {
    return res.status(400).json({ error: 'Missing name parameter' });
  }

  try {
    const isOnepiece = game === 'onepiece';
    const gameKeyword = isOnepiece ? 'One Piece Card Game' : 'Pokemon';
    const base = set ? set.split('_')[0] : '';

    // Recherche EN
    const queryEN = `${name} ${base} ${gameKeyword}`.trim();
    const searchEN = await fetch(
      `https://www.pricecharting.com/api/products?q=${encodeURIComponent(queryEN)}&t=${PC_TOKEN}&status=price`,
      { headers: { 'User-Agent': 'Nakama/1.0' } }
    );
    const dataEN = await searchEN.json();
    const productsEN = dataEN.products || [];

    // EN = pas japonais
    const enProduct = productsEN.find(p => !p['console-name']?.includes('Japanese'));
    // JP = japonais
    const jpProduct = productsEN.find(p => p['console-name']?.includes('Japanese'));

    const result = {
      price_en_usd: null,
      price_en_graded_usd: null,
      price_jp_usd: null,
      price_jp_graded_usd: null,
      source: 'PriceCharting',
    };

    // Fetch prix EN
    if (enProduct?.id) {
      const detailEN = await fetch(
        `https://www.pricecharting.com/api/product?id=${enProduct.id}&t=${PC_TOKEN}`,
        { headers: { 'User-Agent': 'Nakama/1.0' } }
      );
      const dEN = await detailEN.json();
      const c = v => (v && v > 0) ? Math.round(v) / 100 : null;
      result.price_en_usd = c(dEN['loose-price']);
      result.price_en_graded_usd = c(dEN['condition-17-price']); // PSA 9
    }

    // Fetch prix JP
    if (jpProduct?.id) {
      const detailJP = await fetch(
        `https://www.pricecharting.com/api/product?id=${jpProduct.id}&t=${PC_TOKEN}`,
        { headers: { 'User-Agent': 'Nakama/1.0' } }
      );
      const dJP = await detailJP.json();
      const c = v => (v && v > 0) ? Math.round(v) / 100 : null;
      result.price_jp_usd = c(dJP['loose-price']);
      result.price_jp_graded_usd = c(dJP['condition-17-price']);
    }

    // Cache 24h côté Vercel CDN
    res.setHeader('Cache-Control', 's-maxage=86400, stale-while-revalidate');
    return res.status(200).json(result);

  } catch (err) {
    console.error('PriceCharting error:', err);
    return res.status(500).json({ error: 'Failed to fetch price' });
  }
}
