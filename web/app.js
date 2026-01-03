/**
 * app.js - Main Application Logic
 * Pure Frontend Polymarket Dashboard
 */

// Company display info
const COMPANY_INFO = {
    'nvda': { ticker: 'NVDA', name: 'NVIDIA Corporation', icon: '🟢', category: 'stock' },
    'aapl': { ticker: 'AAPL', name: 'Apple Inc.', icon: '🍎', category: 'stock' },
    'nflx': { ticker: 'NFLX', name: 'Netflix Inc.', icon: '🎬', category: 'stock' },
    'open': { ticker: 'OPEN', name: 'Opendoor Technologies', icon: '🏠', category: 'stock' },
    'googl': { ticker: 'GOOGL', name: 'Alphabet Inc.', icon: '🔍', category: 'stock' },
    'amzn': { ticker: 'AMZN', name: 'Amazon.com', icon: '📦', category: 'stock' },
    'msft': { ticker: 'MSFT', name: 'Microsoft Corp.', icon: '🪟', category: 'stock' },
    'pltr': { ticker: 'PLTR', name: 'Palantir Technologies', icon: '🔮', category: 'stock' },
    'tsla': { ticker: 'TSLA', name: 'Tesla Inc.', icon: '⚡', category: 'stock' },
    'meta': { ticker: 'META', name: 'Meta Platforms', icon: '👤', category: 'stock' },
    'gc': { ticker: 'GC', name: 'Gold Futures', icon: '🥇', category: 'commodity' },
    'si': { ticker: 'SI', name: 'Silver Futures', icon: '🥈', category: 'commodity' },
    'cl': { ticker: 'CL', name: 'Crude Oil Futures', icon: '🛢️', category: 'commodity' }
};

// State
let marketData = [];
let stockDataCache = {};
let selectedCompany = null;
let currentView = 'home';
let isRefreshing = false;
let currentSort = { column: null, direction: 'desc' };
let lastOpportunitiesData = [];

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    showLoading(true);
    await fetchAllData();
    renderCompanyList();
    showTopOpportunities();
    updateLastUpdated();
    startAutoRefresh();
    showLoading(false);
});

function showLoading(show) {
    const loader = document.getElementById('loading');
    if (loader) {
        loader.style.display = show ? 'flex' : 'none';
    }
}

// Fetch all data from APIs
async function fetchAllData() {
    console.log('Fetching all data...');
    const startTime = Date.now();

    // Fetch stock prices and volatility in parallel
    const tickers = [...new Set(API.EVENTS.map(e => e.ticker))];
    const stockPromises = tickers.map(async ticker => {
        const [price, volatility] = await Promise.all([
            API.fetchStockPrice(ticker),
            API.fetchHistoricalVolatility(ticker)
        ]);

        const config = API.COMPANIES[ticker] || {};
        stockDataCache[ticker] = {
            ticker,
            currentPrice: price || config.defaultPrice,
            volatility: volatility || config.defaultVolatility,
            dividendYield: config.dividendYield || 0,
            timeToExpiry: API.getTimeToExpiry(),
            riskFreeRate: API.RISK_FREE_RATE
        };
    });

    await Promise.all(stockPromises);
    console.log('Stock data fetched');

    // Fetch all events in parallel
    const eventPromises = API.EVENTS.map(async eventConfig => {
        const event = await API.fetchEventData(eventConfig.slug);
        if (!event) return null;

        const stockInfo = stockDataCache[eventConfig.ticker];
        const markets = event.markets || [];

        // Fetch orderbooks for all markets
        const marketResults = await Promise.all(markets.map(async market => {
            try {
                let prices = market.outcomePrices || '[]';
                if (typeof prices === 'string') prices = JSON.parse(prices);

                let tokens = market.clobTokenIds || '[]';
                if (typeof tokens === 'string') tokens = JSON.parse(tokens);

                const question = market.question || 'Unknown';
                const strikePrice = API.extractStrikePrice(question);

                const result = {
                    question,
                    strike_price: strikePrice,
                    yes_probability: prices[0] ? parseFloat(prices[0]) : null,
                    no_probability: prices[1] ? parseFloat(prices[1]) : null
                };

                // Calculate Black-Scholes
                if (strikePrice && stockInfo) {
                    const bs = BlackScholes.calculateFairValue(strikePrice, stockInfo);
                    if (bs) {
                        result.bs_fair_value = bs.price;
                        result.bs_probability = bs.probability;
                        if (result.yes_probability) {
                            result.edge_vs_market = bs.price - result.yes_probability;
                        }
                    }
                }

                // Fetch orderbook
                if (tokens.length >= 1) {
                    result.yes_token_id = tokens[0];
                    if (tokens.length >= 2) result.no_token_id = tokens[1];

                    const book = await API.fetchOrderBook(tokens[0]);
                    const analysis = API.analyzeOrderBook(book);
                    if (analysis) {
                        result.yes_orderbook = analysis;
                        if (result.bs_fair_value) {
                            result.edge_vs_bid = result.bs_fair_value - analysis.best_bid;
                            result.edge_vs_ask = result.bs_fair_value - analysis.best_ask;
                        }
                    }
                }

                return result;
            } catch (e) {
                console.error('Error processing market:', e);
                return null;
            }
        }));

        return {
            event_slug: eventConfig.slug,
            event_title: event.title || eventConfig.slug,
            stock_data: stockInfo,
            markets: marketResults.filter(m => m !== null)
        };
    });

    const results = await Promise.all(eventPromises);
    marketData = results.filter(r => r !== null);

    console.log(`Data fetched in ${(Date.now() - startTime) / 1000}s`);
}

