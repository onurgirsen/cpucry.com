/**
 * API Module - Handles all external API calls
 */

const API = {
    // Cache for stock data (to reduce API calls)
    stockCache: {},
    stockCacheExpiry: 5 * 60 * 1000,  // 5 minutes

    /**
     * Fetch with optional CORS proxy
     */
    async fetchWithProxy(url, options = {}) {
        const proxyUrl = CONFIG.CORS_PROXY ? CONFIG.CORS_PROXY + encodeURIComponent(url) : url;

        try {
            const response = await fetch(proxyUrl, {
                ...options,
                headers: {
                    'Accept': 'application/json',
                    ...options.headers
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.warn(`API call failed for ${url}:`, error.message);
            return null;
        }
    },

    /**
     * Fetch event data from Polymarket Gamma API
     */
    async getEventData(eventSlug) {
        const url = `${CONFIG.GAMMA_API}/events?slug=${eventSlug}`;
        const data = await this.fetchWithProxy(url);
        return data && data.length > 0 ? data[0] : null;
    },

    /**
     * Fetch order book from Polymarket CLOB API
     */
    async getOrderBook(tokenId) {
        const url = `${CONFIG.CLOB_API}/book?token_id=${tokenId}`;
        return await this.fetchWithProxy(url);
    },

    /**
     * Analyze order book to get best bid/ask
     */
    analyzeOrderBook(orderBook) {
        if (!orderBook) return null;

        const bids = orderBook.bids || [];
        const asks = orderBook.asks || [];

        // Sort bids (highest first) and asks (lowest first)
        const bidsSorted = [...bids].sort((a, b) => parseFloat(b.price) - parseFloat(a.price));
        const asksSorted = [...asks].sort((a, b) => parseFloat(a.price) - parseFloat(b.price));

        const bestBid = bidsSorted.length > 0 ? parseFloat(bidsSorted[0].price) : 0;
        const bestAsk = asksSorted.length > 0 ? parseFloat(asksSorted[0].price) : 1;

        const totalBid = bids.reduce((sum, b) => sum + parseFloat(b.size), 0);
        const totalAsk = asks.reduce((sum, a) => sum + parseFloat(a.size), 0);

        return {
            bestBid,
            bestAsk,
            spread: bestAsk - bestBid,
            totalBidLiquidity: totalBid,
            totalAskLiquidity: totalAsk
        };
    },

    /**
     * Fetch stock price from Yahoo Finance
     */
    async getStockPrice(ticker) {
        // Check cache first
        const cached = this.stockCache[ticker];
        if (cached && Date.now() - cached.timestamp < this.stockCacheExpiry) {
            return cached.data;
        }

        const companyConfig = CONFIG.COMPANIES[ticker];
        if (!companyConfig) return null;

        try {
            // Use 3 months of data for proper volatility calculation (matching Python version)
            const url = `${CONFIG.YAHOO_API}/${ticker}?interval=1d&range=3mo`;
            const data = await this.fetchWithProxy(url);

            if (data && data.chart && data.chart.result && data.chart.result[0]) {
                const meta = data.chart.result[0].meta;
                const price = meta.regularMarketPrice;

                // Calculate historical volatility from closes (matching Python's 90-day approach)
                const closes = data.chart.result[0].indicators?.quote?.[0]?.close || [];
                let volatility = companyConfig.defaultVolatility;

                // Need at least 20 data points for reliable volatility
                if (closes.length >= 20) {
                    const returns = [];
                    for (let i = 1; i < closes.length; i++) {
                        if (closes[i] && closes[i - 1] && closes[i - 1] > 0) {
                            returns.push((closes[i] - closes[i - 1]) / closes[i - 1]);
                        }
                    }

                    if (returns.length >= 15) {
                        // Calculate mean
                        const mean = returns.reduce((a, b) => a + b, 0) / returns.length;

                        // Calculate variance using sample variance (n-1 denominator, matching Python)
                        const variance = returns.reduce((sum, r) => sum + Math.pow(r - mean, 2), 0) / (returns.length - 1);
                        const dailyVol = Math.sqrt(variance);

                        // Annualize
                        volatility = dailyVol * Math.sqrt(252);

                        console.log(`[VOL] ${ticker}: ${(volatility * 100).toFixed(1)}% (from ${returns.length} days of data)`);

                        // Sanity check - volatility should be reasonable
                        if (volatility < 0.10 || volatility > 2.0) {
                            console.warn(`[VOL] ${ticker}: Calculated vol ${(volatility * 100).toFixed(1)}% out of range, using default ${(companyConfig.defaultVolatility * 100).toFixed(1)}%`);
                            volatility = companyConfig.defaultVolatility;
                        }
                    } else {
                        console.warn(`[VOL] ${ticker}: Only ${returns.length} valid returns, using default volatility`);
                    }
                } else {
                    console.warn(`[VOL] ${ticker}: Only ${closes.length} data points, using default volatility`);
                }

                const stockData = {
                    price: price || companyConfig.defaultPrice,
                    volatility: volatility,
                    dividendYield: companyConfig.dividendYield
                };

                // Cache the result
                this.stockCache[ticker] = {
                    data: stockData,
                    timestamp: Date.now()
                };

                return stockData;
            }
        } catch (error) {
            console.warn(`Failed to fetch stock data for ${ticker}:`, error);
        }

        // Return defaults if API fails
        console.warn(`[VOL] ${ticker}: API failed, using default values`);
        return {
            price: companyConfig.defaultPrice,
            volatility: companyConfig.defaultVolatility,
            dividendYield: companyConfig.dividendYield
        };
    },

    /**
     * Extract strike price from question text
     */
    extractStrikePrice(question) {
        const match = question.match(/\$?([\d,]+(?:\.\d+)?)/);
        if (match) {
            return parseFloat(match[1].replace(/,/g, ''));
        }
        return null;
    },

    /**
     * Fetch all market data for a company
     */
    async fetchCompanyData(ticker) {
        const companyConfig = CONFIG.COMPANIES[ticker];
        if (!companyConfig) return null;

        // Fetch stock data and event data in parallel
        const [stockData, eventData] = await Promise.all([
            this.getStockPrice(ticker),
            this.getEventData(companyConfig.slug)
        ]);

        if (!eventData) {
            console.warn(`No event data for ${ticker}`);
            return null;
        }

        const markets = eventData.markets || [];
        const processedMarkets = [];

        // Fetch all order books in parallel
        const orderBookPromises = markets.map(async (market) => {
            let tokens = market.clobTokenIds || '[]';
            if (typeof tokens === 'string') {
                try { tokens = JSON.parse(tokens); } catch { tokens = []; }
            }

            let orderBook = null;
            if (tokens.length >= 1) {
                orderBook = await this.getOrderBook(tokens[0]);
            }

            return { market, orderBook };
        });

        const marketResults = await Promise.all(orderBookPromises);

        for (const { market, orderBook } of marketResults) {
            let prices = market.outcomePrices || '[]';
            if (typeof prices === 'string') {
                try { prices = JSON.parse(prices); } catch { prices = []; }
            }

            const question = market.question || 'Unknown';
            const strikePrice = this.extractStrikePrice(question);

            const marketResult = {
                question,
                strikePrice,
                yesProbability: prices.length > 0 ? parseFloat(prices[0]) : null,
                noProbability: prices.length > 1 ? parseFloat(prices[1]) : null
            };

            // Calculate Black-Scholes fair value
            if (strikePrice && stockData) {
                const bsResult = BlackScholes.calculateFairValue(strikePrice, stockData);
                if (bsResult) {
                    marketResult.bsFairValue = bsResult.price;
                    marketResult.bsProbability = bsResult.probability;

                    if (marketResult.yesProbability !== null) {
                        marketResult.edgeVsMarket = bsResult.price - marketResult.yesProbability;
                    }
                }
            }

            // Add order book analysis
            const analysis = this.analyzeOrderBook(orderBook);
            if (analysis) {
                marketResult.yesOrderbook = analysis;

                if (marketResult.bsFairValue !== undefined) {
                    marketResult.edgeVsBid = marketResult.bsFairValue - analysis.bestBid;
                    marketResult.edgeVsAsk = marketResult.bsFairValue - analysis.bestAsk;
                }
            }

            processedMarkets.push(marketResult);
        }

        return {
            eventSlug: companyConfig.slug,
            eventTitle: eventData.title || companyConfig.slug,
            stockData,
            markets: processedMarkets
        };
    },

    /**
     * Fetch all companies data
     */
    async fetchAllData() {
        const tickers = Object.keys(CONFIG.COMPANIES);

        const results = await Promise.all(
            tickers.map(ticker => this.fetchCompanyData(ticker))
        );

        return results.filter(r => r !== null);
    }
};

window.API = API;
