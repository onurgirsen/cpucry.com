/**
 * Polymarket Dashboard - Main Application
 * Standalone client-side version
 */

// State
let marketData = [];
let selectedCompany = null;
let isRefreshing = false;
let autoRefreshInterval = null;
let currentView = 'home';
let previousOpportunities = null;

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    showLoading(true);
    await loadData();
    renderCompanyList();
    showTopOpportunities();
    updateLastUpdated();
    startAutoRefresh();
    showLoading(false);
});

// Show/hide loading state
function showLoading(show) {
    const loadingState = document.getElementById('loadingState');
    const tableContainer = document.getElementById('tableContainer');

    if (loadingState) loadingState.style.display = show ? 'flex' : 'none';
    if (tableContainer) tableContainer.style.display = show ? 'none' : 'block';
}

// Start auto-refresh
function startAutoRefresh() {
    if (autoRefreshInterval) clearInterval(autoRefreshInterval);
    autoRefreshInterval = setInterval(async () => {
        await manualRefresh();
    }, CONFIG.AUTO_REFRESH_MS);
}

// Manual refresh - fetches fresh data from APIs
async function manualRefresh() {
    if (isRefreshing) return;

    isRefreshing = true;
    const btn = document.getElementById('refreshBtn');
    if (btn) {
        btn.classList.add('loading');
        btn.disabled = true;
    }

    try {
        await loadData();
        renderCompanyList();

        if (currentView === 'home') {
            showTopOpportunities();
        } else if (selectedCompany) {
            const updatedEvent = marketData.find(e => e.eventSlug === selectedCompany.eventSlug);
            if (updatedEvent) {
                selectCompany(updatedEvent);
            }
        }

        updateLastUpdated();
        console.log('Refresh complete');
    } catch (error) {
        console.error('Refresh error:', error);
    } finally {
        isRefreshing = false;
        if (btn) {
            btn.classList.remove('loading');
            btn.disabled = false;
        }
    }
}

// Load data from APIs
async function loadData() {
    try {
        marketData = await API.fetchAllData();
        console.log('Loaded market data:', marketData);
    } catch (error) {
        console.error('Error loading data:', error);
    }
}

// Render company list in sidebar
function renderCompanyList() {
    const container = document.getElementById('companyList');
    if (!container) return;

    container.innerHTML = '';

    for (const event of marketData) {
        const ticker = extractTicker(event.eventSlug);
        const info = CONFIG.COMPANIES[ticker] || { name: 'Unknown', icon: '📊' };

        const item = document.createElement('div');
        item.className = 'company-item';
        item.dataset.slug = event.eventSlug;

        item.innerHTML = `
            <div class="company-icon">${info.icon}</div>
            <div class="company-info">
                <div class="company-ticker">${ticker}</div>
                <div class="company-name">${info.name}</div>
            </div>
            <div class="company-markets-count">${event.markets.length}</div>
        `;

        item.addEventListener('click', () => selectCompany(event));
        container.appendChild(item);
    }
}

// Extract ticker from slug
function extractTicker(slug) {
    const match = slug.match(/^([a-z]+)-above/);
    return match ? match[1].toUpperCase() : slug.toUpperCase();
}

// Select a company
function selectCompany(event) {
    currentView = 'company';
    selectedCompany = event;

    // Update active state in sidebar
    document.querySelectorAll('.company-item').forEach(item => {
        item.classList.toggle('active', item.dataset.slug === event.eventSlug);
    });

    // Update header
    const ticker = extractTicker(event.eventSlug);
    const info = CONFIG.COMPANIES[ticker] || { name: 'Unknown', icon: '📊' };

    document.getElementById('companyTitle').textContent = `${info.icon} ${ticker} - ${info.name}`;
    document.getElementById('companySubtitle').textContent = event.eventTitle;

    // Show stats and table
    document.getElementById('statsGrid').style.display = 'grid';
    document.getElementById('tableContainer').style.display = 'block';
    document.getElementById('emptyState').style.display = 'none';

    // Restore company table header
    const thead = document.querySelector('#marketsTable thead tr');
    thead.innerHTML = `
        <th>Strike</th>
        <th class="bs-fair-value-header">BS Prob (NO)</th>
        <th colspan="2" class="col-group-header col-ask-header">Buy YES</th>
        <th colspan="2" class="col-group-header col-bid-header">Buy NO</th>
        <th>Market YES</th>
        <th>ROI (1$)</th>
        <th>Kelly %</th>
    `;

    updateStats(event.markets, event.stockData);
    renderMarketsTable(event.markets);
}

