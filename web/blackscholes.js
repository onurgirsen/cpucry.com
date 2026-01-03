/**
 * blackscholes.js - Black-Scholes calculations
 * Pure JavaScript implementation
 */

/**
 * Standard normal cumulative distribution function (CDF)
 * Approximation using Abramowitz and Stegun formula
 */
function normalCDF(x) {
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
}

/**
 * Calculate Black-Scholes binary call probability
 * P(S_T > K) = N(d2)
 * 
 * @param {number} S - Current stock price
 * @param {number} K - Strike price
 * @param {number} T - Time to expiration (years)
 * @param {number} r - Risk-free interest rate
 * @param {number} sigma - Volatility (annualized)
 * @param {number} q - Dividend yield
 * @returns {Object} { price, probability }
 */
function blackScholesBinaryCall(S, K, T, r, sigma, q = 0) {
    if (T <= 0) {
        return {
            price: S > K ? 1.0 : 0.0,
            probability: S > K ? 1.0 : 0.0
        };
    }

    if (sigma <= 0) sigma = 0.001;

    // d2 = (ln(S/K) + (r - q - σ²/2) * T) / (σ * √T)
    const d2 = (Math.log(S / K) + (r - q - 0.5 * sigma * sigma) * T) / (sigma * Math.sqrt(T));

    // Probability = N(d2) under risk-neutral measure
    const probability = normalCDF(d2);

    // Fair Value (Price) = e^(-rT) * Probability
    const discountFactor = Math.exp(-r * T);
    const price = discountFactor * probability;

    return { price, probability };
}

/**
 * Calculate fair value for a market
 */
function calculateFairValue(strikePrice, stockData) {
    if (!stockData || !stockData.currentPrice || !stockData.volatility) {
        return null;
    }

    const S = stockData.currentPrice;
    const K = strikePrice;
    const T = stockData.timeToExpiry;
    const r = stockData.riskFreeRate || 0.045;
    const sigma = stockData.volatility;
    const q = stockData.dividendYield || 0;

    return blackScholesBinaryCall(S, K, T, r, sigma, q);
}

// Export
window.BlackScholes = {
    normalCDF,
    blackScholesBinaryCall,
    calculateFairValue
};