// Manual refresh
async function manualRefresh() {
    if (isRefreshing) return;

    const btn = document.querySelector('.refresh-btn');
    btn.classList.add('loading');
    btn.disabled = true;
    isRefreshing = true;

    try {
        showLoading(true);
        await fetchAllData();
        renderCompanyList();

        if (currentView === 'home') {
            showTopOpportunities();
        } else if (selectedCompany) {
            const updated = marketData.find(e => e.event_slug === selectedCompany.event_slug);
            if (updated) selectCompany(updated);
        }

        updateLastUpdated();
    } catch (error) {
        console.error('Refresh error:', error);
    } finally {
        showLoading(false);
        isRefreshing = false;
        btn.classList.remove('loading');
        btn.disabled = false;
    }
}

// Auto refresh every 60 seconds
function startAutoRefresh() {
    setInterval(async () => {
        if (!isRefreshing) {
            await fetchAllData();
            if (currentView === 'home') {
                showTopOpportunities();
            }
            updateLastUpdated();
        }
    }, 60000);
}

function updateLastUpdated() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString();
    document.getElementById('lastUpdated').textContent = `Updated: ${timeStr}`;
}

// Extract ticker from slug
function extractTicker(slug) {
    const stockMatch = slug.match(/^([a-z]+)-above/);
    if (stockMatch) return stockMatch[1];

    const commodityMatch = slug.match(/^([a-z]+)-over-under/);
    if (commodityMatch) return commodityMatch[1];

    return slug.split('-')[0];
}

// Render company list with categories
function renderCompanyList() {
    const container = document.getElementById('companyList');
    container.innerHTML = '';

    const stockEvents = [];
    const commodityEvents = [];

    for (const event of marketData) {
        const ticker = extractTicker(event.event_slug);
        const info = COMPANY_INFO[ticker] || { ticker: ticker.toUpperCase(), name: 'Unknown', icon: '📊', category: 'stock' };

        if (info.category === 'commodity') {
            commodityEvents.push({ event, ticker, info });
        } else {
            stockEvents.push({ event, ticker, info });
        }
    }

    // Stock Markets section
    if (stockEvents.length > 0) {
        const header = document.createElement('h3');
        header.className = 'sidebar-section-header';
        header.innerHTML = '📈 Stock Markets';
        container.appendChild(header);

        for (const { event, info } of stockEvents) {
            container.appendChild(createCompanyItem(event, info));
        }
    }

    // Commodity Markets section
    if (commodityEvents.length > 0) {
        const header = document.createElement('h3');
        header.className = 'sidebar-section-header';
        header.innerHTML = '🏆 Commodity Markets';
        container.appendChild(header);

        for (const { event, info } of commodityEvents) {
            container.appendChild(createCompanyItem(event, info));
        }
    }
}

function createCompanyItem(event, info) {
    const item = document.createElement('div');
    item.className = 'company-item';
    item.dataset.slug = event.event_slug;

    item.innerHTML = `
        <div class="company-icon">${info.icon}</div>
        <div class="company-info">
            <div class="company-ticker">${info.ticker}</div>
            <div class="company-name">${info.name}</div>
        </div>
        <div class="company-markets-count">${event.markets.length}</div>
    `;

    item.addEventListener('click', () => selectCompany(event));
    return item;
}