// Update stats cards
function updateStats(markets, stockData) {
    document.getElementById('totalMarkets').textContent = markets.length;

    if (stockData) {
        if (stockData.price) {
            document.getElementById('currentPrice').textContent = `$${stockData.price.toFixed(2)}`;
        }

        const volElement = document.getElementById('volatility');
        if (stockData.volatility) {
            volElement.textContent = `${(stockData.volatility * 100).toFixed(1)}%`;
        } else {
            volElement.textContent = 'N/A';
        }

        document.getElementById('riskFreeRate').textContent = `${(CONFIG.RISK_FREE_RATE * 100).toFixed(2)}%`;

        const T = BlackScholes.getTimeToExpiry(CONFIG.RESOLUTION_DATE);
        const days = Math.round(T * CONFIG.TRADING_DAYS_PER_YEAR);
        document.getElementById('daysToExpiry').textContent = `${days} days`;
    }
}

// Render markets table for a single company
function renderMarketsTable(markets) {
    const tbody = document.getElementById('marketsTableBody');
    tbody.innerHTML = '';

    // Sort by strike price
    const sorted = [...markets].sort((a, b) => (a.strikePrice || 0) - (b.strikePrice || 0));

    for (const market of sorted) {
        const row = document.createElement('tr');
        row.className = 'fade-in';

        const strikePrice = market.strikePrice ? `$${market.strikePrice}` : 'N/A';
        const yesProb = market.yesProbability !== null ? (market.yesProbability * 100).toFixed(1) : 'N/A';

        const ob = market.yesOrderbook;
        const bestAsk = ob?.bestAsk !== undefined ? ob.bestAsk.toFixed(3) : 'N/A';
        const bestBid = ob?.bestBid;
        const buyNoPrice = bestBid !== undefined ? (1 - bestBid) : null;
        const buyNoDisplay = buyNoPrice !== null ? buyNoPrice.toFixed(3) : 'N/A';

        // Black-Scholes values
        let bsProbHtml = 'N/A';
        let bsNoPrice = null;

        if (market.bsFairValue !== undefined && market.bsProbability !== undefined) {
            const yesPct = (market.bsProbability * 100).toFixed(2);
            const noPct = ((1 - market.bsProbability) * 100).toFixed(2);
            bsProbHtml = `<span style="color: #00b894; font-weight: 500;">${yesPct}%</span> <span style="color: #ff7675; font-size: 0.9em;">(${noPct}%)</span>`;

            let discountFactor = 1.0;
            if (market.bsProbability > 0.001) {
                discountFactor = market.bsFairValue / market.bsProbability;
            }
            bsNoPrice = discountFactor * (1 - market.bsProbability);
        }

        // ROI calculations
        let roiYes = -999, kellyYes = 0;
        if (market.bsFairValue !== undefined && ob?.bestAsk) {
            roiYes = (market.bsFairValue - ob.bestAsk) / ob.bestAsk;
            if (market.bsProbability !== undefined && roiYes > 0) {
                kellyYes = (market.bsProbability - ob.bestAsk) / (1 - ob.bestAsk);
            }
        }

        let roiNo = -999, kellyNo = 0;
        if (bsNoPrice !== null && buyNoPrice !== null && buyNoPrice > 0) {
            roiNo = (bsNoPrice - buyNoPrice) / buyNoPrice;
            if (market.bsProbability !== undefined && roiNo > 0) {
                const probNo = 1 - market.bsProbability;
                kellyNo = (probNo - buyNoPrice) / (1 - buyNoPrice);
            }
        }

        // Edge display
        let edgeAskHtml = 'N/A';
        if (market.edgeVsAsk !== undefined) {
            const edge = market.edgeVsAsk * 100;
            const edgeClass = edge < 0 ? 'edge-negative' : edge >= 1 ? 'edge-positive' : 'edge-warning';
            edgeAskHtml = `<span class="${edgeClass}">${edge >= 0 ? '+' : ''}${edge.toFixed(1)}%</span>`;
        }

        let edgeBidHtml = 'N/A';
        if (bsNoPrice !== null && bestBid !== undefined) {
            const edge = (bsNoPrice - (1 - bestBid)) * 100;
            const edgeClass = edge < 0 ? 'edge-negative' : edge >= 1 ? 'edge-positive' : 'edge-warning';
            edgeBidHtml = `<span class="${edgeClass}">${edge >= 0 ? '+' : ''}${edge.toFixed(1)}%</span>`;
        }

        // Best ROI
        let bestRoi = -999, bestKelly = 0, side = '';
        if (roiYes >= roiNo) {
            bestRoi = roiYes; bestKelly = kellyYes; side = 'YES';
        } else {
            bestRoi = roiNo; bestKelly = kellyNo; side = 'NO';
        }

        let roiHtml = 'N/A';
        let kellyHtml = '<span style="color: #b2bec3;">0%</span>';

        if (bestRoi > -999) {
            const roiPct = bestRoi * 100;
            const colorIcon = roiPct >= 0 ? '🟢' : '🔴';
            roiHtml = `${colorIcon} <strong>${side}</strong> ${roiPct >= 0 ? '+' : ''}${roiPct.toFixed(1)}%`;

            if (bestKelly > 0) {
                const displayKelly = Math.min(bestKelly * 100, 100).toFixed(1);
                kellyHtml = `<span style="font-weight: bold; color: #2d3436;">${displayKelly}%</span>`;
            }
        }

        row.innerHTML = `
            <td class="strike-price">${strikePrice}</td>
            <td class="bs-fair-value">${bsProbHtml}</td>
            <td class="ask-price col-group-start col-ask">${bestAsk}</td>
            <td class="col-group-end col-ask">${edgeAskHtml}</td>
            <td class="bid-price col-group-start col-bid">${buyNoDisplay}</td>
            <td class="col-group-end col-bid">${edgeBidHtml}</td>
            <td class="yes-prob">${yesProb}%</td>
            <td class="roi-column" style="font-weight: bold;">${roiHtml}</td>
            <td class="kelly-column">${kellyHtml}</td>
        `;

        tbody.appendChild(row);
    }
}

