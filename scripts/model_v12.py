# -*- coding: utf-8 -*-
"""Pyodide-compatible version of the BTC direction model."""

import math
import threading
import time
import queue
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

try:
    import pyodide_http  # type: ignore

    pyodide_http.patch_all()
except Exception:
    pass

import numpy as np
import pandas as pd
import requests

try:
    from IPython.display import clear_output, display, Image
except Exception:
    def clear_output(wait: bool = False):
        print("\n" * 2)

    def display(*args, **kwargs):
        return None

    class Image:  # pragma: no cover
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

from scipy.stats import t as student_t, poisson
from collections import deque

ARCH_AVAILABLE = True
try:
    from arch import arch_model
except ImportError:
    ARCH_AVAILABLE = False
    arch_model = None
    print("UYARI: 'arch' kütüphanesi bulunamadı. GARCH bileşeni devre dışı bırakıldı.")

ENABLE_PLOTTING = True
try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
except ImportError:
    ENABLE_PLOTTING = False
    plt = None
    mdates = None
    print("UYARI: 'matplotlib' kütüphanesi bulunamadı, grafik çizimi devre dışı.")


START_TZ = "Europe/Berlin"
HORIZON_MIN = 15
POLL_SEC = 1.0
EXCHANGES = ["BINANCE", "COINBASE"]

HIST_MINUTES_GARCH = 1440
HIST_MINUTES_DRIFT = 120

JUMP_THRESH_K = 4.0

PARAM_EWMA_SPAN_MIN = 60
DRIFT_EWMA_SPAN_MIN = 15
DRIFT_OBI_WEIGHT = 0.5

OBI_SMOOTHING_SECONDS = 30

GARCH_AGG_MIN = 5
GARCH_DIST = "t"
GARCH_P = 1
GARCH_Q = 1
GARCH_O = 1
LONG_TERM_HV_DAYS = 90

FIXED_DF_T = 3.0
FALLBACK_ANNUAL_VOL = 0.90
KAPPA_DECAY_HALFLIFE_MIN = 10.0
THETA_MEAN_REVERSION = 0.0001
FIXED_LAMBDA_PER_DAY = 1.0
FIXED_SIGMA_JUMP = 0.01

PLOT_UPDATE_SEC = 5
PLOT_HISTORY_POINTS = 120
PLOT_FILENAME = "probability_plot.png"

UA = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
SECONDS_PER_YEAR = 365.25 * 24 * 60 * 60
SECONDS_PER_DAY = 24 * 60 * 60
KAPPA_SEC = (
    math.log(2) / (KAPPA_DECAY_HALFLIFE_MIN * 60.0)
    if KAPPA_DECAY_HALFLIFE_MIN > 0
    else 0
)
FIXED_LAMBDA_SEC = FIXED_LAMBDA_PER_DAY / SECONDS_PER_DAY


def fmt_mmss(s):
    s = max(0, int(round(s)))
    return f"{s // 60:02d}:{s % 60:02d}"


def dt_loc(ts):
    return datetime.fromtimestamp(ts, tz=ZoneInfo(START_TZ))


def to_ms(ts):
    return int(round(ts * 1000.0))


def rs_variance(o, h, l, c):
    try:
        if not (o > 0 and h > 0 and l > 0 and c > 0):
            return 0.0
        if h < l:
            h_, l_ = l, h
        else:
            h_, l_ = h, l
        if not (h_ > 0 and l_ > 0):
            return 0.0
        lo = math.log(o)
        lh = math.log(h_)
        ll = math.log(l_)
        lc = math.log(c)
        term = (lh - lo) * (lh - lc) + (ll - lo) * (ll - lc)
        return max(term, 0.0)
    except Exception:
        return 0.0


