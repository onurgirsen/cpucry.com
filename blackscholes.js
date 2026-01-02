/**
 * Black-Scholes Model Implementation
 * For binary/digital call options (probability of S > K at expiry)
 */

const BlackScholes = {
    /**
     * Standard normal cumulative distribution function
     */
    normCDF(x) {
        const a1 = 0.254829592;
        const a2 = -0.284496736;
        const a3 = 1.421413741;
        const a4 = -1.453152027;
        const a5 = 1.061405429;
        const p = 0.3275911;

        const sign = x < 0 ? -1 : 1;
        x = Math.abs(x) / Math.sqrt(2);

        const t = 1.0 / (1.0 + p * x);
        const y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);

        return 0.5 * (1.0 + sign * y);
    },

    /**
     * Calculate probability of stock being above strike at expiration
     * For a binary/digital call option: P(S_T > K)
     * 
     * @param {number} S - Current stock price
     * @param {number} K - Strike price
     * @param {number} T - Time to expiration (in years)
     * @param {number} r - Risk-free interest rate
     * @param {number} sigma - Volatility (annualized)
     * @param {number} q - Dividend yield (continuous)
     * @returns {object} { fairValue, probability }
     */
    binaryCall(S, K, T, r, sigma, q = 0) {
        if (T <= 0) {
            const prob = S > K ? 1.0 : 0.0;
            return { fairValue: prob, probability: prob };
        }

        if (sigma <= 0) {
            sigma = 0.001;
        }

        // d2 = (ln(S/K) + (r - q - σ²/2) * T) / (σ * √T)
        const d2 = (Math.log(S / K) + (r - q - 0.5 * sigma * sigma) * T) / (sigma * Math.sqrt(T));

        // Probability = N(d2) under risk-neutral measure
        const probability = this.normCDF(d2);

        // Fair Value (Price) = e^(-rT) * Probability
        const discountFactor = Math.exp(-r * T);
        const fairValue = discountFactor * probability;

        return { fairValue, probability };
    },

    /**
     * Calculate time to expiry in years based on trading days
     * @param {Date} resolutionDate - Market resolution date
     * @returns {number} Time in years
     */
    getTimeToExpiry(resolutionDate) {
        const now = new Date();
        const calendarDays = (resolutionDate - now) / (1000 * 60 * 60 * 24);
        const tradingDays = calendarDays * (5 / 7);  // Approximate trading days
        return Math.max(tradingDays / CONFIG.TRADING_DAYS_PER_YEAR, 0.001);
    },

    /**
     * Calculate fair value for a market
     * @param {number} strikePrice - Strike price
     * @param {object} stockData - Stock data with price and volatility
     * @returns {object|null} { price, probability } or null
     */
    calculateFairValue(strikePrice, stockData) {
        if (!stockData || !stockData.price || !stockData.volatility) {
            return null;
        }

        const S = stockData.price;
        const K = strikePrice;
        const T = this.getTimeToExpiry(CONFIG.RESOLUTION_DATE);
        const r = CONFIG.RISK_FREE_RATE;
        const sigma = stockData.volatility;
        const q = stockData.dividendYield || 0;

        const result = this.binaryCall(S, K, T, r, sigma, q);

        return {
            price: result.fairValue,
            probability: result.probability
        };
    }
};

window.BlackScholes = BlackScholes;