// Show top opportunities homepage
function showTopOpportunities() {
    currentView = 'home';
    selectedCompany = null;

    document.querySelectorAll('.company-item').forEach(item => {
        item.classList.remove('active');
    });

    document.getElementById('companyTitle').textContent = '🏆 Top Opportunities';
    document.getElementById('companySubtitle').textContent = 'Best probability-adjusted returns (ROI) across all markets';
    document.getElementById('statsGrid').style.display = 'none';
    document.getElementById('tableContainer').style.display = 'block';
    document.getElementById('emptyState').style.display = 'none';

    // Collect all opportunities
    const allOpportunities = [];

    for (const event of marketData) {
        const ticker = extractTicker(event.eventSlug);
        const info = CONFIG.COMPANIES[ticker] || { name: 'Unknown', icon: '📊' };

        for (const market of event.markets) {
            const ob = market.yesOrderbook;
            const strikePrice = market.strikePrice;

            const bestAsk = ob?.bestAsk;
            const bestBid = ob?.bestBid;
            const buyNoPrice = bestBid !== undefined ? (1 - bestBid) : null;

            let bsFairValue = market.bsFairValue;
            let bsProbability = market.bsProbability;
            let bsNoPrice = null;

            if (bsFairValue !== undefined && bsProbability !== undefined) {
                let discountFactor = 1.0;
                if (bsProbability > 0.001) {
                    discountFactor = bsFairValue / bsProbability;
                }
                bsNoPrice = discountFactor * (1 - bsProbability);
            }

            let roiYes = -999, kellyYes = 0;
            if (bsFairValue !== undefined && bestAsk) {
                roiYes = (bsFairValue - bestAsk) / bestAsk;
                if (bsProbability !== undefined && roiYes > 0) {
                    kellyYes = (bsProbability - bestAsk) / (1 - bestAsk);
                }
            }

            let roiNo = -999, kellyNo = 0;
            if (bsNoPrice !== null && buyNoPrice !== null && buyNoPrice > 0) {
                roiNo = (bsNoPrice - buyNoPrice) / buyNoPrice;
                if (bsProbability !== undefined && roiNo > 0) {
                    const probNo = 1 - bsProbability;
                    kellyNo = (probNo - buyNoPrice) / (1 - buyNoPrice);
                }
            }

            let bestRoi = -999, bestKelly = 0, side = '';
            if (roiYes >= roiNo) {
                bestRoi = roiYes; bestKelly = kellyYes; side = 'YES';
            } else {
                bestRoi = roiNo; bestKelly = kellyNo; side = 'NO';
            }

            if (bestRoi > -999) {
                allOpportunities.push({
                    ticker,
                    icon: info.icon,
                    strikePrice,
                    bsProbability,
                    bestAsk,
                    buyNoPrice,
                    roi: bestRoi,
                    roiSide: side,
                    kelly: bestKelly,
                    yesProb: market.yesProbability,
                    edgeAsk: market.edgeVsAsk !== undefined ? market.edgeVsAsk * 100 : null,
                    edgeBid: (bsNoPrice && buyNoPrice) ? (bsNoPrice - buyNoPrice) * 100 : null,
                    event
                });
            }
        }
    }

    allOpportunities.sort((a, b) => b.roi - a.roi);
    const top20 = allOpportunities.slice(0, 20);

    // Detect changes
    const changes = detectOpportunityChanges(previousOpportunities, top20);

    previousOpportunities = top20.map(opp => ({
        key: `${opp.ticker}-${opp.strikePrice}`,
        roi: opp.roi,
        bestAsk: opp.bestAsk,
        buyNoPrice: opp.buyNoPrice,
        kelly: opp.kelly
    }));

    renderTopOpportunitiesTable(top20, changes);
}

