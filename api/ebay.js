export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET');
  
  const { keywords } = req.query;
  if (!keywords) return res.status(400).json({ error: 'Missing keywords' });

  const EBAY_APP_ID = 'Bricefor-OPItem-PRD-0995efe7b-e9e35dbd';
  
  const url = `https://svcs.ebay.com/services/search/FindingService/v1?OPERATION-NAME=findCompletedItems&SERVICE-VERSION=1.0.0&SECURITY-APPNAME=${EBAY_APP_ID}&RESPONSE-DATA-FORMAT=JSON&keywords=${encodeURIComponent(keywords)}&itemFilter(0).name=SoldItemsOnly&itemFilter(0).value=true&itemFilter(1).name=Currency&itemFilter(1).value=EUR&sortOrder=EndTimeSoonest&paginationInput.entriesPerPage=5`;

  try {
    const response = await fetch(url);
    const data = await response.json();
    const items = data?.findCompletedItemsResponse?.[0]?.searchResult?.[0]?.item || [];
    
    const sales = items.map(item => ({
      title: item.title?.[0],
      price: item.sellingStatus?.[0]?.currentPrice?.[0]?.__value__,
      currency: item.sellingStatus?.[0]?.currentPrice?.[0]?.['@currencyId'],
      date: item.listingInfo?.[0]?.endTime?.[0],
      url: item.viewItemURL?.[0]
    }));
    
    res.status(200).json({ sales });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
}