// Show home page with top opportunities
function showTopOpportunities() {
    currentView = 'home';
    selectedCompany = null;

    document.querySelectorAll('.company-item').forEach(item => item.classList.remove('active'));

    document.getElementById('companyTitle').textContent = 'Top Opportunities';
    document.getElementById('companySubtitle').textContent = 'Best risk-adjusted returns across all markets';

    // Collect all opportunities
    const opportunities = [];
    for (const event of marketData) {
        const ticker = extractTicker(event.event_slug);
        const info = COMPANY_INFO[ticker] || { ticker: ticker.toUpperCase(), icon: '📊' };

        for (const market of event.markets) {
            if (market.bs_fair_value && market.yes_orderbook) {
                const askPrice = market.yes_orderbook.best_ask;
                const bsProb = market.bs_probability;
                const marketProb = askPrice;

                // Kelly Criterion
                const edge = bsProb - marketProb;
                const odds = (1 - askPrice) / askPrice;
                const kelly = edge > 0 ? (edge / (1 / odds)) * 100 : 0;

                // ROI calculation
                const potentialReturn = 1 - askPrice;
                const roi = (bsProb * potentialReturn - (1 - bsProb) * askPrice) * 100;

                opportunities.push({
                    ticker: info.ticker,
                    icon: info.icon,
                    strike: market.strike_price,
                    bsProb: bsProb * 100,
                    marketProb: marketProb * 100,
                    askPrice,
                    roi,
                    kelly,
                    edge: edge * 100
                });
            }
        }
    }

    // Sort and render
    const sorted = sortOpportunities(opportunities);
    renderTopOpportunitiesTable(sorted);
    lastOpportunitiesData = sorted;
}

function sortOpportunities(data) {
    if (!currentSort.column) {
        return data.sort((a, b) => b.roi - a.roi);
    }

    return [...data].sort((a, b) => {
        let valA, valB;
        switch (currentSort.column) {
            case 'strike': valA = a.strike; valB = b.strike; break;
            case 'yesProb': valA = a.marketProb; valB = b.marketProb; break;
            case 'roi': valA = a.roi; valB = b.roi; break;
            case 'kelly': valA = a.kelly; valB = b.kelly; break;
            default: return 0;
        }
        return currentSort.direction === 'asc' ? valA - valB : valB - valA;
    });
}

function renderTopOpportunitiesTable(opportunities) {
    const thead = document.getElementById('marketTableHead');
    const tbody = document.getElementById('marketTableBody');

    const getSortIndicator = (col) => {
        if (currentSort.column !== col) return ' <span class="sort-indicator">⇵</span>';
        return currentSort.direction === 'asc'
            ? ' <span class="sort-indicator sort-asc">↑</span>'
            : ' <span class="sort-indicator sort-desc">↓</span>';
    };

    thead.innerHTML = `
        <th>Company</th>
        <th class="sortable" data-sort="strike">Strike${getSortIndicator('strike')}</th>
        <th>BS Prob (YES)</th>
        <th class="sortable" data-sort="yesProb">Market YES${getSortIndicator('yesProb')}</th>
        <th class="sortable" data-sort="roi">ROI (1$)${getSortIndicator('roi')}</th>
        <th class="sortable" data-sort="kelly">Kelly %${getSortIndicator('kelly')}</th>
    `;

    // Add sort click handlers
    thead.querySelectorAll('.sortable').forEach(th => {
        th.addEventListener('click', () => {
            const col = th.dataset.sort;
            if (currentSort.column === col) {
                currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
            } else {
                currentSort.column = col;
                currentSort.direction = 'desc';
            }
            showTopOpportunities();
        });
    });

    tbody.innerHTML = opportunities.map(opp => {
        const roiClass = opp.roi > 0 ? 'positive' : 'negative';
        const kellyClass = opp.kelly > 0 ? 'positive' : '';
        const edgeClass = opp.edge > 0 ? 'positive' : 'negative';

        return `
            <tr>
                <td class="company-cell">${opp.icon} ${opp.ticker}</td>
                <td>$${opp.strike.toLocaleString()}</td>
                <td>${opp.bsProb.toFixed(1)}%</td>
                <td>${opp.marketProb.toFixed(1)}%</td>
                <td class="${roiClass}">${opp.roi >= 0 ? '+' : ''}${opp.roi.toFixed(2)}%</td>
                <td class="${kellyClass}">${opp.kelly.toFixed(1)}%</td>
            </tr>
        `;
    }).join('');

    // Update stats
    document.getElementById('totalMarkets').textContent = opportunities.length;
    document.getElementById('currentPrice').textContent = '-';
    document.getElementById('volatility').textContent = '-';
}

