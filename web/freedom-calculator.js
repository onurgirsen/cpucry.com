/**
 * freedom-calculator.js
 * Financial freedom calculator: deterministic compounding projection +
 * Monte Carlo simulation (1,000-10,000 paths) over random monthly returns.
 * Pure vanilla JS, hand-rolled SVG charts - no external dependencies.
 */

(() => {
    'use strict';

    const SVGNS = 'http://www.w3.org/2000/svg';

    // Chart-only colors: darker variants of the site accent/status hues so
    // marks stay within the dark-surface OKLCH lightness band (validated
    // separately from the lighter UI badge tokens in styles.css).
    const CHART = {
        accent: '#6366f1',
        accentSoft: 'rgba(99, 102, 241, 0.22)',
        accentSofter: 'rgba(99, 102, 241, 0.10)',
        principal: '#7c7c8a',
        principalSoft: 'rgba(124, 124, 138, 0.18)',
        success: '#059669',
        danger: '#dc2626',
        warning: '#d97706',
        grid: 'rgba(255, 255, 255, 0.08)',
        text: '#a0a0b0',
        textMuted: '#606070'
    };

    const RETURN_PRESETS = {
        deposit: { return: 5, vol: 5 },
        balanced: { return: 8, vol: 10 },
        stocks: { return: 10, vol: 16 },
        sp500: { return: 11, vol: 18 },
        aggressive: { return: 20, vol: 45 }
    };

    // ---- DOM refs ----
    const el = {
        startingCapital: document.getElementById('startingCapital'),
        monthlyContribution: document.getElementById('monthlyContribution'),
        targetAmount: document.getElementById('targetAmount'),
        currencySelect: document.getElementById('currencySelect'),
        returnPreset: document.getElementById('returnPreset'),
        years: document.getElementById('years'),
        yearsValue: document.getElementById('yearsValue'),
        annualReturn: document.getElementById('annualReturn'),
        annualReturnValue: document.getElementById('annualReturnValue'),
        annualVol: document.getElementById('annualVol'),
        annualVolValue: document.getElementById('annualVolValue'),
        inflationRate: document.getElementById('inflationRate'),
        inflationValue: document.getElementById('inflationValue'),
        numSimulations: document.getElementById('numSimulations'),
        showReal: document.getElementById('showReal'),
        calcBtn: document.getElementById('calcBtn'),
        deterministicStats: document.getElementById('deterministicStats'),
        mcStats: document.getElementById('mcStats'),
        mcSubtitle: document.getElementById('mcSubtitle'),
        probLabel: document.getElementById('probLabel'),
        probFill: document.getElementById('probFill'),
        growthChart: document.getElementById('growthChart'),
        fanChart: document.getElementById('fanChart'),
        histChart: document.getElementById('histChart'),
        percentileTable: document.getElementById('percentileTable'),
        currencyPrefixes: [
            document.getElementById('currencyPrefix1'),
            document.getElementById('currencyPrefix2'),
            document.getElementById('currencyPrefix3')
        ]
    };

    // ---- Formatting ----
    function formatCompact(value, currency) {
        const sign = value < 0 ? '-' : '';
        const abs = Math.abs(value);
        if (abs >= 1e9) return `${sign}${currency}${(abs / 1e9).toFixed(2)} Milyar`;
        if (abs >= 1e6) return `${sign}${currency}${(abs / 1e6).toFixed(2)} Milyon`;
        if (abs >= 1e3) return `${sign}${currency}${(abs / 1e3).toFixed(1)} Bin`;
        return `${sign}${currency}${abs.toFixed(0)}`;
    }

    function formatFull(value, currency) {
        return `${currency}${Math.round(value).toLocaleString('tr-TR')}`;
    }

    function formatPct(value, digits = 1) {
        return `%${value.toFixed(digits)}`;
    }

    function currentCurrency() {
        return el.currencySelect.value;
    }

    // ---- Random normal (Box-Muller, cached spare) ----
    let spareNormal = null;
    function randNormal() {
        if (spareNormal !== null) {
            const v = spareNormal;
            spareNormal = null;
            return v;
        }
        let u = 0, v = 0;
        while (u === 0) u = Math.random();
        while (v === 0) v = Math.random();
        const mag = Math.sqrt(-2 * Math.log(u));
        const z0 = mag * Math.cos(2 * Math.PI * v);
        const z1 = mag * Math.sin(2 * Math.PI * v);
        spareNormal = z1;
        return z0;
    }

    function percentileOf(sortedArr, p) {
        const idx = (p / 100) * (sortedArr.length - 1);
        const lo = Math.floor(idx), hi = Math.ceil(idx);
        if (lo === hi) return sortedArr[lo];
        const frac = idx - lo;
        return sortedArr[lo] * (1 - frac) + sortedArr[hi] * frac;
    }

    // ---- Deterministic projection ----
    function computeDeterministic({ capital, contribution, annualReturn, years }) {
        const monthlyRate = Math.pow(1 + annualReturn / 100, 1 / 12) - 1;
        const months = years * 12;
        let balance = capital;
        let principal = capital;
        const yearlyBalance = [capital];
        const yearlyPrincipal = [capital];
        for (let m = 1; m <= months; m++) {
            balance = balance * (1 + monthlyRate) + contribution;
            principal += contribution;
            if (m % 12 === 0) {
                yearlyBalance.push(balance);
                yearlyPrincipal.push(principal);
            }
        }
        return {
            yearlyBalance, yearlyPrincipal,
            finalBalance: balance, finalPrincipal: principal,
            finalGrowth: balance - principal
        };
    }

    function computeTimeToTarget({ capital, contribution, annualReturn, target }) {
        if (capital >= target) return { months: 0, reached: true };
        const monthlyRate = Math.pow(1 + annualReturn / 100, 1 / 12) - 1;
        let balance = capital;
        const maxMonths = 100 * 12;
        for (let m = 1; m <= maxMonths; m++) {
            balance = balance * (1 + monthlyRate) + contribution;
            if (balance >= target) return { months: m, reached: true };
        }
        return { months: maxMonths, reached: false };
    }

    // ---- Monte Carlo simulation ----
    function runMonteCarlo({ capital, contribution, annualReturn, annualVol, years, target, numSims }) {
        const months = years * 12;
        const monthlyMean = Math.pow(1 + annualReturn / 100, 1 / 12) - 1;
        const monthlyVol = (annualVol / 100) / Math.sqrt(12);

        const yearSnapshots = [];
        for (let y = 0; y <= years; y++) yearSnapshots.push(new Float64Array(numSims));

        const finalBalances = new Float64Array(numSims);
        const reachedTarget = new Uint8Array(numSims);
        const yearsToReach = new Float64Array(numSims).fill(-1);

        for (let s = 0; s < numSims; s++) {
            let balance = capital;
            yearSnapshots[0][s] = balance;
            let reached = balance >= target;
            if (reached) yearsToReach[s] = 0;
            for (let m = 1; m <= months; m++) {
                const r = monthlyMean + monthlyVol * randNormal();
                balance = Math.max(0, balance * (1 + r) + contribution);
                if (!reached && balance >= target) {
                    reached = true;
                    yearsToReach[s] = m / 12;
                }
                if (m % 12 === 0) yearSnapshots[m / 12][s] = balance;
            }
            finalBalances[s] = balance;
            reachedTarget[s] = reached ? 1 : 0;
        }

        const percentileSet = [5, 10, 25, 50, 75, 90, 95];
        const yearlyPercentiles = yearSnapshots.map(arr => {
            const sorted = Float64Array.from(arr).sort();
            const out = {};
            for (const p of percentileSet) out[p] = percentileOf(sorted, p);
            return out;
        });

        const finalSorted = Float64Array.from(finalBalances).sort();
        const finalPercentiles = {};
        for (const p of percentileSet) finalPercentiles[p] = percentileOf(finalSorted, p);

        let successCount = 0;
        for (let s = 0; s < numSims; s++) successCount += reachedTarget[s];
        const successProb = successCount / numSims;

        const reachedYears = [];
        for (let s = 0; s < numSims; s++) if (yearsToReach[s] >= 0) reachedYears.push(yearsToReach[s]);
        reachedYears.sort((a, b) => a - b);
        const medianYearsToReach = reachedYears.length
            ? percentileOf(Float64Array.from(reachedYears), 50)
            : null;

        return { yearlyPercentiles, finalBalances, finalSorted, finalPercentiles, successProb, medianYearsToReach };
    }

    // Bins the 1st-99th percentile range so a handful of extreme tail paths
    // (common with high volatility x long horizon, compounding lognormal-style)
    // don't collapse the whole histogram into a single spike; out-of-range
    // values still count, just clamped into the edge bins.
    function buildHistogram(finalSorted, numBins = 24) {
        const min = percentileOf(finalSorted, 1);
        const max = percentileOf(finalSorted, 99);
        const range = (max - min) || 1;
        const binWidth = range / numBins;
        const bins = Array.from({ length: numBins }, (_, i) => ({
            start: min + i * binWidth,
            end: min + (i + 1) * binWidth,
            count: 0
        }));
        for (let i = 0; i < finalSorted.length; i++) {
            let idx = Math.floor((finalSorted[i] - min) / binWidth);
            if (idx >= numBins) idx = numBins - 1;
            if (idx < 0) idx = 0;
            bins[idx].count++;
        }
        return bins;
    }

    // ---- Inflation / real-value deflation ----
    function deflator(inflationRate, yearIndex) {
        return Math.pow(1 + inflationRate / 100, yearIndex);
    }

    // ---- SVG helpers ----
    function svgEl(tag, attrs) {
        const e = document.createElementNS(SVGNS, tag);
        for (const k in attrs) e.setAttribute(k, attrs[k]);
        return e;
    }

    function clearChart(container) {
        container.innerHTML = '';
    }

    function niceStep(range, targetTicks = 5) {
        const raw = range / targetTicks;
        const mag = Math.pow(10, Math.floor(Math.log10(raw)));
        const norm = raw / mag;
        let step;
        if (norm < 1.5) step = 1;
        else if (norm < 3) step = 2;
        else if (norm < 7) step = 5;
        else step = 10;
        return step * mag;
    }

    function makeTooltip(wrapper) {
        const tip = document.createElement('div');
        tip.className = 'fc-tooltip';
        wrapper.appendChild(tip);
        return tip;
    }

    // ==================================================================
    // Chart 1: Growth chart - stacked area (principal + growth) vs target
    // ==================================================================
    function renderGrowthChart(container, data) {
        clearChart(container);
        const { years, principalArr, balanceArr, target, currency, inflationRate, showReal } = data;
        const W = 900, H = 380;
        const margin = { left: 78, right: 20, top: 20, bottom: 34 };
        const plotW = W - margin.left - margin.right;
        const plotH = H - margin.top - margin.bottom;
        const n = years + 1;

        const disp = (value, yearIdx) => showReal ? value / deflator(inflationRate, yearIdx) : value;
        const dPrincipal = principalArr.map((v, i) => disp(v, i));
        const dBalance = balanceArr.map((v, i) => disp(v, i));
        const dTarget = Array.from({ length: n }, (_, i) => disp(target, i));

        const maxVal = Math.max(...dBalance, ...dTarget) * 1.08;
        const yStep = niceStep(maxVal);
        const yMax = Math.ceil(maxVal / yStep) * yStep;

        const xScale = i => margin.left + (i / (n - 1)) * plotW;
        const yScale = v => margin.top + (1 - v / yMax) * plotH;

        const wrapper = document.createElement('div');
        wrapper.style.position = 'relative';
        const title = document.createElement('div');
        title.className = 'fc-chart-title';
        title.textContent = showReal
            ? `Portföy Büyümesi (Bugünkü Alım Gücü, Enflasyon %${inflationRate.toFixed(1)})`
            : 'Portföy Büyümesi (Nominal)';
        wrapper.appendChild(title);

        const svg = svgEl('svg', { viewBox: `0 0 ${W} ${H}`, width: W, height: H });

        // gridlines + y labels
        for (let v = 0; v <= yMax + 0.001; v += yStep) {
            const y = yScale(v);
            svg.appendChild(svgEl('line', { x1: margin.left, x2: W - margin.right, y1: y, y2: y, stroke: CHART.grid, 'stroke-width': 1 }));
            const label = svgEl('text', { x: margin.left - 10, y: y + 4, 'text-anchor': 'end', fill: CHART.textMuted, 'font-size': 11 });
            label.textContent = formatCompact(v, currency);
            svg.appendChild(label);
        }

        // x labels
        const xStep = years <= 10 ? 1 : years <= 20 ? 2 : 5;
        for (let i = 0; i <= years; i += xStep) {
            const x = xScale(i);
            const label = svgEl('text', { x, y: H - margin.bottom + 20, 'text-anchor': 'middle', fill: CHART.textMuted, 'font-size': 11 });
            label.textContent = `${i}y`;
            svg.appendChild(label);
        }

        // principal area (baseline -> principal)
        let principalPath = `M ${xScale(0)} ${yScale(0)} `;
        for (let i = 0; i < n; i++) principalPath += `L ${xScale(i)} ${yScale(dPrincipal[i])} `;
        principalPath += `L ${xScale(n - 1)} ${yScale(0)} Z`;
        svg.appendChild(svgEl('path', { d: principalPath, fill: CHART.principalSoft, stroke: 'none' }));

        // growth band (principal -> balance)
        let growthPath = `M ${xScale(0)} ${yScale(dPrincipal[0])} `;
        for (let i = 0; i < n; i++) growthPath += `L ${xScale(i)} ${yScale(dBalance[i])} `;
        for (let i = n - 1; i >= 0; i--) growthPath += `L ${xScale(i)} ${yScale(dPrincipal[i])} `;
        growthPath += 'Z';
        svg.appendChild(svgEl('path', { d: growthPath, fill: CHART.accentSofter, stroke: 'none' }));

        // principal line
        let principalLine = `M ${xScale(0)} ${yScale(dPrincipal[0])} `;
        for (let i = 1; i < n; i++) principalLine += `L ${xScale(i)} ${yScale(dPrincipal[i])} `;
        svg.appendChild(svgEl('path', { d: principalLine, fill: 'none', stroke: CHART.principal, 'stroke-width': 2, 'stroke-linejoin': 'round' }));

        // total balance line
        let balanceLine = `M ${xScale(0)} ${yScale(dBalance[0])} `;
        for (let i = 1; i < n; i++) balanceLine += `L ${xScale(i)} ${yScale(dBalance[i])} `;
        svg.appendChild(svgEl('path', { d: balanceLine, fill: 'none', stroke: CHART.accent, 'stroke-width': 2.5, 'stroke-linejoin': 'round' }));

        // target dashed line
        const targetY = yScale(dTarget[n - 1]);
        if (dTarget[n - 1] <= yMax * 1.02) {
            svg.appendChild(svgEl('line', {
                x1: margin.left, x2: W - margin.right, y1: yScale(dTarget[0]), y2: targetY,
                stroke: CHART.warning, 'stroke-width': 2, 'stroke-dasharray': '6 4'
            }));
        }

        // hover overlay
        const hitRect = svgEl('rect', { x: margin.left, y: margin.top, width: plotW, height: plotH, fill: 'transparent', style: 'cursor:crosshair; pointer-events:all;' });
        const crosshair = svgEl('line', { y1: margin.top, y2: H - margin.bottom, stroke: CHART.text, 'stroke-width': 1, opacity: 0 });
        svg.appendChild(crosshair);
        svg.appendChild(hitRect);
        wrapper.appendChild(svg);
        const tip = makeTooltip(wrapper);

        hitRect.addEventListener('pointermove', (e) => {
            const rect = svg.getBoundingClientRect();
            const scaleX = W / rect.width;
            const mouseX = (e.clientX - rect.left) * scaleX;
            let i = Math.round(((mouseX - margin.left) / plotW) * (n - 1));
            i = Math.max(0, Math.min(n - 1, i));
            const x = xScale(i);
            crosshair.setAttribute('x1', x);
            crosshair.setAttribute('x2', x);
            crosshair.setAttribute('opacity', 1);

            tip.innerHTML = `
                <div class="fc-tooltip-title">${i}. Yıl</div>
                <div class="fc-tooltip-row"><span class="fc-tooltip-key" style="background:${CHART.accent}"></span><span class="fc-tooltip-name">Toplam Bakiye</span><span class="fc-tooltip-val">${formatFull(dBalance[i], currency)}</span></div>
                <div class="fc-tooltip-row"><span class="fc-tooltip-key" style="background:${CHART.principal}"></span><span class="fc-tooltip-name">Yatırılan Anapara</span><span class="fc-tooltip-val">${formatFull(dPrincipal[i], currency)}</span></div>
                <div class="fc-tooltip-row"><span class="fc-tooltip-key" style="background:${CHART.accent}"></span><span class="fc-tooltip-name">Getiri</span><span class="fc-tooltip-val">${formatFull(dBalance[i] - dPrincipal[i], currency)}</span></div>
            `;
            tip.classList.add('visible');
            const wrapRect = wrapper.getBoundingClientRect();
            const px = ((x / W) * wrapRect.width);
            tip.style.left = `${Math.min(Math.max(px + 12, 0), wrapRect.width - tip.offsetWidth - 8)}px`;
            tip.style.top = `10px`;
        });
        hitRect.addEventListener('pointerleave', () => {
            tip.classList.remove('visible');
            crosshair.setAttribute('opacity', 0);
        });

        const legend = document.createElement('div');
        legend.className = 'fc-legend';
        legend.innerHTML = `
            <span class="fc-legend-item"><span class="fc-legend-swatch" style="background:${CHART.principal}"></span>Yatırılan Anapara</span>
            <span class="fc-legend-item"><span class="fc-legend-swatch" style="background:${CHART.accent}"></span>Toplam Bakiye</span>
            <span class="fc-legend-item"><span class="fc-legend-swatch dashed" style="color:${CHART.warning}"></span>Hedef</span>
        `;
        wrapper.appendChild(legend);
        container.appendChild(wrapper);
    }

    // ==================================================================
    // Chart 2: Monte Carlo fan chart
    // ==================================================================
    function renderFanChart(container, data) {
        clearChart(container);
        const { years, yearlyPercentiles, deterministicBalance, target, currency, inflationRate, showReal } = data;
        const W = 900, H = 420;
        const margin = { left: 78, right: 20, top: 20, bottom: 34 };
        const plotW = W - margin.left - margin.right;
        const plotH = H - margin.top - margin.bottom;
        const n = years + 1;

        const disp = (value, yearIdx) => showReal ? value / deflator(inflationRate, yearIdx) : value;

        const p5 = yearlyPercentiles.map((p, i) => disp(p[5], i));
        const p10 = yearlyPercentiles.map((p, i) => disp(p[10], i));
        const p25 = yearlyPercentiles.map((p, i) => disp(p[25], i));
        const p50 = yearlyPercentiles.map((p, i) => disp(p[50], i));
        const p75 = yearlyPercentiles.map((p, i) => disp(p[75], i));
        const p90 = yearlyPercentiles.map((p, i) => disp(p[90], i));
        const p95 = yearlyPercentiles.map((p, i) => disp(p[95], i));
        const det = deterministicBalance.map((v, i) => disp(v, i));
        const dTarget = Array.from({ length: n }, (_, i) => disp(target, i));

        const maxVal = Math.max(...p95, ...det, ...dTarget) * 1.08;
        const yStep = niceStep(maxVal);
        const yMax = Math.ceil(maxVal / yStep) * yStep;

        const xScale = i => margin.left + (i / (n - 1)) * plotW;
        const yScale = v => margin.top + (1 - Math.max(v, 0) / yMax) * plotH;

        const wrapper = document.createElement('div');
        wrapper.style.position = 'relative';
        const title = document.createElement('div');
        title.className = 'fc-chart-title';
        title.textContent = `Olası Senaryolar (${n - 1} Yıl, Yüzdelik Dilimler)${showReal ? ' — Reel' : ''}`;
        wrapper.appendChild(title);

        const svg = svgEl('svg', { viewBox: `0 0 ${W} ${H}`, width: W, height: H });

        for (let v = 0; v <= yMax + 0.001; v += yStep) {
            const y = yScale(v);
            svg.appendChild(svgEl('line', { x1: margin.left, x2: W - margin.right, y1: y, y2: y, stroke: CHART.grid, 'stroke-width': 1 }));
            const label = svgEl('text', { x: margin.left - 10, y: y + 4, 'text-anchor': 'end', fill: CHART.textMuted, 'font-size': 11 });
            label.textContent = formatCompact(v, currency);
            svg.appendChild(label);
        }
        const xStep = years <= 10 ? 1 : years <= 20 ? 2 : 5;
        for (let i = 0; i <= years; i += xStep) {
            const x = xScale(i);
            const label = svgEl('text', { x, y: H - margin.bottom + 20, 'text-anchor': 'middle', fill: CHART.textMuted, 'font-size': 11 });
            label.textContent = `${i}y`;
            svg.appendChild(label);
        }

        function band(top, bottom, opacity) {
            let d = `M ${xScale(0)} ${yScale(top[0])} `;
            for (let i = 1; i < n; i++) d += `L ${xScale(i)} ${yScale(top[i])} `;
            for (let i = n - 1; i >= 0; i--) d += `L ${xScale(i)} ${yScale(bottom[i])} `;
            d += 'Z';
            return svgEl('path', { d, fill: CHART.accent, opacity, stroke: 'none' });
        }
        svg.appendChild(band(p95, p5, 0.10));
        svg.appendChild(band(p90, p10, 0.16));
        svg.appendChild(band(p75, p25, 0.26));

        function line(arr, color, width, dash) {
            let d = `M ${xScale(0)} ${yScale(arr[0])} `;
            for (let i = 1; i < n; i++) d += `L ${xScale(i)} ${yScale(arr[i])} `;
            const attrs = { d, fill: 'none', stroke: color, 'stroke-width': width, 'stroke-linejoin': 'round' };
            if (dash) attrs['stroke-dasharray'] = dash;
            return svgEl('path', attrs);
        }
        svg.appendChild(line(det, CHART.warning, 2, '6 4'));
        svg.appendChild(line(p50, CHART.accent, 2.5, null));

        if (dTarget[n - 1] <= yMax * 1.02) {
            svg.appendChild(svgEl('line', {
                x1: margin.left, x2: W - margin.right, y1: yScale(dTarget[0]), y2: yScale(dTarget[n - 1]),
                stroke: CHART.danger, 'stroke-width': 2, 'stroke-dasharray': '2 4'
            }));
        }

        const hitRect = svgEl('rect', { x: margin.left, y: margin.top, width: plotW, height: plotH, fill: 'transparent', style: 'cursor:crosshair; pointer-events:all;' });
        const crosshair = svgEl('line', { y1: margin.top, y2: H - margin.bottom, stroke: CHART.text, 'stroke-width': 1, opacity: 0 });
        svg.appendChild(crosshair);
        svg.appendChild(hitRect);
        wrapper.appendChild(svg);
        const tip = makeTooltip(wrapper);

        hitRect.addEventListener('pointermove', (e) => {
            const rect = svg.getBoundingClientRect();
            const scaleX = W / rect.width;
            const mouseX = (e.clientX - rect.left) * scaleX;
            let i = Math.round(((mouseX - margin.left) / plotW) * (n - 1));
            i = Math.max(0, Math.min(n - 1, i));
            const x = xScale(i);
            crosshair.setAttribute('x1', x);
            crosshair.setAttribute('x2', x);
            crosshair.setAttribute('opacity', 1);

            tip.innerHTML = `
                <div class="fc-tooltip-title">${i}. Yıl</div>
                <div class="fc-tooltip-row"><span class="fc-tooltip-key" style="background:${CHART.accent}"></span><span class="fc-tooltip-name">Medyan (P50)</span><span class="fc-tooltip-val">${formatFull(p50[i], currency)}</span></div>
                <div class="fc-tooltip-row"><span class="fc-tooltip-key" style="background:${CHART.accent};opacity:.4"></span><span class="fc-tooltip-name">İyimser (P90)</span><span class="fc-tooltip-val">${formatFull(p90[i], currency)}</span></div>
                <div class="fc-tooltip-row"><span class="fc-tooltip-key" style="background:${CHART.accent};opacity:.4"></span><span class="fc-tooltip-name">Kötümser (P10)</span><span class="fc-tooltip-val">${formatFull(p10[i], currency)}</span></div>
                <div class="fc-tooltip-row"><span class="fc-tooltip-key" style="background:${CHART.warning}"></span><span class="fc-tooltip-name">Sabit Getiri Senaryosu</span><span class="fc-tooltip-val">${formatFull(det[i], currency)}</span></div>
            `;
            tip.classList.add('visible');
            const wrapRect = wrapper.getBoundingClientRect();
            const px = ((x / W) * wrapRect.width);
            tip.style.left = `${Math.min(Math.max(px + 12, 0), wrapRect.width - tip.offsetWidth - 8)}px`;
            tip.style.top = `10px`;
        });
        hitRect.addEventListener('pointerleave', () => {
            tip.classList.remove('visible');
            crosshair.setAttribute('opacity', 0);
        });

        const legend = document.createElement('div');
        legend.className = 'fc-legend';
        legend.innerHTML = `
            <span class="fc-legend-item"><span class="fc-legend-swatch" style="background:${CHART.accent}"></span>Medyan (P50)</span>
            <span class="fc-legend-item"><span class="fc-legend-swatch area" style="background:${CHART.accentSoft}"></span>%25-%75 aralığı</span>
            <span class="fc-legend-item"><span class="fc-legend-swatch area" style="background:${CHART.accentSofter}"></span>%5-%95 aralığı</span>
            <span class="fc-legend-item"><span class="fc-legend-swatch dashed" style="color:${CHART.warning}"></span>Sabit getiri senaryosu</span>
            <span class="fc-legend-item"><span class="fc-legend-swatch dashed" style="color:${CHART.danger}"></span>Hedef</span>
        `;
        wrapper.appendChild(legend);
        container.appendChild(wrapper);
    }

    // ==================================================================
    // Chart 3: Histogram of final balances
    // ==================================================================
    function renderHistogram(container, data) {
        clearChart(container);
        const { finalSorted, target, currency, years, inflationRate, showReal, numSims } = data;
        const finalDeflator = deflator(inflationRate, years);
        const disp = v => showReal ? v / finalDeflator : v;

        const dFinal = Float64Array.from(finalSorted).map(disp).sort();
        const dTarget = disp(target);
        const bins = buildHistogram(dFinal, 26);

        const W = 900, H = 340;
        const margin = { left: 78, right: 20, top: 20, bottom: 44 };
        const plotW = W - margin.left - margin.right;
        const plotH = H - margin.top - margin.bottom;

        const maxCount = Math.max(...bins.map(b => b.count)) * 1.15;
        const xMin = bins[0].start, xMax = bins[bins.length - 1].end;

        const xScale = v => margin.left + ((v - xMin) / (xMax - xMin)) * plotW;
        const yScale = c => margin.top + (1 - c / maxCount) * plotH;

        const wrapper = document.createElement('div');
        wrapper.style.position = 'relative';
        const title = document.createElement('div');
        title.className = 'fc-chart-title';
        title.textContent = `${numSims.toLocaleString('tr-TR')} Senaryonun Sonuç Dağılımı (${years}. Yıl Sonu Bakiyesi)${showReal ? ' — Reel' : ''}`;
        wrapper.appendChild(title);
        const note = document.createElement('div');
        note.className = 'fc-subtle';
        note.style.marginTop = '-0.4rem';
        note.textContent = 'En uç %1\'lik iyi ve kötü senaryolar okunabilirlik için kenar kutularda toplanmıştır.';
        wrapper.appendChild(note);

        const svg = svgEl('svg', { viewBox: `0 0 ${W} ${H}`, width: W, height: H });

        const yStep = niceStep(maxCount, 4);
        for (let c = 0; c <= maxCount; c += yStep) {
            const y = yScale(c);
            svg.appendChild(svgEl('line', { x1: margin.left, x2: W - margin.right, y1: y, y2: y, stroke: CHART.grid, 'stroke-width': 1 }));
            const label = svgEl('text', { x: margin.left - 10, y: y + 4, 'text-anchor': 'end', fill: CHART.textMuted, 'font-size': 11 });
            label.textContent = Math.round(c).toLocaleString('tr-TR');
            svg.appendChild(label);
        }

        const gap = 2;
        const barW = Math.max(1, plotW / bins.length - gap);
        const tip = makeTooltip(wrapper);

        bins.forEach((bin, i) => {
            const mid = (bin.start + bin.end) / 2;
            const color = mid >= dTarget ? CHART.success : CHART.danger;
            const x = xScale(bin.start) + gap / 2;
            const y = yScale(bin.count);
            const h = Math.max(0, (margin.top + plotH) - y);
            const rect = svgEl('rect', {
                x, y, width: Math.max(0, barW), height: h,
                fill: color, opacity: 0.75, rx: 3
            });
            rect.style.cursor = 'pointer';
            rect.addEventListener('pointerenter', () => rect.setAttribute('opacity', 1));
            rect.addEventListener('pointerleave', () => {
                rect.setAttribute('opacity', 0.75);
                tip.classList.remove('visible');
            });
            rect.addEventListener('pointermove', (e) => {
                const pct = (bin.count / dFinal.length * 100).toFixed(1);
                const rangeLabel = i === 0
                    ? `${formatFull(bin.end, currency)} ve altı`
                    : i === bins.length - 1
                        ? `${formatFull(bin.start, currency)} ve üzeri`
                        : `${formatFull(bin.start, currency)} — ${formatFull(bin.end, currency)}`;
                tip.innerHTML = `
                    <div class="fc-tooltip-title">${rangeLabel}</div>
                    <div class="fc-tooltip-row"><span class="fc-tooltip-key" style="background:${color}"></span><span class="fc-tooltip-name">Senaryo Sayısı</span><span class="fc-tooltip-val">${bin.count.toLocaleString('tr-TR')} (${pct}%)</span></div>
                `;
                tip.classList.add('visible');
                const wrapRect = wrapper.getBoundingClientRect();
                const svgRect = svg.getBoundingClientRect();
                const relX = (e.clientX - svgRect.left) / svgRect.width * wrapRect.width;
                tip.style.left = `${Math.min(Math.max(relX + 12, 0), wrapRect.width - tip.offsetWidth - 8)}px`;
                tip.style.top = `10px`;
            });
            svg.appendChild(rect);
        });

        // target marker line
        if (dTarget >= xMin && dTarget <= xMax) {
            const tx = xScale(dTarget);
            svg.appendChild(svgEl('line', {
                x1: tx, x2: tx, y1: margin.top, y2: margin.top + plotH,
                stroke: CHART.warning, 'stroke-width': 2, 'stroke-dasharray': '5 4'
            }));
            const label = svgEl('text', { x: tx, y: margin.top - 6, 'text-anchor': 'middle', fill: CHART.warning, 'font-size': 11, 'font-weight': 700 });
            label.textContent = 'Hedef';
            svg.appendChild(label);
        }

        // x axis labels (a handful across the range)
        const numXLabels = 6;
        for (let i = 0; i <= numXLabels; i++) {
            const v = xMin + (i / numXLabels) * (xMax - xMin);
            const x = xScale(v);
            const label = svgEl('text', { x, y: H - margin.bottom + 20, 'text-anchor': 'middle', fill: CHART.textMuted, 'font-size': 10 });
            label.textContent = formatCompact(v, currency);
            svg.appendChild(label);
        }

        wrapper.appendChild(svg);

        const legend = document.createElement('div');
        legend.className = 'fc-legend';
        legend.innerHTML = `
            <span class="fc-legend-item"><span class="fc-legend-swatch area" style="background:${CHART.success}"></span>Hedefe ulaştı</span>
            <span class="fc-legend-item"><span class="fc-legend-swatch area" style="background:${CHART.danger}"></span>Hedefin altında kaldı</span>
            <span class="fc-legend-item"><span class="fc-legend-swatch dashed" style="color:${CHART.warning}"></span>Hedef tutar</span>
        `;
        wrapper.appendChild(legend);
        container.appendChild(wrapper);
    }

    // ---- Stat card helper ----
    function statCard(label, value, opts = {}) {
        const div = document.createElement('div');
        div.className = 'fc-stat';
        div.innerHTML = `
            <div class="fc-stat-label">${label}</div>
            <div class="fc-stat-value ${opts.cls || ''}">${value}</div>
            ${opts.sub ? `<div class="fc-stat-sub">${opts.sub}</div>` : ''}
        `;
        return div;
    }

    function monthsToYearMonthStr(months) {
        const y = Math.floor(months / 12);
        const m = Math.round(months % 12);
        if (y === 0) return `${m} ay`;
        if (m === 0) return `${y} yıl`;
        return `${y} yıl ${m} ay`;
    }

    // ---- Read inputs ----
    function readInputs() {
        return {
            capital: parseFloat(el.startingCapital.value) || 0,
            contribution: parseFloat(el.monthlyContribution.value) || 0,
            target: parseFloat(el.targetAmount.value) || 0,
            years: parseInt(el.years.value, 10),
            annualReturn: parseFloat(el.annualReturn.value),
            annualVol: parseFloat(el.annualVol.value),
            inflationRate: parseFloat(el.inflationRate.value),
            numSims: parseInt(el.numSimulations.value, 10),
            showReal: el.showReal.checked,
            currency: currentCurrency()
        };
    }

    // ---- Main compute + render ----
    function computeAndRender() {
        const input = readInputs();
        const currency = input.currency;

        // Deterministic
        const det = computeDeterministic(input);
        const timeToTarget = computeTimeToTarget(input);

        el.deterministicStats.innerHTML = '';
        el.deterministicStats.appendChild(statCard(
            'Hedefe Ulaşma Süresi',
            timeToTarget.reached ? monthsToYearMonthStr(timeToTarget.months) : `100+ yıl (ulaşılamıyor)`,
            { cls: timeToTarget.reached ? 'accent' : 'danger' }
        ));
        el.deterministicStats.appendChild(statCard(
            `${input.years}. Yıl Sonu Bakiye (Nominal)`,
            formatFull(det.finalBalance, currency),
            { sub: `Reel (bugünkü): ${formatFull(det.finalBalance / deflator(input.inflationRate, input.years), currency)}` }
        ));
        el.deterministicStats.appendChild(statCard('Toplam Yatırılan Anapara', formatFull(det.finalPrincipal, currency)));
        el.deterministicStats.appendChild(statCard('Toplam Getiri', formatFull(det.finalGrowth, currency), { cls: 'success' }));

        renderGrowthChart(el.growthChart, {
            years: input.years,
            principalArr: det.yearlyPrincipal,
            balanceArr: det.yearlyBalance,
            target: input.target,
            currency,
            inflationRate: input.inflationRate,
            showReal: input.showReal
        });

        // Monte Carlo (deferred slightly so the "computing" UI state paints first)
        el.mcSubtitle.textContent = `${input.numSims.toLocaleString('tr-TR')} paralel senaryo simüle ediliyor...`;
        el.calcBtn.disabled = true;
        el.calcBtn.textContent = '⏳ Hesaplanıyor...';

        setTimeout(() => {
            const mc = runMonteCarlo(input);

            el.mcSubtitle.textContent = `Aylık getiriler bağımsız normal dağılımdan örneklenerek ${input.numSims.toLocaleString('tr-TR')} paralel senaryo (${input.years} yıl) simüle edildi.`;

            const probPct = mc.successProb * 100;
            el.probLabel.textContent = formatPct(probPct);
            el.probFill.style.width = `${probPct}%`;
            el.probFill.style.background = probPct >= 70 ? CHART.success : probPct >= 40 ? CHART.warning : CHART.danger;

            el.mcStats.innerHTML = '';
            el.mcStats.appendChild(statCard(
                'Hedefe Ulaşma Olasılığı',
                formatPct(probPct),
                { cls: probPct >= 50 ? 'success' : 'danger' }
            ));
            el.mcStats.appendChild(statCard(
                'Medyan Hedefe Ulaşma Süresi',
                mc.medianYearsToReach !== null ? monthsToYearMonthStr(mc.medianYearsToReach * 12) : 'Ulaşamayanlar çoğunlukta',
            ));
            const finalDefl = deflator(input.inflationRate, input.years);
            const dispFinal = v => input.showReal ? v / finalDefl : v;
            el.mcStats.appendChild(statCard(
                `Medyan ${input.years}. Yıl Bakiyesi`,
                formatFull(dispFinal(mc.finalPercentiles[50]), currency)
            ));
            el.mcStats.appendChild(statCard(
                'Kötümser / İyimser (P10 - P90)',
                `${formatCompact(dispFinal(mc.finalPercentiles[10]), currency)} — ${formatCompact(dispFinal(mc.finalPercentiles[90]), currency)}`
            ));

            renderFanChart(el.fanChart, {
                years: input.years,
                yearlyPercentiles: mc.yearlyPercentiles,
                deterministicBalance: det.yearlyBalance,
                target: input.target,
                currency,
                inflationRate: input.inflationRate,
                showReal: input.showReal
            });

            renderHistogram(el.histChart, {
                finalSorted: mc.finalSorted,
                target: input.target,
                currency,
                years: input.years,
                inflationRate: input.inflationRate,
                showReal: input.showReal,
                numSims: input.numSims
            });

            renderPercentileTable(mc, input, dispFinal);

            el.calcBtn.disabled = false;
            el.calcBtn.textContent = '📊 Hesapla ve Simüle Et';
        }, 30);
    }

    function renderPercentileTable(mc, input, dispFinal) {
        const currency = input.currency;
        const rows = [5, 10, 25, 50, 75, 90, 95].map(p => {
            const val = dispFinal(mc.finalPercentiles[p]);
            const reached = val >= (input.showReal ? input.target / deflator(input.inflationRate, input.years) : input.target);
            return `<tr>
                <td>P${p}</td>
                <td>${formatFull(val, currency)}</td>
                <td style="color:${reached ? 'var(--success)' : 'var(--danger)'}">${reached ? 'Hedefin üzerinde' : 'Hedefin altında'}</td>
            </tr>`;
        }).join('');
        el.percentileTable.innerHTML = `
            <thead><tr><th>Yüzdelik Dilim</th><th>${input.years}. Yıl Bakiyesi</th><th>Hedefe Göre</th></tr></thead>
            <tbody>${rows}</tbody>
        `;
    }

    // ---- Presets & slider sync ----
    function applyPreset(name) {
        const preset = RETURN_PRESETS[name];
        if (!preset) return;
        el.annualReturn.value = preset.return;
        el.annualVol.value = preset.vol;
        syncBadges();
    }

    function syncBadges() {
        el.yearsValue.textContent = `${el.years.value} yıl`;
        el.annualReturnValue.textContent = formatPct(parseFloat(el.annualReturn.value));
        el.annualVolValue.textContent = formatPct(parseFloat(el.annualVol.value));
        el.inflationValue.textContent = formatPct(parseFloat(el.inflationRate.value));
    }

    function syncCurrencyPrefixes() {
        const c = currentCurrency();
        el.currencyPrefixes.forEach(node => { if (node) node.textContent = c; });
    }

    function wireEvents() {
        el.returnPreset.addEventListener('change', () => {
            if (el.returnPreset.value !== 'custom') applyPreset(el.returnPreset.value);
        });
        el.annualReturn.addEventListener('input', () => {
            el.returnPreset.value = 'custom';
            syncBadges();
        });
        el.annualVol.addEventListener('input', () => {
            el.returnPreset.value = 'custom';
            syncBadges();
        });
        el.years.addEventListener('input', syncBadges);
        el.inflationRate.addEventListener('input', syncBadges);
        el.currencySelect.addEventListener('change', syncCurrencyPrefixes);
        el.showReal.addEventListener('change', computeAndRender);
        el.calcBtn.addEventListener('click', computeAndRender);
        window.addEventListener('resize', () => { /* SVG viewBox scales responsively, no-op */ });
    }

    // ---- Init ----
    document.addEventListener('DOMContentLoaded', () => {
        applyPreset('balanced');
        syncBadges();
        syncCurrencyPrefixes();
        wireEvents();
        computeAndRender();
    });
})();