// Detect changes between previous and current opportunities
function detectOpportunityChanges(previous, current) {
    const changes = {
        newRows: new Set(),
        changedRows: new Map()
    };

    if (!previous) return changes;

    const prevMap = new Map();
    previous.forEach(opp => prevMap.set(opp.key, opp));

    current.forEach(opp => {
        const key = `${opp.ticker}-${opp.strikePrice}`;
        const prev = prevMap.get(key);

        if (!prev) {
            changes.newRows.add(key);
        } else {
            const changedFields = [];

            if (Math.abs((opp.roi - prev.roi) * 100) > 0.5) changedFields.push('roi');
            if (opp.bestAsk !== undefined && prev.bestAsk !== undefined) {
                if (Math.abs(opp.bestAsk - prev.bestAsk) > 0.001) changedFields.push('bestAsk');
            }
            if (opp.buyNoPrice !== null && prev.buyNoPrice !== null) {
                if (Math.abs(opp.buyNoPrice - prev.buyNoPrice) > 0.001) changedFields.push('buyNo');
            }
            if (Math.abs((opp.kelly - prev.kelly) * 100) > 0.5) changedFields.push('kelly');

            if (changedFields.length > 0) {
                changes.changedRows.set(key, changedFields);
            }
        }
    });

    return changes;
}