// Select and show a specific company
function selectCompany(event) {
    currentView = 'company';
    selectedCompany = event;

    document.querySelectorAll('.company-item').forEach(item => {
        item.classList.toggle('active', item.dataset.slug === event.event_slug);
    });

    const ticker = extractTicker(event.event_slug);
    const info = COMPANY_INFO[ticker] || { ticker: ticker.toUpperCase(), name: 'Unknown', icon: '📊' };

    document.getElementById('companyTitle').textContent = `${info.icon} ${info.ticker} - ${info.name}`;
    document.getElementById('companySubtitle').textContent = event.event_title;

    renderCompanyMarkets(event);
}

function renderCompanyMarkets(event) {
    const thead = document.getElementById('marketTableHead');
    const tbody = document.getElementById('marketTableBody');

    thead.innerHTML = `
        <th>Strike</th>
        <th>BS Prob (NO)</th>
        <th colspan="2" class="col-group-header">Buy YES</th>
        <th colspan="2" class="col-group-header">Buy NO</th>
        <th>Market YES</th>
        <th>ROI (1$)</th>
        <th>Kelly %</th>
    `;

    const markets = event.markets.sort((a, b) => (a.strike_price || 0) - (b.strike_price || 0));

    tbody.innerHTML = markets.map(market => {
        if (!market.strike_price) return '';

        const bsProb = market.bs_probability || 0;
        const noProb = (1 - bsProb) * 100;
        const yesProb = (market.yes_probability || 0) * 100;

        let askPrice = '-', bidPrice = '-', roi = 0, kelly = 0;

        if (market.yes_orderbook) {
            askPrice = market.yes_orderbook.best_ask.toFixed(3);
            bidPrice = market.yes_orderbook.best_bid.toFixed(3);

            const ask = market.yes_orderbook.best_ask;
            const potentialReturn = 1 - ask;
            roi = (bsProb * potentialReturn - (1 - bsProb) * ask) * 100;

            const edge = bsProb - ask;
            const odds = (1 - ask) / ask;
            kelly = edge > 0 ? (edge / (1 / odds)) * 100 : 0;
        }

        const roiClass = roi > 0 ? 'positive' : 'negative';
        const kellyClass = kelly > 0 ? 'positive' : '';

        return `
            <tr>
                <td>$${market.strike_price.toLocaleString()}</td>
                <td>${noProb.toFixed(1)}%</td>
                <td class="col-ask">${askPrice}</td>
                <td class="edge-cell ${market.edge_vs_ask > 0 ? 'positive' : 'negative'}">
                    ${market.edge_vs_ask ? (market.edge_vs_ask * 100).toFixed(1) + '%' : '-'}
                </td>
                <td class="col-bid">${bidPrice}</td>
                <td class="edge-cell ${market.edge_vs_bid > 0 ? 'positive' : 'negative'}">
                    ${market.edge_vs_bid ? (market.edge_vs_bid * 100).toFixed(1) + '%' : '-'}
                </td>
                <td>${yesProb.toFixed(1)}%</td>
                <td class="${roiClass}">${roi >= 0 ? '+' : ''}${roi.toFixed(2)}%</td>
                <td class="${kellyClass}">${kelly.toFixed(1)}%</td>
            </tr>
        `;
    }).join('');

    // Update stats
    document.getElementById('totalMarkets').textContent = markets.length;

    if (event.stock_data) {
        const sd = event.stock_data;
        document.getElementById('currentPrice').textContent = sd.currentPrice ? `$${sd.currentPrice.toFixed(2)}` : '-';
        document.getElementById('volatility').textContent = sd.volatility ? `${(sd.volatility * 100).toFixed(1)}%` : '-';
    }
}

// Make functions globally available
window.manualRefresh = manualRefresh;
window.showTopOpportunities = showTopOpportunities;
