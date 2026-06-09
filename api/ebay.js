export const config = { runtime: 'edge' };

export default async function handler(req) {
  const { searchParams } = new URL(req.url);
  const keywords = searchParams.get('keywords');
  
  if (!keywords) {
    return new Response(JSON.stringify({ error: 'Missing keywords' }), {
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
    });
  }

  const EBAY_APP_ID = 'Bricefor-OPItem-PRD-0995efe7b-e9e35dbd';
  const url = `https://svcs.ebay.com/services/search/FindingService/v1?OPERATION-NAME=findCompletedItems&SERVICE-VERSION=1.0.0&SECURITY-APPNAME=${EBAY_APP_ID}&RESPONSE-DATA-FORMAT=JSON&keywords=${encodeURIComponent(keywords)}&itemFilter(0).name=SoldItemsOnly&itemFilter(0).value=true&sortOrder=EndTimeSoonest&paginationInput.entriesPerPage=5`;

  try {
    const response = await fetch(url);
    const text = await response.text();
    const data = JSON.parse(text);
    const items = data?.findCompletedItemsResponse?.[0]?.searchResult?.[0]?.item || [];
    
    const sales = items.map(item => ({
      title: item.title?.[0],
      price: item.sellingStatus?.[0]?.currentPrice?.[0]?.__value__,
      currency: item.sellingStatus?.[0]?.currentPrice?.[0]?.['@currencyId'],
      date: item.listingInfo?.[0]?.endTime?.[0],
      url: item.viewItemURL?.[0]
    }));
    
    return new Response(JSON.stringify({ sales }), {
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: err.message, raw: err.toString() }), {
      headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' }
    });
  }
}