// Render top opportunities table
function renderTopOpportunitiesTable(opportunities, changes = { newRows: new Set(), changedRows: new Map() }) {
    const tbody = document.getElementById('marketsTableBody');
    const thead = document.querySelector('#marketsTable thead tr');

    thead.innerHTML = `
        <th>Company</th>
        <th>Strike</th>
        <th class="bs-fair-value-header">BS Prob (NO)</th>
        <th colspan="2" class="col-group-header col-ask-header">Buy YES</th>
        <th colspan="2" class="col-group-header col-bid-header">Buy NO</th>
        <th>Market YES</th>
        <th>ROI (1$)</th>
        <th>Kelly %</th>
    `;

    tbody.innerHTML = '';

    for (const opp of opportunities) {
        const row = document.createElement('tr');
        const key = `${opp.ticker}-${opp.strikePrice}`;

        if (changes.newRows.has(key)) {
            row.className = 'row-new';
        } else if (changes.changedRows.has(key)) {
            row.className = 'row-changed';
        } else {
            row.className = 'fade-in';
        }

        row.style.cursor = 'pointer';
        const changedFields = changes.changedRows.get(key) || [];

        row.addEventListener('click', () => selectCompany(opp.event));

        const strikePriceStr = '$' + (opp.strikePrice || 0).toLocaleString('en-US');
        const yesProb = opp.yesProb !== null ? (opp.yesProb * 100).toFixed(1) : 'N/A';

        let bsProbHtml = 'N/A';
        if (opp.bsProbability !== undefined) {
            const yesPct = (opp.bsProbability * 100).toFixed(2);
            const noPct = ((1 - opp.bsProbability) * 100).toFixed(2);
            bsProbHtml = `<span style="color: #00b894; font-weight: 500;">${yesPct}%</span> <span style="color: #ff7675; font-size: 0.9em;">(${noPct}%)</span>`;
        }

        const bestAsk = opp.bestAsk !== undefined ? opp.bestAsk.toFixed(3) : 'N/A';
        const bestAskClass = changedFields.includes('bestAsk') ? 'value-changed' : '';

        let edgeAskHtml = 'N/A';
        if (opp.edgeAsk !== null) {
            const edge = opp.edgeAsk;
            const edgeClass = edge < 0 ? 'edge-negative' : edge >= 1 ? 'edge-positive' : 'edge-warning';
            edgeAskHtml = `<span class="${edgeClass}">${edge >= 0 ? '+' : ''}${edge.toFixed(1)}%</span>`;
        }

        const buyNo = opp.buyNoPrice !== null ? opp.buyNoPrice.toFixed(3) : 'N/A';
        const buyNoClass = changedFields.includes('buyNo') ? 'value-changed' : '';

        let edgeBidHtml = 'N/A';
        if (opp.edgeBid !== null) {
            const edge = opp.edgeBid;
            const edgeClass = edge < 0 ? 'edge-negative' : edge >= 1 ? 'edge-positive' : 'edge-warning';
            edgeBidHtml = `<span class="${edgeClass}">${edge >= 0 ? '+' : ''}${edge.toFixed(1)}%</span>`;
        }

        const roiPct = opp.roi * 100;
        const colorIcon = roiPct >= 0 ? '🟢' : '🔴';
        const roiHtml = `${colorIcon} <strong>${opp.roiSide}</strong> ${roiPct >= 0 ? '+' : ''}${roiPct.toFixed(1)}%`;
        const roiClass = changedFields.includes('roi') ? 'value-changed' : '';

        let kellyHtml = '<span style="color: #b2bec3;">0%</span>';
        if (opp.kelly > 0) {
            const displayKelly = Math.min(opp.kelly * 100, 100).toFixed(1);
            kellyHtml = `<span style="font-weight: bold; color: #2d3436;">${displayKelly}%</span>`;
        }
        const kellyClass = changedFields.includes('kelly') ? 'value-changed' : '';

        row.innerHTML = `
            <td class="company-cell">${opp.icon} ${opp.ticker}</td>
            <td class="strike-price">${strikePriceStr}</td>
            <td class="bs-fair-value">${bsProbHtml}</td>
            <td class="ask-price col-group-start col-ask ${bestAskClass}">${bestAsk}</td>
            <td class="col-group-end col-ask">${edgeAskHtml}</td>
            <td class="bid-price col-group-start col-bid ${buyNoClass}">${buyNo}</td>
            <td class="col-group-end col-bid">${edgeBidHtml}</td>
            <td class="yes-prob">${yesProb}%</td>
            <td class="roi-column ${roiClass}" style="font-weight: bold;">${roiHtml}</td>
            <td class="kelly-column ${kellyClass}">${kellyHtml}</td>
        `;

        tbody.appendChild(row);
    }
}

// Update last updated timestamp
function updateLastUpdated() {
    const now = new Date();
    const formatted = now.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    document.getElementById('lastUpdated').textContent = `Updated: ${formatted}`;
}