def compute_start_time_local():
    tz = ZoneInfo(START_TZ)
    now_local = datetime.now(tz)
    quarter_minutes = (now_local.minute // 15) * 15
    start_local = now_local.replace(minute=quarter_minutes, second=0, microsecond=0)
    return start_local.strftime("%Y-%m-%d %H:%M:%S")


START_TIME_LOCAL = compute_start_time_local()



def calculate_long_term_hv(
    exchange="BINANCE", days=LONG_TERM_HV_DAYS, fallback_vol=FALLBACK_ANNUAL_VOL
):
    print(f"Başlangıç: Son {days} günlük HV hesaplanıyor ({exchange})...")
    fallback_var_sec = (fallback_vol ** 2) / SECONDS_PER_YEAR
    now = datetime.now(timezone.utc)
    end_time = now - timedelta(days=1)
    start_time = end_time - timedelta(days=days)
    daily_prices = []
    try:
        if exchange == "BINANCE":
            symbol = "BTCUSDT"
            interval = "1d"
            limit = days + 5
            url = (
                "https://api.binance.com/api/v3/klines?symbol="
                f"{symbol}&interval={interval}&startTime={to_ms(start_time.timestamp())}&limit={limit}"
            )
            print(f"DEBUG: Binance URL: {url}")
            r = requests.get(url, timeout=10, headers=UA)
            r.raise_for_status()
            data = r.json()
            data_filtered = [
                k
                for k in data
                if len(k) > 6
                and to_ms(start_time.timestamp()) <= k[0] < to_ms(end_time.timestamp())
            ]
            if not data_filtered:
                raise ValueError(
                    f"Binance [{start_time.date()} - {end_time.date()}] veri yok."
                )
            if len(data_filtered) < days * 0.7:
                print(f"UYARI: Binance az veri ({len(data_filtered)}/{days}).")
            daily_prices = [float(k[4]) for k in data_filtered]
        elif exchange == "COINBASE":
            product_id = "BTC-USD"
            granularity = 86400
            all_candles = []
            current_start_dt = start_time
            max_requests_cb = (days // 300) + 2
            request_count_cb = 0
            while current_start_dt < end_time and request_count_cb < max_requests_cb:
                request_count_cb += 1
                batch_end_dt = min(current_start_dt + timedelta(days=300), end_time)
                start_iso = current_start_dt.isoformat().replace("+00:00", "Z")
                end_iso = batch_end_dt.isoformat().replace("+00:00", "Z")
                url = (
                    "https://api.exchange.coinbase.com/products/"
                    f"{product_id}/candles?granularity={granularity}&start={start_iso}&end={end_iso}"
                )
                print(f"DEBUG: Coinbase URL: {url}")
                try:
                    r_cb = requests.get(url, timeout=10, headers=UA)
                    r_cb.raise_for_status()
                    candles = r_cb.json()
                    if isinstance(candles, list):
                        candles.sort(key=lambda x: int(x[0]))
                        all_candles.extend(candles)
                        if candles:
                            last_candle_dt = datetime.fromtimestamp(
                                int(candles[-1][0]), tz=timezone.utc
                            )
                            current_start_dt = (
                                last_candle_dt.replace(
                                    hour=0, minute=0, second=0, microsecond=0
                                )
                                + timedelta(days=1)
                            )
                        else:
                            current_start_dt = batch_end_dt
                    else:
                        print(f"UYARI: Coinbase geçersiz yanıt: {candles}")
                        break
                except requests.exceptions.RequestException as cb_e:
                    print(f"Coinbase API hatası: {cb_e}")
                    break
                time.sleep(0.4)
            if not all_candles:
                raise ValueError(
                    f"Coinbase [{start_time.date()} - {end_time.date()}] veri yok."
                )
            all_candles.sort(key=lambda x: int(x[0]))
            data_filtered = [
                c
                for c in all_candles
                if start_time.timestamp() <= c[0] < end_time.timestamp()
            ]
            unique_data = []
            seen_days = set()
            for c in data_filtered:
                day_ts = int(c[0]) // SECONDS_PER_DAY
                if day_ts not in seen_days:
                    if len(c) > 4:
                        unique_data.append(c)
                    seen_days.add(day_ts)
            data_filtered = unique_data
            if len(data_filtered) < days * 0.7:
                print(f"UYARI: Coinbase az veri ({len(data_filtered)}/{days}).")
            if not data_filtered:
                raise ValueError(
                    f"Coinbase [{start_time.date()} - {end_time.date()}] filtrelenmiş veri yok."
                )
            daily_prices = [float(c[4]) for c in data_filtered]
        else:
            raise ValueError("Desteklenmeyen borsa")
        if not daily_prices or len(daily_prices) < 2:
            raise ValueError("Yetersiz fiyat noktası.")
        daily_prices = [p for p in daily_prices if p > 0]
        if len(daily_prices) < 2:
            raise ValueError("Yetersiz pozitif fiyat noktası.")
        log_returns = np.log(np.array(daily_prices[1:]) / np.array(daily_prices[:-1]))
        log_returns = log_returns[
            ~np.isnan(log_returns) & ~np.isinf(log_returns)
        ]
        if len(log_returns) < max(days * 0.5, 10):
            raise ValueError(f"Yetersiz geçerli log getiri: {len(log_returns)}")
        daily_vol = np.std(log_returns, ddof=1)
        annual_vol = daily_vol * np.sqrt(365.25)
        annual_vol = np.clip(annual_vol, 0.15, 2.50)
        mean_var_sec = (annual_vol ** 2) / SECONDS_PER_YEAR
        print(
            f"Uzun Vadeli HV ({len(log_returns)} getiri): {annual_vol * 100:.1f}% -> "
            f"Taban Saniyelik Varyans: {mean_var_sec:.2e}"
        )
        return max(mean_var_sec, fallback_var_sec)
    except requests.exceptions.HTTPError as http_err:
        print(
            "UYARI: Uzun vadeli HV hesaplanamadı (HTTP"
            f" {http_err.response.status_code}), varsayılan {fallback_vol * 100:.0f}% kullanılacak."
        )
        return fallback_var_sec
    except Exception as e:
        print(
            "UYARI: Uzun vadeli HV hesaplanamadı ("
            f"{type(e).__name__}: {e}), varsayılan {fallback_vol * 100:.0f}% kullanılacak."
        )
        return fallback_var_sec



def fit_garch_model(ohlc_1m, agg_minutes=GARCH_AGG_MIN):
    if not ARCH_AVAILABLE or arch_model is None:
        return None
    if ohlc_1m is None or len(ohlc_1m) < 60:
        return None
    df = pd.DataFrame(ohlc_1m, columns=["timestamp", "open", "high", "low", "close"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")
    df = df.set_index("timestamp")
    agg_rule = f"{agg_minutes}T"
    ohlc_agg = df["close"].resample(agg_rule).last()
    ohlc_agg = ohlc_agg.dropna()
    ohlc_agg = ohlc_agg[ohlc_agg > 0]
    if len(ohlc_agg) < 20:
        return None
    log_returns = np.log(ohlc_agg / ohlc_agg.shift(1)).dropna() * 100
    if (
        log_returns.empty
        or log_returns.isnull().all()
        or log_returns.std() < 1e-12
    ):
        return None
    q_low, q_high = log_returns.dropna().quantile([0.01, 0.99])
    if pd.isna(q_low) or pd.isna(q_high):
        log_returns_clipped = log_returns.dropna()
    else:
        log_returns_clipped = log_returns.clip(lower=q_low, upper=q_high).dropna()
    if log_returns_clipped.empty:
        return None
    try:
        garch = arch_model(
            log_returns_clipped,
            mean="Zero",
            vol="GARCH",
            p=GARCH_P,
            o=GARCH_O,
            q=GARCH_Q,
            dist=GARCH_DIST,
        )
    except Exception as model_def_e:
        print(f"UYARI: GARCH modeli tanımlanamadı: {model_def_e}")
        return None
    try:
        res = garch.fit(update_freq=0, disp="off", show_warning=False)
        if not res.convergence_flag == 0:
            print(f"UYARI: GARCH modeli yakınsamadı (flag={res.convergence_flag}).")
        return res
    except (np.linalg.LinAlgError, ValueError) as fit_e:
        print(f"UYARI: GARCH modeli uydurulamadı (Veri/Yakınsama): {fit_e}")
        return None
    except Exception as fit_e:
        print(f"UYARI: GARCH modeli uydurulamadı (Beklenmedik): {fit_e}")
        return None


def get_garch_forecast(garch_result, tau_seconds, long_term_var_floor_sec):
    df_fallback = FIXED_DF_T
    var_fallback = long_term_var_floor_sec * max(tau_seconds, 1.0)
    if garch_result is None or tau_seconds <= 0:
        return var_fallback, df_fallback
    garch_period_sec = GARCH_AGG_MIN * 60
    horizon_steps = max(math.ceil(tau_seconds / garch_period_sec), 1)
    try:
        forecast = garch_result.forecast(
            horizon=horizon_steps, reindex=False, method="analytic"
        )
        if forecast is None or forecast.variance.empty:
            raise ValueError("GARCH tahmini boş.")
        variances_forecast_hstep = forecast.variance.iloc[-1].values / 10000
        floor_var_hstep = long_term_var_floor_sec * garch_period_sec / 10000
        if np.isnan(variances_forecast_hstep).any():
            print("UYARI: GARCH varyans tahmininde NaN var.")
            variances_forecast_hstep = np.nan_to_num(
                variances_forecast_hstep, nan=floor_var_hstep
            )
        variances_forecast_hstep = np.maximum(variances_forecast_hstep, floor_var_hstep)
        full_steps = int(tau_seconds // garch_period_sec)
        partial_step_ratio = (tau_seconds % garch_period_sec) / garch_period_sec
        cumulative_var_hstep = 0.0
        num_forecasts = len(variances_forecast_hstep)
        steps_to_sum = min(full_steps, num_forecasts)
        if steps_to_sum > 0:
            cumulative_var_hstep += np.sum(
                np.maximum(variances_forecast_hstep[:steps_to_sum], 0)
            )
        if partial_step_ratio > 0:
            step_index = min(full_steps, num_forecasts - 1)
            if step_index >= 0:
                cumulative_var_hstep += (
                    max(variances_forecast_hstep[step_index], 0) * partial_step_ratio
                )
        final_cumulative_var = cumulative_var_hstep
        return max(final_cumulative_var, 1e-18), FIXED_DF_T
    except Exception as e:
        print(f"UYARI: GARCH tahmini alınamadı: {e}")
        return var_fallback, df_fallback



def get_raw_returns_from_ohlc(ohlc_1m):
    if ohlc_1m is None or len(ohlc_1m) < 2:
        return None
    timestamps = []
    ret = []
    valid_data_count = 0
    for i, (t, o, h, l, c) in enumerate(ohlc_1m):
        current_ret = np.nan
        if c > 0:
            try:
                if i > 0:
                    prev_candle = ohlc_1m[i - 1]
                    if len(prev_candle) > 4:
                        prev_c = prev_candle[4]
                        if prev_c > 0:
                            current_ret = math.log(c / prev_c)
                            if (
                                not pd.isna(current_ret)
                                and not np.isinf(current_ret)
                            ):
                                timestamps.append(t)
                                ret.append(current_ret)
                                valid_data_count += 1
            except Exception:
                pass
    if valid_data_count < 5:
        return None
    index = pd.to_datetime(timestamps, unit="s")
    ret_series = pd.Series(ret, index=index, dtype=float)
    return ret_series


def estimate_drift(raw_returns: pd.Series, obi: float, obi_weight: float):
    if raw_returns is None or len(raw_returns) < 5:
        return 0.0, (0.0, 0.0, (obi - 0.5) * 2.0, 0.0)
    span = max(DRIFT_EWMA_SPAN_MIN, 2)
    base_drift_per_min = 0.0
    ewm_std_min = 0.0
    try:
        ewm_mean = raw_returns.ewm(span=span, adjust=True).mean()
        ewm_std = raw_returns.ewm(span=span, adjust=True).std()
        if not ewm_mean.empty:
            base_drift_per_min = float(ewm_mean.iloc[-1])
        if not ewm_std.empty:
            ewm_std_min = float(ewm_std.iloc[-1])
        if pd.isna(base_drift_per_min):
            base_drift_per_min = 0.0
        if pd.isna(ewm_std_min):
            ewm_std_min = 0.0
    except IndexError:
        base_drift_per_min = 0.0
        ewm_std_min = 0.0
    obi_signal = (obi - 0.5) * 2.0
    ewm_std_min = max(ewm_std_min, 1e-10)
    obi_drift_per_min = obi_signal * ewm_std_min * obi_weight
    final_drift_per_min = base_drift_per_min + obi_drift_per_min
    mu_sec = float(final_drift_per_min / 60.0)
    debug_drift = (base_drift_per_min, obi_drift_per_min, obi_signal, ewm_std_min)
    return mu_sec, debug_drift


def prob_direction(
    delta,
    tau,
    garch_cumulative_var,
    df_t,
    V_meas,
    mu=0.0,
    log_s0=None,
):
    if tau <= 0.0:
        return float(1.0 if delta > 0 else 0.0)
    mu_effective_sec = mu
    if THETA_MEAN_REVERSION > 0:
        mu_effective_sec = mu - THETA_MEAN_REVERSION * delta
    if KAPPA_SEC > 1e-9:
        expected_total_drift = (
            mu_effective_sec / KAPPA_SEC
        ) * (1.0 - math.exp(-KAPPA_SEC * tau))
    else:
        expected_total_drift = mu_effective_sec * tau
    total_signal = delta + expected_total_drift
    lambda_total_tau = FIXED_LAMBDA_SEC * tau
    jump_var_term = lambda_total_tau * (FIXED_SIGMA_JUMP ** 2)
    total_variance = (
        max(garch_cumulative_var, 1e-18)
        + max(jump_var_term, 0.0)
        + max(V_meas, 1e-18)
    )
    denom = np.sqrt(total_variance)
    if denom <= 1e-12:
        print("UYARI: 'z' SıfırDenom.")
        return 0.5
    z = total_signal / denom
    current_df = FIXED_DF_T
    try:
        if np.isnan(z) or np.isinf(z):
            print("UYARI: 'z' NaN/Inf.")
            return 0.5
        P = float(student_t.cdf(z, df=current_df))
    except Exception as e:
        print(f"UYARI: t.cdf hatası: {e}. z={z}, df={current_df}")
        P = 0.5
    return float(np.clip(P, 0.0, 1.0))



def live_binance_book():
    url = "https://api.binance.com/api/v3/ticker/bookTicker?symbol=BTCUSDT"
    r = requests.get(url, timeout=2.5, headers=UA)
    r.raise_for_status()
    j = r.json()
    bid = float(j["bidPrice"])
    ask = float(j["askPrice"])
    mid = (bid + ask) / 2.0
    bid_sz = float(j["bidQty"])
    ask_sz = float(j["askQty"])
    bid_sz = max(bid_sz, 0.0)
    ask_sz = max(ask_sz, 0.0)
    return dict(
        price=mid,
        bid=bid,
        ask=ask,
        bid_sz=bid_sz,
        ask_sz=ask_sz,
        src="BINANCE",
        inst="BTCUSDT",
        quote="USDT",
    )


def live_binance_last():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    r = requests.get(url, timeout=2.5, headers=UA)
    r.raise_for_status()
    p = float(r.json()["price"])
    return dict(
        price=p,
        bid=None,
        ask=None,
        bid_sz=None,
        ask_sz=None,
        src="BINANCE",
        inst="BTCUSDT",
        quote="USDT",
    )


def live_coinbase_book_level1():
    url = "https://api.exchange.coinbase.com/products/BTC-USD/book?level=1"
    r = requests.get(url, timeout=2.5, headers=UA)
    r.raise_for_status()
    j = r.json()
    bid = bid_sz = ask = ask_sz = mid = 0.0
    if j and "bids" in j and j["bids"] and len(j["bids"][0]) >= 2:
        bid = float(j["bids"][0][0])
        bid_sz = float(j["bids"][0][1])
    if j and "asks" in j and j["asks"] and len(j["asks"][0]) >= 2:
        ask = float(j["asks"][0][0])
        ask_sz = float(j["asks"][0][1])
    if bid > 0 and ask > 0:
        mid = (bid + ask) / 2.0
    bid_sz = max(bid_sz, 0.0)
    ask_sz = max(ask_sz, 0.0)
    return dict(
        price=mid,
        bid=bid,
        ask=ask,
        bid_sz=bid_sz,
        ask_sz=ask_sz,
        src="COINBASE",
        inst="BTC-USD",
        quote="USD",
    )


FETCHERS = {
    "BINANCE": (live_binance_book, live_binance_last),
    "COINBASE": (live_coinbase_book_level1,),
}


class PriceFeed:
    def __init__(self, interval_sec=1.0, exchanges=None):
        self.interval = interval_sec
        self.exchanges = exchanges or EXCHANGES
        self._q = queue.Queue(maxsize=10)
        self._run = False
        self._thread = None
        self.status = "INIT"
        self.last_error = None

    def _try_fetch(self):
        last_err = None
        for ex in self.exchanges:
            if ex not in FETCHERS:
                continue
            for f in FETCHERS[ex]:
                try:
                    d = f()
                    self.status = f"{d['src']} OK"
                    self.last_error = None
                    return d
                except Exception as e:
                    last_err = e
                    self.last_error = str(e)[:160]
                    continue
        self.status = "NO_DATA"
        return None

    def _run_loop(self):
        while self._run:
            t0 = time.time()
            d = self._try_fetch()
            if d is not None:
                ts = datetime.now(timezone.utc).timestamp()
                payload = (
                    ts,
                    d["price"],
                    d.get("bid"),
                    d.get("ask"),
                    d["src"],
                    d["inst"],
                    d["quote"],
                    d.get("bid_sz"),
                    d.get("ask_sz"),
                )
                try:
                    if self._q.full():
                        try:
                            self._q.get_nowait()
                        except queue.Empty:
                            pass
                    self._q.put_nowait(payload)
                except queue.Full:
                    pass
            elapsed = time.time() - t0
            sleep_time = max(0.0, self.interval - elapsed)
            time.sleep(sleep_time)

    def start(self):
        if not self._run:
            self._run = True
            self._thread = threading.Thread(
                target=self._run_loop, daemon=True
            )
            self._thread.start()

    def stop(self):
        self._run = False
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=max(self.interval * 2, 2.0))
            if self._thread.is_alive():
                print("UYARI: Fiyat beslemesi thread'i zamanında durmadı.")
        self._thread = None

    def get_latest(self, timeout=None):
        payload = None
        try:
            while not self._q.empty():
                payload = self._q.get_nowait()
        except queue.Empty:
            pass
        if payload is None and timeout is not None and timeout > 0:
            try:
                payload = self._q.get(timeout=timeout)
            except queue.Empty:
                return None
        return payload



def binance_start_price(start_ts):
    base = "https://api.binance.com/api/v3/aggTrades?symbol=BTCUSDT"
    start_ms = to_ms(start_ts)
    url_after = f"{base}&startTime={start_ms}&endTime={start_ms + 15000}&limit=1"
    try:
        r = requests.get(url_after, timeout=3.0, headers=UA)
        r.raise_for_status()
        arr = r.json()
        if isinstance(arr, list) and len(arr) > 0 and "p" in arr[0]:
            return float(arr[0]["p"]), "BINANCE aggTrades after"
    except Exception as e1:
        print(f"UYARI: Binance aggTrades after alınamadı: {e1}")
    url_before = f"{base}&startTime={start_ms - 15000}&endTime={start_ms}&limit=1000"
    try:
        r = requests.get(url_before, timeout=3.0, headers=UA)
        r.raise_for_status()
        arr = r.json()
        if isinstance(arr, list) and len(arr) > 0 and "p" in arr[-1]:
            return float(arr[-1]["p"]), "BINANCE aggTrades before"
    except Exception as e2:
        print(f"UYARI: Binance aggTrades before alınamadı: {e2}")
    kurl = (
        "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&startTime="
        f"{(start_ms // 60000) * 60000}&limit=1"
    )
    try:
        r = requests.get(kurl, timeout=3.0, headers=UA)
        r.raise_for_status()
        k = r.json()
        if isinstance(k, list) and len(k) > 0 and len(k[0]) > 1:
            return float(k[0][1]), "BINANCE kline 1m open"
    except Exception as e3:
        print(f"UYARI: Binance kline 1m open alınamadı: {e3}")
    raise RuntimeError("Binance başlangıç fiyatı hiçbir yöntemle alınamadı.")


def coinbase_start_price_exact_open(start_ts):
    bucket = int(start_ts) // 60 * 60
    start_iso = (
        datetime.fromtimestamp(bucket - 1, tz=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )
    end_iso = (
        datetime.fromtimestamp(bucket + 61, tz=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )
    url = (
        "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=60&start="
        f"{start_iso}&end={end_iso}"
    )
    try:
        r = requests.get(url, timeout=3.5, headers=UA)
        r.raise_for_status()
        arr = r.json()
        if isinstance(arr, list):
            for c in arr:
                if len(c) > 3 and int(c[0]) == bucket:
                    return float(c[3]), "COINBASE exact 1m open"
    except Exception as e:
        raise RuntimeError(f"Coinbase başlangıç fiyatı alınamadı (API Hatası: {e})")
    raise RuntimeError("Coinbase başlangıç fiyatı alınamadı (tam bucket bulunamadı)")


def fetch_start_price(exchange, start_ts):
    if exchange == "BINANCE":
        return binance_start_price(start_ts)
    elif exchange == "COINBASE":
        return coinbase_start_price_exact_open(start_ts)
    else:
        raise RuntimeError(f"Başlangıç fiyatı için desteklenmeyen borsa: {exchange}")



def binance_ohlc_1m(t_from, t_to):
    start_ms = to_ms(t_from)
    end_ms = to_ms(t_to)
    all_klines = []
    current_start_ms = start_ms
    limit = 1000
    max_requests = (int(t_to - t_from) // (limit * 60)) + 3
    request_count = 0
    while current_start_ms < end_ms and request_count < max_requests:
        request_count += 1
        url = (
            "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&startTime="
            f"{current_start_ms}&endTime={end_ms}&limit={limit}"
        )
        try:
            r = requests.get(url, timeout=5.0, headers=UA)
            r.raise_for_status()
            klines = r.json()
            if not klines or not isinstance(klines, list):
                break
            all_klines.extend(klines)
            last_ts_ms = klines[-1][0]
            current_start_ms = last_ts_ms + 60000
            if current_start_ms >= end_ms:
                break
            if len(klines) < limit:
                break
        except requests.exceptions.RequestException as e:
            print(f"Binance API hatası (1m OHLC): {e}")
            break
        time.sleep(0.3)
    out = []
    processed_ts = set()
    for k_idx, k in enumerate(all_klines if isinstance(all_klines, list) else []):
        t_open = -1
        try:
            if not isinstance(k, list) or len(k) < 5:
                continue
            t_open_ms = k[0]
            if not isinstance(t_open_ms, (int, float)):
                continue
            t_open = int(t_open_ms // 1000)
            if (
                t_open in processed_ts
                or t_open < int(t_from)
                or t_open >= int(t_to)
            ):
                continue
            processed_ts.add(t_open)
            o = float(k[1])
            h = float(k[2])
            l = float(k[3])
            c = float(k[4])
            if o <= 0 or h <= 0 or l <= 0 or c <= 0:
                continue
            out.append((t_open, o, h, l, c))
        except (ValueError, IndexError, TypeError) as parse_err:
            print(
                "UYARI: Binance mum verisi ayrıştırılamadı (index"
                f" {k_idx}): Veri={k}, Hata: {parse_err}"
            )
            continue
        except Exception as unexpected_err:
            print(
                "UYARI: Mum işlenirken beklenmedik hata (Binance, t="
                f"{t_open if t_open != -1 else 'bilinmiyor'}): {k}, Hata: {unexpected_err}"
            )
            continue
    out.sort(key=lambda x: x[0])
    return out


def coinbase_ohlc_1m(t_from, t_to):
    all_candles = []
    current_start_ts = int(t_from) // 60 * 60
    end_ts = int(t_to) // 60 * 60
    max_requests = (int(t_to - t_from) // (300 * 60)) + 3
    request_count = 0
    while current_start_ts < end_ts and request_count < max_requests:
        request_count += 1
        batch_end_ts = min(current_start_ts + 300 * 60, end_ts)
        start_iso = (
            datetime.fromtimestamp(current_start_ts, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
        end_iso = (
            datetime.fromtimestamp(batch_end_ts, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )
        url = (
            "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=60&start="
            f"{start_iso}&end={end_iso}"
        )
        try:
            r = requests.get(url, timeout=6.0, headers=UA)
            r.raise_for_status()
            candles = r.json()
            if isinstance(candles, list):
                candles.sort(key=lambda x: int(x[0]))
                all_candles.extend(candles)
            elif not isinstance(candles, list):
                print(f"UYARI: Coinbase geçersiz yanıt: {candles}")
                break
            if candles and isinstance(candles, list):
                if candles[-1] and len(candles[-1]) > 0:
                    last_candle_ts = int(candles[-1][0])
                    current_start_ts = last_candle_ts + 60
                else:
                    current_start_ts = batch_end_ts
                if current_start_ts >= end_ts:
                    break
            else:
                current_start_ts = batch_end_ts
        except requests.exceptions.RequestException as e:
            print(f"Coinbase API hatası (1m OHLC): {e}")
            break
        time.sleep(0.5)
    out = []
    processed_ts = set()
    for c_idx, c in enumerate(all_candles if isinstance(all_candles, list) else []):
        t_open = -1
        try:
            if not isinstance(c, list) or len(c) < 5:
                continue
            t_open_val = c[0]
            if not isinstance(t_open_val, (int, float)):
                continue
            t_open = int(t_open_val)
            if (
                t_open in processed_ts
                or t_open < int(t_from)
                or t_open >= int(t_to)
            ):
                continue
            processed_ts.add(t_open)
            o = float(c[3])
            h = float(c[2])
            l = float(c[1])
            cc = float(c[4])
            if o <= 0 or h <= 0 or l <= 0 or cc <= 0:
                continue
            out.append((t_open, o, h, l, cc))
        except (ValueError, IndexError, TypeError) as parse_err:
            print(
                "UYARI: Coinbase mum verisi ayrıştırılamadı (index"
                f" {c_idx}): Veri={c}, Hata: {parse_err}"
            )
            continue
        except Exception as unexpected_err:
            print(
                "UYARI: Mum işlenirken beklenmedik hata (Coinbase, t="
                f"{t_open if t_open != -1 else 'bilinmiyor'}): {c}, Hata: {unexpected_err}"
            )
            continue
    out.sort(key=lambda x: x[0])
    return out


def get_ohlc(exchange, t_from, t_to):
    duration_minutes = int(t_to - t_from) // 60
    print(f"Geçmiş OHLC çekiliyor ({duration_minutes} dakika)...")
    t_start_fetch = time.time()
    result = None
    try:
        if exchange == "BINANCE":
            result = binance_ohlc_1m(t_from, t_to)
        elif exchange == "COINBASE":
            result = coinbase_ohlc_1m(t_from, t_to)
        else:
            raise ValueError("Desteklenmeyen borsa")
    except Exception as e:
        print(f"OHLC çekme sırasında kritik hata: {e}")
        return None
    if result is not None:
        expected_minutes = max(0, duration_minutes)
        result = [c for c in result if t_from <= c[0] < t_to]
        print(
            f"OHLC çekme tamamlandı ({len(result)}/{expected_minutes} mum,"
            f" {time.time() - t_start_fetch:.1f} saniye)."
        )
        if expected_minutes > 20 and len(result) < expected_minutes * 0.8:
            print(
                f"UYARI: Beklenenden ({expected_minutes}) önemli ölçüde az mum ({len(result)}) alındı."
            )
    else:
        print(f"OHLC çekme başarısız ({time.time() - t_start_fetch:.1f} saniye).")
    return result



def extract_sigma_star(ohlc_short, start_bucket, long_term_hv_var_sec):
    if ohlc_short is None or len(ohlc_short) < 5:
        print("UYARI: extract_sigma_star için yetersiz OHLC.")
        return long_term_hv_var_sec
    rs_star = None
    RS_valid_short = []
    for (t, o, h, l, c) in ohlc_short:
        try:
            if all(v > 0 for v in [o, h, l, c]):
                current_rs = rs_variance(o, h, l, c)
                RS_valid_short.append(current_rs)
                if int(t) == start_bucket:
                    rs_star = current_rs
        except Exception:
            continue
    fallback_sigma_star2 = long_term_hv_var_sec
    sigma_star2 = fallback_sigma_star2
    if rs_star is None or rs_star <= 0:
        if RS_valid_short:
            try:
                rs_series = pd.Series(RS_valid_short).dropna()
                if not rs_series.empty:
                    rs_star_median = float(rs_series.median())
                    min_rs = fallback_sigma_star2 * 60 * 0.1
                    max_rs = fallback_sigma_star2 * 60 * 10
                    if not pd.isna(rs_star_median):
                        rs_star_median_clipped = np.clip(
                            rs_star_median, min_rs, max_rs
                        )
                        if rs_star_median_clipped > 0:
                            sigma_star2 = max(
                                rs_star_median_clipped / 60.0,
                                fallback_sigma_star2 * 0.1,
                            )
            except Exception as median_err:
                print(f"UYARI: Sigma_star2 median hatası: {median_err}")
    else:
        sigma_star2 = max(rs_star / 60.0, fallback_sigma_star2 * 0.1)
    return sigma_star2


def update_plot(timestamps, p_up_hist, p_down_hist, filename=PLOT_FILENAME):
    if not ENABLE_PLOTTING or not timestamps or len(timestamps) < 2:
        return
    try:
        plt.figure(figsize=(10, 4))
        times_dt = [
            datetime.fromtimestamp(ts, tz=ZoneInfo(START_TZ)) for ts in list(timestamps)
        ]
        p_up_percent = [p * 100 for p in list(p_up_hist)]
        p_down_percent = [p * 100 for p in list(p_down_hist)]
        plt.plot(times_dt, p_up_percent, label="P(Yüksek)", color="green", linewidth=1.5)
        plt.plot(
            times_dt, p_down_percent, label="P(Düşük)", color="red", linewidth=1.5
        )
        plt.ylabel("Olasılık (%)")
        plt.title("BTC 15dk Yön Olasılığı Zaman Serisi")
        plt.ylim(-5, 105)
        plt.grid(True, linestyle="--", alpha=0.6)
        plt.legend(loc="best")
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
        plt.gca().xaxis.set_major_locator(plt.MaxNLocator(10))
        plt.xticks(rotation=30, ha="right")
        plt.axhline(50, color="grey", linestyle=":", linewidth=1)
        plt.axhline(0, color="black", linestyle="-", linewidth=0.5)
        plt.axhline(100, color="black", linestyle="-", linewidth=0.5)
        plt.tight_layout()
        plt.savefig(filename, dpi=90, bbox_inches="tight")
        plt.close()
    except Exception as plot_err:
        print(f"UYARI: Grafik çizilemedi: {plot_err}")
    finally:
        if plt:
            plt.close("all")



def main():
    long_term_hv_var_sec = calculate_long_term_hv(exchange=EXCHANGES[0])
    start_dt_local = datetime.strptime(START_TIME_LOCAL, "%Y-%m-%d %H:%M:%S").replace(
        tzinfo=ZoneInfo(START_TZ)
    )
    t0 = start_dt_local.astimezone(timezone.utc).timestamp()
    log_s0 = None
    Tend = t0 + int(HORIZON_MIN * 60)
    feed = PriceFeed(interval_sec=POLL_SEC, exchanges=EXCHANGES)
    feed.start()
    s0 = None
    s0_src = ""
    obi_live = 0.5
    obi_smoothed = 0.5
    obi_history = deque(maxlen=OBI_SMOOTHING_SECONDS)
    raw_returns_drift = None
    sigma_star2 = long_term_hv_var_sec
    garch_result = None
    df_t = FIXED_DF_T
    mu_sec = 0.0
    debug_drift = (0.0, 0.0, 0.0, 0.0)
    garch_cumulative_var = long_term_hv_var_sec * HORIZON_MIN * 60
    src = inst = quote = "", "", ""
    plot_timestamps = deque(maxlen=PLOT_HISTORY_POINTS)
    plot_p_up_hist = deque(maxlen=PLOT_HISTORY_POINTS)
    plot_p_down_hist = deque(maxlen=PLOT_HISTORY_POINTS)
    last_plot_time = 0
    print("Başlatılıyor...")
    now_t_init = time.time()
    it_init = feed.get_latest(timeout=15.0)
    if it_init is None:
        print("Başlangıç fiyatı alınamadı (Timeout)! Feed durumu:", feed.status)
        feed.stop()
        return
    now_t_init, _, _, _, src, _, _, _, _ = it_init
    hist_from_init = now_t_init - HIST_MINUTES_GARCH * 60.0
    try:
        ohlc_garch = get_ohlc(src, hist_from_init, now_t_init)
    except Exception as e:
        print(f"İlk OHLC çekme hatası: {e}")
        feed.stop()
        return
    if ohlc_garch is None:
        print("İlk OHLC verisi alınamadı.")
        feed.stop()
        return
    print("İlk GARCH modeli uyduruluyor...")
    garch_result = fit_garch_model(ohlc_garch)
    if garch_result is None:
        print("UYARI: İlk GARCH uydurulamadı.")
    else:
        print(f"İlk GARCH modeli uyduruldu (df={FIXED_DF_T:.1f} kullanılacak).")
    print("İlk drift ve sigma_star hesaplanıyor...")
    ohlc_drift = ohlc_garch[-(HIST_MINUTES_DRIFT + 5) :] if ohlc_garch else None
    start_bucket = int(t0) // 60 * 60
    sigma_star2 = extract_sigma_star(ohlc_drift, start_bucket, long_term_hv_var_sec)
    raw_returns_drift = get_raw_returns_from_ohlc(ohlc_drift)
    it_init_obi = feed.get_latest(timeout=1.0)
    if it_init_obi:
        _, _, _, _, _, _, _, bid_sz_init, ask_sz_init = it_init_obi
        if (
            bid_sz_init is not None
            and ask_sz_init is not None
            and bid_sz_init >= 0
            and ask_sz_init >= 0
        ):
            denom_obi_init = bid_sz_init + ask_sz_init
            if denom_obi_init > 1e-12:
                obi_live = bid_sz_init / denom_obi_init
    obi_history.append(obi_live)
    obi_smoothed = obi_live
    mu_sec, debug_drift = estimate_drift(
        raw_returns_drift, obi_smoothed, DRIFT_OBI_WEIGHT
    )
    print("Başlatma tamamlandı, panel başlıyor...")
    time.sleep(1)
    last_min_bucket = -1
    last_p = 0.0

    while True:
        it = feed.get_latest(timeout=POLL_SEC * 1.5)
        if it is None:
            if feed._run:
                clear_output(wait=True)
                print(
                    "Canlı fiyat bekleniyor (veri akışı yok)... Feed durumu:",
                    feed.status,
                    "Hata:",
                    feed.last_error,
                )
                now_t_stale = time.time()
                tau = max(0.0, Tend - now_t_stale)
                if tau <= 0:
                    break
                try:
                    garch_cumulative_var_fallback, _ = get_garch_forecast(
                        garch_result, tau, long_term_hv_var_sec
                    )
                    garch_cumulative_var = garch_cumulative_var_fallback
                    if last_p > 0 and s0 > 0 and log_s0 is not None:
                        delta_stale = math.log(last_p) - log_s0
                        V_meas_stale = float(
                            (sigma_star2 if sigma_star2 else long_term_hv_var_sec)
                            + 0.0
                        )
                        mu_effective_sec_stale = (
                            mu_sec - THETA_MEAN_REVERSION * delta_stale
                        )
                        P_up = prob_direction(
                            delta_stale,
                            tau,
                            garch_cumulative_var,
                            FIXED_DF_T,
                            V_meas_stale,
                            mu=mu_effective_sec_stale,
                            log_s0=log_s0,
                        )
                        P_down = 1.0 - P_up
                        print("=== BTC 15 dk Yön Olasılığı (v12 - Hibrit) ===")
                        print(f"Kaynak/Enstrüman:   {src} / {inst} (ESKİ VERİ)")
                        print(
                            "Başlangıç (yerel):  "
                            f"{dt_loc(t0).strftime('%Y-%m-%d %H:%M:%S')}  [{START_TZ}]"
                        )
                        print(
                            f"Başlangıç fiyatı:   {s0:,.2f} {quote}  (S_*)  [{s0_src}]"
                        )
                        print(
                            f"Hedef bitiş:        {dt_loc(Tend).strftime('%H:%M:%S')}  [{START_TZ}]"
                        )
                        print("-")
                        print(
                            f"Şimdi (yerel):      {dt_loc(now_t_stale).strftime('%Y-%m-%d %H:%M:%S')} (Veri Yok)"
                        )
                        print(
                            f"Anlık fiyat (WMP):  {last_p:,.2f} {quote} (Son bilinen)"
                        )
                        print(
                            f"Emir Deft. Dng (OBI): {obi_live*100.0:5.2f}% Alış (Son Canlı)"
                        )
                        print(
                            f"Yumuşatılmış OBI:   {obi_smoothed*100.0:5.2f}% Alış ({len(obi_history)} sn)"
                        )
                        print(
                            f"Tahmini Drift (sn):   {mu_sec:,.8f} (Son bilinen, Ağırlık: {DRIFT_OBI_WEIGHT})"
                        )
                        print(f"Kalan süre:         {fmt_mmss(tau)}  (mm:ss)")
                        print(
                            "P(Yüksek) / P(Düşük):  "
                            f"{100.0*P_up:5.2f}%  /  {100.0*P_down:5.2f}%"
                        )
                    else:
                        P_up, P_down = 0.5, 0.5
                        print("Panel güncellenemiyor (geçerli fiyat yok).")
                except Exception as stale_e:
                    print(f"Eski veriyle panel güncellenirken hata: {stale_e}")
                    P_up, P_down = 0.5, 0.5
                current_time = time.time()
                if ENABLE_PLOTTING and current_time - last_plot_time >= PLOT_UPDATE_SEC:
                    plot_timestamps.append(current_time)
                    plot_p_up_hist.append(P_up)
                    plot_p_down_hist.append(P_down)
                    update_plot(plot_timestamps, plot_p_up_hist, plot_p_down_hist)
                    last_plot_time = current_time
                time.sleep(POLL_SEC)
                continue
            else:
                print("Fiyat beslemesi durdu.")
                break

        now_t, p_mid, bid, ask, src, inst, quote, bid_sz, ask_sz = it
        if p_mid is None or p_mid <= 0:
            p_mid = last_p
        if last_p <= 0 and p_mid > 0:
            last_p = p_mid
        if s0 is None:
            try:
                s0, s0_src = fetch_start_price(src, t0)
                if s0 <= 0:
                    raise ValueError("Başlangıç fiyatı sıfır veya negatif.")
                log_s0 = math.log(s0)
            except Exception as e:
                clear_output(wait=True)
                print(f"Başlangıç fiyatı alınamadı! Hata: {e}")
                feed.stop()
                return
        if log_s0 is None:
            print("Kritik Hata: log_s0 hesaplanamadı.")
            feed.stop()
            return
        p = p_mid
        current_obi_live = obi_live
        if (
            bid is not None
            and ask is not None
            and bid > 0
            and ask > 0
            and bid_sz is not None
            and ask_sz is not None
            and bid_sz >= 0
            and ask_sz >= 0
        ):
            denom_wmp = bid_sz + ask_sz
            if denom_wmp > 1e-12:
                try:
                    wmp_calc = (bid * ask_sz + ask * bid_sz) / denom_wmp
                    obi_calc = bid_sz / denom_wmp
                    if (
                        not pd.isna(wmp_calc)
                        and not pd.isna(obi_calc)
                        and not np.isinf(wmp_calc)
                        and not np.isinf(obi_calc)
                        and wmp_calc > 0
                    ):
                        p = wmp_calc
                        current_obi_live = obi_calc
                    else:
                        current_obi_live = 0.5
                except (ZeroDivisionError, OverflowError):
                    current_obi_live = 0.5
            else:
                current_obi_live = 0.5
        else:
            current_obi_live = 0.5
        obi_live = current_obi_live
        if p > 0:
            last_p = p
        else:
            p = last_p
        if p <= 0:
            print(f"UYARI: Geçerli fiyat (p) sıfır veya negatif: {p}.")
            continue
        tau = max(0.0, Tend - now_t)
        obi_history.append(obi_live)
        if len(obi_history) > 0:
            obi_smoothed = sum(obi_history) / len(obi_history)
        else:
            obi_smoothed = 0.5
        cur_min_bucket = int(now_t) // 60
        if cur_min_bucket != last_min_bucket:
            print(f"\nYeni dakika ({cur_min_bucket}), yavaş parametreler güncelleniyor...")
            new_ohlc_garch = None
            update_successful = False
            try:
                hist_from_garch = now_t - HIST_MINUTES_GARCH * 60.0
                new_ohlc_garch = get_ohlc(src, hist_from_garch, now_t)
                if new_ohlc_garch and len(new_ohlc_garch) >= HIST_MINUTES_GARCH * 0.8:
                    print("GARCH modeli yeniden uyduruluyor...")
                    new_garch_result = fit_garch_model(new_ohlc_garch)
                    if new_garch_result:
                        garch_result = new_garch_result
                        print("GARCH modeli güncellendi.")
                        update_successful = True
                    else:
                        print("UYARI: GARCH modeli bu dakika uydurulamadı.")
                    if update_successful:
                        ohlc_drift_now = new_ohlc_garch[-(HIST_MINUTES_DRIFT + 5) :]
                        sigma_star2_new = extract_sigma_star(
                            ohlc_drift_now, start_bucket, long_term_hv_var_sec
                        )
                        raw_returns_drift_new = get_raw_returns_from_ohlc(
                            ohlc_drift_now
                        )
                        if raw_returns_drift_new is not None and sigma_star2_new > 0:
                            raw_returns_drift = raw_returns_drift_new
                            sigma_star2 = sigma_star2_new
                            print("Drift verisi (raw) ve Sigma_star2 güncellendi.")
                        else:
                            print("UYARI: Drift verisi/Sigma_star2 güncellenemedi.")
                            raw_returns_drift = None
                else:
                    print(
                        "UYARI: OHLC çekilemedi veya yetersiz ("
                        f"{len(new_ohlc_garch) if new_ohlc_garch else 0} mum)."
                    )
            except Exception as e:
                print(f"Yavaş parametre güncelleme hatası: {e}")
                raw_returns_drift = None
            last_min_bucket = cur_min_bucket

        try:
            mu_sec, debug_drift = estimate_drift(
                raw_returns_drift, obi_smoothed, DRIFT_OBI_WEIGHT
            )
            garch_cumulative_var, _ = get_garch_forecast(
                garch_result, tau, long_term_hv_var_sec
            )
            df_t = FIXED_DF_T
        except Exception as e:
            print(f"Hızlı güncelleme (drift/GARCH forecast) hatası: {e}")
            mu_sec, debug_drift = 0.0, (0.0, 0.0, 0.0, 0.0)
            garch_cumulative_var = long_term_hv_var_sec * max(tau, 1.0)
            df_t = FIXED_DF_T

        sigma_micro2 = 0.0
        if bid is not None and ask is not None and p > 0 and bid > 0 and ask > 0:
            try:
                if bid < ask + p * 0.001:
                    half_spread_rel = 0.5 * (ask - bid) / p
                    max_micro_var = (
                        garch_cumulative_var / max(tau, 1) * 0.1
                        if garch_cumulative_var > 0
                        else (0.005 / 2) ** 2
                    )
                    sigma_micro2 = min(
                        max(half_spread_rel ** 2, 0.0), max(max_micro_var, 1e-12)
                    )
            except Exception:
                sigma_micro2 = 0.0
        current_sigma_star2 = (
            sigma_star2 if sigma_star2 is not None and sigma_star2 > 0 else long_term_hv_var_sec
        )
        V_meas = float(current_sigma_star2 + sigma_micro2)
        try:
            log_p = math.log(p)
            delta = log_p - log_s0
        except (ValueError, TypeError):
            delta = 0.0
            print(f"UYARI: Delta hesaplanırken log hatası. p={p}, s0={s0}")
        mu_effective_sec = mu_sec - THETA_MEAN_REVERSION * delta
        P_up = prob_direction(
            delta,
            tau,
            garch_cumulative_var,
            FIXED_DF_T,
            V_meas,
            mu=mu_effective_sec,
            log_s0=log_s0,
        )
        P_down = 1.0 - P_up
        plot_timestamps.append(now_t)
        plot_p_up_hist.append(P_up)
        plot_p_down_hist.append(P_down)
        clear_output(wait=True)
        print("=== BTC 15 dk Yön Olasılığı (v12 - Hibrit) ===")
        print(f"Kaynak/Enstrüman:   {src} / {inst}")
        print(
            f"Başlangıç (yerel):  {dt_loc(t0).strftime('%Y-%m-%d %H:%M:%S')}  [{START_TZ}]"
        )
        print(f"Başlangıç fiyatı:   {s0:,.2f} {quote}  (S_*)  [{s0_src}]")
        print(f"Hedef bitiş:        {dt_loc(Tend).strftime('%H:%M:%S')}  [{START_TZ}]")
        print("-")
        print(f"Şimdi (yerel):      {dt_loc(now_t).strftime('%Y-%m-%d %H:%M:%S')}")
        if (bid is not None) and (ask is not None):
            print(f"Anlık fiyat (WMP):  {p:,.2f} {quote}  [bid {bid:,.2f} / ask {ask:,.2f}]")
        else:
            print(f"Anlık fiyat:        {p:,.2f} {quote}")
        print(f"Emir Deft. Dng (OBI): {obi_live*100.0:5.2f}% Alış  <-- (CANLI)")
        print(
            f"Yumuşatılmış OBI:   {obi_smoothed*100.0:5.2f}% Alış ({len(obi_history)} sn)"
        )
        print(
            f"Tahmini Drift (sn):   {mu_sec:,.8f}     <-- (OBI ile, Ağırlık: {DRIFT_OBI_WEIGHT})"
        )
        print(
            f"Ort. Dönüşlü Drift(sn):{mu_effective_sec:,.8f}     <-- (theta={THETA_MEAN_REVERSION:.1e})"
        )
        print(f"Kalan süre:         {fmt_mmss(tau)}  (mm:ss)")
        print(
            f"P(Yüksek) / P(Düşük):  {100.0*P_up:5.2f}%  /  {100.0*P_down:5.2f}%"
        )
        print("-")
        garch_desc = f"GJR-GARCH({GARCH_P},{GARCH_O},{GARCH_Q})-{GARCH_DIST}"
        print(
            "Model: Decay(k="
            f"{KAPPA_SEC:.1e})+MeanRev(th={THETA_MEAN_REVERSION:.1e})+{garch_desc} Vol(>="
            f"{FALLBACK_ANNUAL_VOL*100:.0f}%)+JumpRisk+t(df={FIXED_DF_T:.1f})"
        )
        print("\n--- gemini ile paylaşılacak anlık veriler (v12) ---")
        print("SİNYAL (PAY) - CANLI HESAPLAMA:")
        print(f"  delta = {delta:,.8f}  # log(p) - log(s0)")
        print(f"  mu_sec = {mu_sec:,.10f}  # Anlık Drift (sn, Yumuşatılmış OBI ile)")
        print(
            f"  mu_effective_sec = {mu_effective_sec:,.10f} # Ort. Dönüşlü Anlık Drift (sn)"
        )
        print(f"  tau = {tau:,.2f}  # Kalan saniye")
        expected_total_drift_debug = 0.0
        if KAPPA_SEC > 1e-9:
            expected_total_drift_debug = (
                mu_effective_sec / KAPPA_SEC
            ) * (1.0 - math.exp(-KAPPA_SEC * tau))
        else:
            expected_total_drift_debug = mu_effective_sec * tau
        print(
            "  Beklenen Drift Etkisi (Bozunan+Etkili, k="
            f"{KAPPA_SEC:.2e}, th={THETA_MEAN_REVERSION:.1e}) = {expected_total_drift_debug:,.8f}"
        )
        print(
            f"  (Karşılaştırma için mu_effective*tau = {mu_effective_sec*tau:,.8f})"
        )
        base_drift_min, obi_drift_min, obi_signal, ewm_std_min = debug_drift
        print("  Drift Bileşenleri (dk başına, Yumuşatılmış OBI ile):")
        print(f"    base_drift_min (geçmiş {HIST_MINUTES_DRIFT}dk) = {base_drift_min:,.10f}")
        print(f"    obi_drift_min (yumuşatılmış) = {obi_drift_min:,.10f}")
        print("  Drift Detayları (Yumuşatılmış OBI ile):")
        print(f"    OBI_smoothed = {obi_smoothed:,.4f} -> obi_signal = {obi_signal:,.4f}")
        print(f"    OBI_live = {obi_live:,.4f} (Karşılaştırma için)")
        print(f"    ewm_std_min ({HIST_MINUTES_DRIFT}dk raw) = {ewm_std_min:,.10f}")
        print(f"    OBI_WEIGHT = {DRIFT_OBI_WEIGHT:,.2f}")
        print("\nGÜRÜLTÜ (PAYDA) - DİNAMİK (v12):")
        print(
            f"  GARCH Tahmini ({garch_desc}, {GARCH_AGG_MIN}min ret, {HIST_MINUTES_GARCH}dk OHLC):"
        )
        print(
            f"    Kümülatif Varyans Tahmini (tau={tau:.0f}s) = {garch_cumulative_var:,.12f}"
        )
        garch_annual_vol = (
            math.sqrt(garch_cumulative_var / max(tau, 1e-6) * SECONDS_PER_YEAR) * 100
            if tau > 0
            else 0.0
        )
        print(f"      -> Yıllık Vol Tahmini ~{garch_annual_vol:.1f}%")
        print(
            f"    Uzun Vadeli Taban Varyans (saniye) = {long_term_hv_var_sec:,.12f} (~"
            f"{math.sqrt(long_term_hv_var_sec * SECONDS_PER_YEAR)*100:.1f}% HV)"
        )
        lambda_total_tau = FIXED_LAMBDA_SEC * tau
        jump_var_term_debug = lambda_total_tau * (FIXED_SIGMA_JUMP ** 2)
        print("  SABİT Sıçrama Riski (v12):")
        print(
            f"    Beklenen Sıçrama Varyansı (tau={tau:.0f}s) = {jump_var_term_debug:,.12f} (lam={FIXED_LAMBDA_SEC:.2e}/s, sigJ={FIXED_SIGMA_JUMP:.3f})"
        )
        print("  ÖLÇÜM VARYANSI - DİNAMİK:")
        print(f"    V_meas = {V_meas:,.12f}  # Toplam ölçüm varyansı")
        print(f"      sigma_star2 (başlangıç) = {current_sigma_star2:,.12f}")
        print(f"      sigma_micro2 (anlık)  = {sigma_micro2:,.12f}")
        print("\nOLASILIK HESAPLAMA (v12):")
        total_variance_debug = (
            max(garch_cumulative_var, 1e-18)
            + max(jump_var_term_debug, 0.0)
            + max(V_meas, 1e-18)
        )
        calc_denom = math.sqrt(total_variance_debug)
        calc_z = (
            (delta + expected_total_drift_debug) / calc_denom
            if calc_denom > 1e-12
            else 0.0
        )
        print("  z = (delta + decayed_eff_drift) / sqrt(garch_var + jump_var + V_meas)")
        print(
            f"  z = ({delta:.6f} + {expected_total_drift_debug:.6f}) / {calc_denom:.6f} = {calc_z:.4f}"
        )
        print(f"  P(Yüksek) = t.cdf(z={calc_z:.4f}, df={FIXED_DF_T:.2f}) = {P_up:.4f}")
        current_time_plot = time.time()
        if ENABLE_PLOTTING and current_time_plot - last_plot_time >= PLOT_UPDATE_SEC:
            print("\nGrafik güncelleniyor...")
            update_plot(plot_timestamps, plot_p_up_hist, plot_p_down_hist)
            last_plot_time = current_time_plot
        if now_t >= Tend - 1e-6:
            break

    feed.stop()
    clear_output(wait=True)
    if last_p > 0 and s0 > 0:
        try:
            log_last_p = math.log(last_p)
            log_s0 = math.log(s0)
            outcome = "YUKARI" if log_last_p > log_s0 else "AŞAĞI"
        except ValueError:
            outcome = "BELİRSİZ (Log Hatası)"
    else:
        outcome = "BELİRSİZ (Geçersiz Fiyat)"
    print("=== Sonuç ===")
    print(f"Kaynak/Enstrüman:   {src} / {inst}")
    print(f"Başlangıç (yerel):  {dt_loc(t0).strftime('%Y-%m-%d %H:%M:%S')}  [{START_TZ}]")
    print(f"S_*:                {s0:.2f} {quote}")
    print(f"S_T (son WMP):      {last_p:,.2f} {quote}")
    print(f"Gerçekleşen:        {outcome}")
    if ENABLE_PLOTTING:
        print("\nSon olasılık grafiği oluşturuluyor...")
        update_plot(
            plot_timestamps,
            plot_p_up_hist,
            plot_p_down_hist,
            filename="final_" + PLOT_FILENAME,
        )


if __name__ == "__main__":
    missing_libs = []
    try:
        import arch  # noqa: F401
    except ImportError:
        missing_libs.append("arch")
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        missing_libs.append("matplotlib")
    try:
        from collections import deque as _deque_test  # noqa: F401
    except ImportError:
        missing_libs.append("collections")
    if missing_libs:
        if "matplotlib" in missing_libs:
            ENABLE_PLOTTING = False
        if "arch" in missing_libs:
            print(
                "HATA: 'arch' kütüphanesi bulunamadı. 'pip install arch matplotlib' komutlarıyla yükleyin."
            )
        if "collections" in missing_libs:
            print("HATA: Standart 'collections' modülü bulunamadı.")
        print(
            "UYARI: Eksik kütüphaneler:",
            ", ".join(m for m in missing_libs if m != "matplotlib"),
        )
        if not ENABLE_PLOTTING:
            print("Grafik çizimi devre dışı bırakıldı.")
    feed_instance = None
    try:
        main()
    except KeyboardInterrupt:
        clear_output(wait=True)
        print("\nKesildi.")
    except Exception as e:
        feed_instance = None
        try:
            if "feed" in locals() and isinstance(locals()["feed"], PriceFeed):
                feed_instance = locals()["feed"]
            elif "feed" in globals() and isinstance(globals()["feed"], PriceFeed):
                feed_instance = globals()["feed"]
            if feed_instance and hasattr(feed_instance, "_run") and feed_instance._run:
                print("Hata oluştu, fiyat beslemesi durduruluyor...")
                feed_instance.stop()
        except Exception as stop_err:
            print(f"Fiyat beslemesini durdururken ek hata: {stop_err}")
        print("\n--- CİDDİ HATA ---")
        print(f"Hata Tipi: {type(e).__name__}")
        print(f"Açıklama: {e}")
        import traceback

        traceback.print_exc()


