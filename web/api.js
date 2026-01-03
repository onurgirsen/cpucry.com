/**
 * api.js - Polymarket and Yahoo Finance API functions
 * Pure frontend - no backend required
 */

// API Endpoints with CORS proxy
const CORS_PROXY = 'https://corsproxy.io/?';
const GAMMA_API_BASE = 'https://gamma-api.polymarket.com';
const CLOB_API_BASE = 'https://clob.polymarket.com';
const YAHOO_API_BASE = 'https://query1.finance.yahoo.com';

// Events to track
const EVENTS = [
    { slug: 'nvda-above-in-january-2026', ticker: 'NVDA' },
    { slug: 'aapl-above-in-january-2026', ticker: 'AAPL' },
    { slug: 'nflx-above-in-january-2026', ticker: 'NFLX' },
    { slug: 'open-above-in-january-2026', ticker: 'OPEN' },
    { slug: 'googl-above-in-january-2026', ticker: 'GOOGL' },
    { slug: 'amzn-above-in-january-2026', ticker: 'AMZN' },
    { slug: 'msft-above-in-january-2026', ticker: 'MSFT' },
    { slug: 'pltr-above-in-january-2026', ticker: 'PLTR' },
    { slug: 'tsla-above-in-january-2026', ticker: 'TSLA' },
    { slug: 'meta-above-in-january-2026', ticker: 'META' },
    { slug: 'gc-over-under-jan-2026', ticker: 'GC=F' },
    { slug: 'si-over-under-jan-2026', ticker: 'SI=F' },
    { slug: 'cl-over-under-jan-2026', ticker: 'CL=F' }
];

// Company configuration
const COMPANIES = {
    'NVDA': { dividendYield: 0.0004, defaultVolatility: 0.45, defaultPrice: 135.00 },
    'AAPL': { dividendYield: 0.005, defaultVolatility: 0.25, defaultPrice: 240.00 },
    'NFLX': { dividendYield: 0.0, defaultVolatility: 0.40, defaultPrice: 900.00 },
    'OPEN': { dividendYield: 0.0, defaultVolatility: 0.80, defaultPrice: 5.00 },
    'GOOGL': { dividendYield: 0.005, defaultVolatility: 0.30, defaultPrice: 190.00 },
    'AMZN': { dividendYield: 0.0, defaultVolatility: 0.35, defaultPrice: 220.00 },
    'MSFT': { dividendYield: 0.008, defaultVolatility: 0.25, defaultPrice: 430.00 },
    'PLTR': { dividendYield: 0.0, defaultVolatility: 0.60, defaultPrice: 75.00 },
    'TSLA': { dividendYield: 0.0, defaultVolatility: 0.55, defaultPrice: 400.00 },
    'META': { dividendYield: 0.004, defaultVolatility: 0.35, defaultPrice: 590.00 },
    'GC=F': { dividendYield: 0.0, defaultVolatility: 0.15, defaultPrice: 2650.00 },
    'SI=F': { dividendYield: 0.0, defaultVolatility: 0.25, defaultPrice: 30.00 },
    'CL=F': { dividendYield: 0.0, defaultVolatility: 0.35, defaultPrice: 75.00 }
};

// Resolution date: January 30, 2026 4PM ET
const RESOLUTION_DATE = new Date('2026-01-30T16:00:00-05:00');
const RISK_FREE_RATE = 0.045;
const TRADING_DAYS_PER_YEAR = 252;

/**
 * Fetch event data from Polymarket Gamma API
 */
async function fetchEventData(eventSlug) {
    try {
        const url = CORS_PROXY + encodeURIComponent(`${GAMMA_API_BASE}/events?slug=${eventSlug}`);
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        return data[0] || null;
    } catch (error) {
        console.error(`Error fetching event ${eventSlug}:`, error);
        return null;
    }
}

/**
 * Fetch order book from Polymarket CLOB API
 */
