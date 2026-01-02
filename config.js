/**
 * Configuration for Polymarket Dashboard
 */

const CONFIG = {
    // API Endpoints
    GAMMA_API: 'https://gamma-api.polymarket.com',
    CLOB_API: 'https://clob.polymarket.com',
    YAHOO_API: 'https://query1.finance.yahoo.com/v8/finance/chart',

    // CORS Proxy - Required for browser-based API access
    // corsproxy.io is a free public CORS proxy
    CORS_PROXY: 'https://corsproxy.io/?',

    // Timing
    AUTO_REFRESH_MS: 30000,  // 30 seconds

    // Market Resolution Date: January 30, 2026 4PM ET
    RESOLUTION_DATE: new Date('2026-01-30T21:00:00Z'),  // UTC time

    // Financial Parameters
    RISK_FREE_RATE: 0.045,  // 4.5% (1-month T-Bill rate)
    TRADING_DAYS_PER_YEAR: 252,

    // Companies to track
    COMPANIES: {
        'NVDA': {
            name: 'NVIDIA Corporation',
            icon: '🟢',
            slug: 'nvda-above-in-january-2026',
            dividendYield: 0.0004,
            defaultVolatility: 0.45,
            defaultPrice: 135.00
        },
        'AAPL': {
            name: 'Apple Inc.',
            icon: '🍎',
            slug: 'aapl-above-in-january-2026',
            dividendYield: 0.005,
            defaultVolatility: 0.25,
            defaultPrice: 240.00
        },
        'NFLX': {
            name: 'Netflix Inc.',
            icon: '🎬',
            slug: 'nflx-above-in-january-2026',
            dividendYield: 0.0,
            defaultVolatility: 0.40,
            defaultPrice: 900.00
        },
        'OPEN': {
            name: 'Opendoor Technologies',
            icon: '🏠',
            slug: 'open-above-in-january-2026',
            dividendYield: 0.0,
            defaultVolatility: 0.80,
            defaultPrice: 5.00
        },
        'GOOGL': {
            name: 'Alphabet Inc.',
            icon: '🔍',
            slug: 'googl-above-in-january-2026',
            dividendYield: 0.005,
            defaultVolatility: 0.30,
            defaultPrice: 190.00
        },
        'AMZN': {
            name: 'Amazon.com',
            icon: '📦',
            slug: 'amzn-above-in-january-2026',
            dividendYield: 0.0,
            defaultVolatility: 0.35,
            defaultPrice: 220.00
        },
        'MSFT': {
            name: 'Microsoft Corp.',
            icon: '🪟',
            slug: 'msft-above-in-january-2026',
            dividendYield: 0.008,
            defaultVolatility: 0.25,
            defaultPrice: 430.00
        },
        'PLTR': {
            name: 'Palantir Technologies',
            icon: '🔮',
            slug: 'pltr-above-in-january-2026',
            dividendYield: 0.0,
            defaultVolatility: 0.60,
            defaultPrice: 75.00
        },
        'TSLA': {
            name: 'Tesla Inc.',
            icon: '⚡',
            slug: 'tsla-above-in-january-2026',
            dividendYield: 0.0,
            defaultVolatility: 0.55,
            defaultPrice: 400.00
        }
    }
};

// Export for use in other modules
window.CONFIG = CONFIG;