async function fetchOrderBook(tokenId) {
    try {
        const url = CORS_PROXY + encodeURIComponent(`${CLOB_API_BASE}/book?token_id=${tokenId}`);
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error(`Error fetching orderbook:`, error);
        return null;
    }
}

/**
 * Fetch stock price from Yahoo Finance via CORS proxy
 */
async function fetchStockPrice(ticker) {
    try {
        const yahooUrl = `${YAHOO_API_BASE}/v8/finance/chart/${ticker}?interval=1d&range=1d`;
        const url = CORS_PROXY + encodeURIComponent(yahooUrl);
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        const result = data?.chart?.result?.[0];
        if (!result) return null;

        return result.meta?.regularMarketPrice || null;
    } catch (error) {
        console.error(`Error fetching stock price for ${ticker}:`, error);
        return null;
    }
}

/**
 * Fetch historical volatility from Yahoo Finance
 */
async function fetchHistoricalVolatility(ticker) {
    try {
        const yahooUrl = `${YAHOO_API_BASE}/v8/finance/chart/${ticker}?interval=1d&range=3mo`;
        const url = CORS_PROXY + encodeURIComponent(yahooUrl);
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        const closes = data?.chart?.result?.[0]?.indicators?.quote?.[0]?.close || [];

        if (closes.length < 20) return null;

        // Calculate daily returns
        const returns = [];
        for (let i = 1; i < closes.length; i++) {
            if (closes[i] && closes[i - 1] && closes[i - 1] > 0) {
                returns.push((closes[i] - closes[i - 1]) / closes[i - 1]);
            }
        }

        if (returns.length < 20) return null;

        // Calculate standard deviation
        const mean = returns.reduce((a, b) => a + b, 0) / returns.length;
        const variance = returns.reduce((sum, r) => sum + Math.pow(r - mean, 2), 0) / (returns.length - 1);
        const dailyVol = Math.sqrt(variance);

        // Annualize
        return dailyVol * Math.sqrt(252);
    } catch (error) {
        console.error(`Error calculating volatility for ${ticker}:`, error);
        return null;
    }
}

/**
 * Analyze order book to get best bid/ask
 */
function analyzeOrderBook(orderBook) {
    if (!orderBook) return null;

    const bids = orderBook.bids || [];
    const asks = orderBook.asks || [];

    const bidsSorted = [...bids].sort((a, b) => parseFloat(b.price) - parseFloat(a.price));
    const asksSorted = [...asks].sort((a, b) => parseFloat(a.price) - parseFloat(b.price));

    const bestBid = bidsSorted.length > 0 ? parseFloat(bidsSorted[0].price) : 0;
    const bestAsk = asksSorted.length > 0 ? parseFloat(asksSorted[0].price) : 1;

    const totalBidLiquidity = bids.reduce((sum, b) => sum + parseFloat(b.size), 0);
    const totalAskLiquidity = asks.reduce((sum, a) => sum + parseFloat(a.size), 0);

    return {
        best_bid: bestBid,
        best_ask: bestAsk,
        spread: bestAsk - bestBid,
        total_bid_liquidity: totalBidLiquidity,
        total_ask_liquidity: totalAskLiquidity
    };
}

/**
 * Extract strike price from question text
 */
function extractStrikePrice(question) {
    const match = question.match(/\$?([\d,]+(?:\.\d+)?)/);
    if (match) {
        return parseFloat(match[1].replace(',', ''));
    }
    return null;
}

/**
 * Get time to expiry in years
 */
function getTimeToExpiry() {
    const now = new Date();
    const calendarDays = (RESOLUTION_DATE - now) / (24 * 3600 * 1000);
    const tradingDays = calendarDays * (5 / 7);
    return Math.max(tradingDays / TRADING_DAYS_PER_YEAR, 0.001);
}

// Export for use in other modules
window.API = {
    EVENTS,
    COMPANIES,
    RISK_FREE_RATE,
    fetchEventData,
    fetchOrderBook,
    fetchStockPrice,
    fetchHistoricalVolatility,
    analyzeOrderBook,
    extractStrikePrice,
    getTimeToExpiry
};
