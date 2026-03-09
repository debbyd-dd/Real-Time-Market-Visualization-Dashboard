"""
╔══════════════════════════════════════════════════════════════════════════╗
║         REAL-TIME MARKET FLOW VISUALIZATION DASHBOARD                   ║
║                                                                          ║
║   • Live WebSocket data streaming simulation                             ║
║   • Animated orb/particle markers with physics-based movement            ║
║   • Dynamic canvas scaling (auto-adjust Y-axis, no clipping/flicker)     ║
║   • Outline mode for intra-territory reversals                           ║
║   • Threshold-based sizing with smooth transitions                       ║
║   • Low-latency redraws optimized for bursty updates                     ║
║                                                                          ║
║   Version: 3.0.0 (Plotly 6.x compatible)                                ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import time
import math
import hashlib
import colorsys
import queue
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from enum import Enum
from collections import deque


# ═══════════════════════════════════════════════════════════════
# SECTION 1: PAGE CONFIG (must be first Streamlit command)
# ═══════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Real-Time Market Flow",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# ═══════════════════════════════════════════════════════════════
# SECTION 2: CONFIGURATION & DATA MODELS
# ═══════════════════════════════════════════════════════════════

class MarkerState(Enum):
    GROWING = "growing"
    SHRINKING = "shrinking"
    DRIFTING = "drifting"
    FROZEN = "frozen"
    PULSING = "pulsing"
    OUTLINE = "outline"
    FADING = "fading"
    EXPLODING = "exploding"


class SignalType(Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    CAUTIOUS_BUY = "cautious_buy"
    NEUTRAL = "neutral"
    CAUTIOUS_SELL = "cautious_sell"
    SELL = "sell"
    STRONG_SELL = "strong_sell"
    REVERSAL = "reversal"


@dataclass
class DashboardConfig:
    """Master configuration"""
    canvas_width: int = 1200
    canvas_height: int = 650
    update_interval_ms: int = 1500
    transition_duration_ms: int = 800
    max_markers: int = 50
    trail_length: int = 20

    # Scaling
    y_axis_padding_pct: float = 0.08
    y_axis_smoothing_factor: float = 0.15
    anti_flicker_threshold: float = 0.02
    scale_lock_duration_seconds: float = 2.0

    # Marker sizing thresholds
    size_min: int = 6
    size_max: int = 30
    size_threshold_low: float = 0.3
    size_threshold_mid: float = 0.6
    size_threshold_high: float = 0.85

    # Colors
    color_strong_buy: str = "#00FF88"
    color_buy: str = "#00CC66"
    color_cautious: str = "#FFD700"
    color_neutral: str = "#888888"
    color_sell: str = "#FF6B6B"
    color_strong_sell: str = "#FF0040"
    color_reversal: str = "#FF00FF"
    color_outline: str = "#FFFFFF"
    color_background: str = "#0a0a1a"
    color_grid: str = "#1a1a2e"

    # Physics
    drift_speed: float = 0.3
    drift_randomness: float = 0.15
    bounce_factor: float = 0.7
    gravity: float = 0.02
    friction: float = 0.98

    # Instruments
    instruments: List[str] = field(default_factory=lambda: [
        "BTC/USD", "ETH/USD", "SOL/USD", "BNB/USD", "XRP/USD",
        "ADA/USD", "AVAX/USD", "DOT/USD", "MATIC/USD", "LINK/USD",
        "ATOM/USD", "UNI/USD", "AAVE/USD", "ARB/USD", "OP/USD",
        "DOGE/USD", "SHIB/USD", "LTC/USD", "FIL/USD", "APT/USD",
    ])


@dataclass
class MarkerData:
    """Single animated marker/orb"""
    id: str
    instrument: str
    x: float = 0.0
    y: float = 0.0
    size: float = 20.0
    target_size: float = 20.0
    color: str = "#00FF88"
    target_color: str = "#00FF88"
    opacity: float = 0.85
    target_opacity: float = 0.85
    state: str = "drifting"
    signal: str = "neutral"
    flow_direction: str = "neutral"

    # Physics
    vx: float = 0.0
    vy: float = 0.0
    ax: float = 0.0
    ay: float = 0.0

    # Data
    price: float = 0.0
    delta: float = 0.0
    delta_pct: float = 0.0
    volume_flow: float = 0.0
    flow_intensity: float = 0.0
    momentum: float = 0.0

    # State
    is_outline: bool = False
    is_frozen: bool = False
    freeze_until: float = 0.0
    pulse_phase: float = 0.0
    trail: List[Tuple[float, float]] = field(default_factory=list)
    age_ticks: int = 0
    last_update: float = field(default_factory=time.time)

    # Territory
    territory_high: float = 0.0
    territory_low: float = 0.0
    territory_center: float = 0.0
    in_reversal: bool = False
    reversal_count: int = 0


@dataclass
class AxisState:
    """Dynamic Y-axis state with anti-flicker"""
    current_min: float = 0.0
    current_max: float = 100.0
    target_min: float = 0.0
    target_max: float = 100.0
    locked_until: float = 0.0
    smoothing_buffer: deque = field(
        default_factory=lambda: deque(maxlen=10)
    )


# ═══════════════════════════════════════════════════════════════
# SECTION 3: MARKET DATA SIMULATOR
# ═══════════════════════════════════════════════════════════════

class MarketDataSimulator:
    """
    High-fidelity market data simulator.
    Phase 1: Synthetic data with realistic statistical properties.
    Phase 2: Replace with live WebSocket feed.
    """

    def __init__(self, config: DashboardConfig):
        self.config = config
        self.instruments = {}
        self.tick_count = 0
        self.regime = "normal"
        self.regime_duration = 0
        self._initialize_instruments()

    def _initialize_instruments(self):
        base_prices = {
            "BTC/USD": 67500, "ETH/USD": 3450, "SOL/USD": 178,
            "BNB/USD": 605, "XRP/USD": 0.62, "ADA/USD": 0.48,
            "AVAX/USD": 38.5, "DOT/USD": 7.8, "MATIC/USD": 0.72,
            "LINK/USD": 18.5, "ATOM/USD": 9.2, "UNI/USD": 12.8,
            "AAVE/USD": 108, "ARB/USD": 1.15, "OP/USD": 2.85,
            "DOGE/USD": 0.165, "SHIB/USD": 0.000028, "LTC/USD": 84,
            "FIL/USD": 5.8, "APT/USD": 9.5,
        }

        volatilities = {
            "BTC/USD": 0.015, "ETH/USD": 0.020, "SOL/USD": 0.035,
            "BNB/USD": 0.018, "XRP/USD": 0.025, "ADA/USD": 0.028,
            "AVAX/USD": 0.032, "DOT/USD": 0.030, "MATIC/USD": 0.035,
            "LINK/USD": 0.028, "ATOM/USD": 0.030, "UNI/USD": 0.032,
            "AAVE/USD": 0.025, "ARB/USD": 0.040, "OP/USD": 0.038,
            "DOGE/USD": 0.045, "SHIB/USD": 0.055, "LTC/USD": 0.022,
            "FIL/USD": 0.035, "APT/USD": 0.038,
        }

        for instrument in self.config.instruments:
            price = base_prices.get(instrument, 100)
            vol = volatilities.get(instrument, 0.025)

            self.instruments[instrument] = {
                'price': price,
                'prev_price': price,
                'base_price': price,
                'volatility': vol,
                'trend': np.random.uniform(-0.3, 0.3),
                'trend_strength': np.random.uniform(0.1, 0.5),
                'mean_reversion_speed': np.random.uniform(0.01, 0.05),
                'volume_base': np.random.uniform(50, 500),
                'volume_current': np.random.uniform(50, 500),
                'momentum': 0.0,
                'momentum_history': deque(maxlen=50),
                'price_history': deque(maxlen=200),
                'delta_history': deque(maxlen=100),
                'flow_accumulator': 0.0,
                'territory_high': price * 1.02,
                'territory_low': price * 0.98,
                'territory_center': price,
                'correlation_group': np.random.randint(0, 4),
                'regime_sensitivity': np.random.uniform(0.5, 1.5),
            }

    def _update_regime(self):
        self.regime_duration += 1
        if self.regime_duration > np.random.randint(30, 100):
            regimes = ["normal", "trending_up", "trending_down",
                       "volatile", "calm", "reversal"]
            weights = [0.30, 0.15, 0.15, 0.15, 0.15, 0.10]
            self.regime = np.random.choice(regimes, p=weights)
            self.regime_duration = 0

    def _generate_correlated_noise(self, n: int) -> np.ndarray:
        market_component = np.random.normal(0, 0.5)
        group_components = {i: np.random.normal(0, 0.3) for i in range(4)}
        noise = np.random.normal(0, 1, n)

        result = []
        for i, instrument in enumerate(self.config.instruments[:n]):
            data = self.instruments[instrument]
            group = data['correlation_group']
            sensitivity = data['regime_sensitivity']

            combined = (
                0.3 * market_component * sensitivity +
                0.25 * group_components[group] +
                0.45 * noise[i]
            )

            if self.regime == "trending_up":
                combined += 0.3 * sensitivity
            elif self.regime == "trending_down":
                combined -= 0.3 * sensitivity
            elif self.regime == "volatile":
                combined *= 2.0
            elif self.regime == "calm":
                combined *= 0.4
            elif self.regime == "reversal":
                combined *= -1.2 if data['momentum'] > 0 else 1.2

            result.append(combined)

        return np.array(result)

    def generate_tick(self) -> Dict[str, Dict]:
        self.tick_count += 1
        self._update_regime()

        n = len(self.config.instruments)
        correlated_noise = self._generate_correlated_noise(n)
        tick_data = {}

        for i, instrument in enumerate(self.config.instruments):
            data = self.instruments[instrument]
            noise = correlated_noise[i]

            vol = data['volatility']
            trend = data['trend']
            mr_speed = data['mean_reversion_speed']

            deviation = (data['price'] - data['base_price']) / data['base_price']
            mr_pull = -mr_speed * deviation
            momentum_push = data['momentum'] * 0.1

            ret = trend * 0.001 + mr_pull + momentum_push + noise * vol

            data['prev_price'] = data['price']
            data['price'] *= (1 + ret)
            data['price'] = max(data['price'], data['base_price'] * 0.5)

            delta = data['price'] - data['prev_price']
            delta_pct = delta / data['prev_price'] * 100
            data['delta_history'].append(delta_pct)

            deltas = list(data['delta_history'])
            if len(deltas) >= 5:
                weights = np.exp(np.linspace(-2, 0, min(len(deltas), 20)))
                weights /= weights.sum()
                recent = deltas[-len(weights):]
                data['momentum'] = np.dot(recent, weights[-len(recent):])
            data['momentum_history'].append(data['momentum'])

            base_vol = data['volume_base']
            vol_mult = 1 + abs(delta_pct) * 5 + np.random.exponential(0.3)
            if self.regime == "volatile":
                vol_mult *= 2
            data['volume_current'] = base_vol * vol_mult

            buy_pressure = np.random.beta(2, 2) + (0.2 if delta > 0 else -0.2)
            buy_pressure = np.clip(buy_pressure, 0, 1)
            flow = (buy_pressure - 0.5) * 2 * data['volume_current']
            data['flow_accumulator'] = data['flow_accumulator'] * 0.9 + flow * 0.1

            flow_intensity = min(abs(data['flow_accumulator']) / (base_vol * 2), 1.0)

            if data['flow_accumulator'] > 0:
                flow_dir = "inflow"
            elif data['flow_accumulator'] < 0:
                flow_dir = "outflow"
            else:
                flow_dir = "neutral"

            alpha = 0.05
            data['territory_high'] = max(
                data['territory_high'] * (1 - alpha) + data['price'] * alpha,
                data['price']
            )
            data['territory_low'] = min(
                data['territory_low'] * (1 - alpha) + data['price'] * alpha,
                data['price']
            )
            data['territory_center'] = (data['territory_high'] + data['territory_low']) / 2

            territory_range = data['territory_high'] - data['territory_low']
            price_position = (data['price'] - data['territory_low']) / max(territory_range, 0.0001)

            in_reversal = False
            if len(deltas) >= 15:
                recent_dir = np.sign(np.mean(deltas[-5:]))
                older_dir = np.sign(np.mean(deltas[-15:-5]))
                if recent_dir != older_dir and older_dir != 0:
                    in_reversal = True

            signal = self._determine_signal(
                delta_pct, data['momentum'], flow_intensity, flow_dir, in_reversal
            )

            data['price_history'].append(data['price'])
            data['trend'] += np.random.normal(0, 0.01)
            data['trend'] = np.clip(data['trend'], -1, 1)

            tick_data[instrument] = {
                'price': round(data['price'], 6),
                'prev_price': round(data['prev_price'], 6),
                'delta': round(delta, 6),
                'delta_pct': round(delta_pct, 4),
                'volume': round(data['volume_current'], 2),
                'flow_direction': flow_dir,
                'flow_intensity': round(flow_intensity, 4),
                'flow_accumulator': round(data['flow_accumulator'], 2),
                'momentum': round(data['momentum'], 4),
                'signal': signal,
                'in_reversal': in_reversal,
                'territory_high': round(data['territory_high'], 6),
                'territory_low': round(data['territory_low'], 6),
                'territory_center': round(data['territory_center'], 6),
                'price_position': round(price_position, 4),
                'regime': self.regime,
                'timestamp': datetime.now().isoformat(),
                'tick': self.tick_count,
            }

        return tick_data

    def _determine_signal(self, delta_pct, momentum, flow_intensity,
                          flow_dir, in_reversal):
        if in_reversal:
            return "reversal"

        score = 0
        if delta_pct > 0.5:
            score += 2
        elif delta_pct > 0.1:
            score += 1
        elif delta_pct < -0.5:
            score -= 2
        elif delta_pct < -0.1:
            score -= 1

        if momentum > 0.3:
            score += 2
        elif momentum > 0.1:
            score += 1
        elif momentum < -0.3:
            score -= 2
        elif momentum < -0.1:
            score -= 1

        if flow_dir == "inflow" and flow_intensity > 0.5:
            score += 1
        elif flow_dir == "outflow" and flow_intensity > 0.5:
            score -= 1

        if score >= 4:
            return "strong_buy"
        elif score >= 2:
            return "buy"
        elif score >= 1:
            return "cautious_buy"
        elif score <= -4:
            return "strong_sell"
        elif score <= -2:
            return "sell"
        elif score <= -1:
            return "cautious_sell"
        else:
            return "neutral"


# ═══════════════════════════════════════════════════════════════
# SECTION 4: MARKER PHYSICS ENGINE
# ═══════════════════════════════════════════════════════════════

class MarkerPhysicsEngine:
    """Physics-based marker animations"""

    def __init__(self, config: DashboardConfig):
        self.config = config
        self.markers: Dict[str, MarkerData] = {}

    def create_or_update_marker(self, instrument: str, tick: Dict) -> MarkerData:
        now = time.time()

        if instrument not in self.markers:
            marker = MarkerData(
                id=hashlib.md5(instrument.encode()).hexdigest()[:8],
                instrument=instrument,
                price=tick['price'],
                delta=tick['delta'],
                delta_pct=tick['delta_pct'],
                volume_flow=tick['volume'],
                flow_intensity=tick['flow_intensity'],
                momentum=tick['momentum'],
                territory_high=tick['territory_high'],
                territory_low=tick['territory_low'],
                territory_center=tick['territory_center'],
            )
            self.markers[instrument] = marker
        else:
            marker = self.markers[instrument]

        marker.price = tick['price']
        marker.delta = tick['delta']
        marker.delta_pct = tick['delta_pct']
        marker.volume_flow = tick['volume']
        marker.flow_intensity = tick['flow_intensity']
        marker.flow_direction = tick['flow_direction']
        marker.momentum = tick['momentum']
        marker.signal = tick['signal']
        marker.territory_high = tick['territory_high']
        marker.territory_low = tick['territory_low']
        marker.territory_center = tick['territory_center']
        marker.in_reversal = tick['in_reversal']
        marker.age_ticks += 1
        marker.last_update = now

        marker.target_size = self._calculate_target_size(tick)
        marker.target_color = self._calculate_target_color(tick)
        marker.state = self._determine_state(marker, tick)
        marker.is_outline = self._should_outline(marker, tick)
        marker.target_opacity = self._calculate_opacity(marker, tick)

        self._apply_physics(marker, tick)
        self._apply_transitions(marker)
        self._update_trail(marker)
        self._handle_freeze(marker, tick, now)

        if marker.state == "pulsing" or marker.in_reversal:
            marker.pulse_phase = (marker.pulse_phase + 0.15) % (2 * math.pi)

        return marker

    def _calculate_target_size(self, tick):
        cfg = self.config
        intensity = tick['flow_intensity']
        abs_delta = abs(tick['delta_pct'])
        abs_momentum = abs(tick['momentum'])

        composite = 0.4 * intensity + 0.3 * min(abs_delta, 1.0) + 0.3 * min(abs_momentum / 0.5, 1.0)

        if composite < cfg.size_threshold_low:
            t = composite / cfg.size_threshold_low
            size = cfg.size_min + t * (cfg.size_max * 0.3 - cfg.size_min)
        elif composite < cfg.size_threshold_mid:
            t = (composite - cfg.size_threshold_low) / (cfg.size_threshold_mid - cfg.size_threshold_low)
            size = cfg.size_max * 0.3 + t * (cfg.size_max * 0.6 - cfg.size_max * 0.3)
        elif composite < cfg.size_threshold_high:
            t = (composite - cfg.size_threshold_mid) / (cfg.size_threshold_high - cfg.size_threshold_mid)
            size = cfg.size_max * 0.6 + t * (cfg.size_max * 0.85 - cfg.size_max * 0.6)
        else:
            t = min((composite - cfg.size_threshold_high) / (1.0 - cfg.size_threshold_high), 1.0)
            size = cfg.size_max * 0.85 + t * (cfg.size_max - cfg.size_max * 0.85)

        vol_factor = 1 + min(tick['volume'] / 500, 0.5) * 0.2
        size *= vol_factor
        return np.clip(size, cfg.size_min, cfg.size_max)

    def _calculate_target_color(self, tick):
        cfg = self.config
        color_map = {
            'strong_buy': cfg.color_strong_buy, 'buy': cfg.color_buy,
            'cautious_buy': cfg.color_cautious, 'neutral': cfg.color_neutral,
            'cautious_sell': cfg.color_cautious, 'sell': cfg.color_sell,
            'strong_sell': cfg.color_strong_sell, 'reversal': cfg.color_reversal,
        }
        return color_map.get(tick['signal'], cfg.color_neutral)

    def _determine_state(self, marker, tick):
        if marker.is_frozen:
            return "frozen"
        if tick['in_reversal']:
            return "outline"

        abs_delta = abs(tick['delta_pct'])
        intensity = tick['flow_intensity']

        if abs_delta > 1.0 or intensity > 0.8:
            return "exploding"
        if tick['delta_pct'] > 0.2 and intensity > 0.5:
            return "growing"
        elif tick['delta_pct'] < -0.2 and intensity > 0.5:
            return "shrinking"
        elif intensity > 0.6:
            return "pulsing"
        elif abs_delta < 0.05 and intensity < 0.2:
            return "fading"
        else:
            return "drifting"

    def _should_outline(self, marker, tick):
        if tick['in_reversal']:
            return True
        if tick['signal'] in ['cautious_buy', 'cautious_sell']:
            return True
        if tick['flow_intensity'] < 0.15 and abs(tick['momentum']) < 0.05:
            return True
        return False

    def _calculate_opacity(self, marker, tick):
        base = 0.85
        if marker.state == "fading":
            base = 0.3
        elif marker.state == "exploding":
            base = 0.95
        elif marker.is_outline:
            base = 0.6
        base += tick['flow_intensity'] * 0.1
        return np.clip(base, 0.2, 0.98)

    def _apply_physics(self, marker, tick):
        cfg = self.config
        if marker.is_frozen:
            marker.vx *= 0.95
            marker.vy *= 0.95
            return

        force_x = tick['momentum'] * cfg.drift_speed * 2 + np.random.normal(0, cfg.drift_randomness)
        force_y = -tick['delta_pct'] * cfg.drift_speed * 5 + np.random.normal(0, cfg.drift_randomness)

        if tick['flow_direction'] == 'inflow':
            force_y -= tick['flow_intensity'] * 0.5
        elif tick['flow_direction'] == 'outflow':
            force_y += tick['flow_intensity'] * 0.5

        marker.ax = force_x
        marker.ay = force_y + cfg.gravity
        marker.vx = (marker.vx + marker.ax) * cfg.friction
        marker.vy = (marker.vy + marker.ay) * cfg.friction
        marker.vx = np.clip(marker.vx, -3.0, 3.0)
        marker.vy = np.clip(marker.vy, -3.0, 3.0)
        marker.x += marker.vx
        marker.y += marker.vy

    def _apply_transitions(self, marker):
        ease = 0.12
        marker.size += (marker.target_size - marker.size) * ease
        marker.opacity += (marker.target_opacity - marker.opacity) * ease
        marker.color = self._interpolate_color(marker.color, marker.target_color, 0.15)

    def _interpolate_color(self, current, target, factor):
        try:
            cr, cg, cb = int(current[1:3], 16), int(current[3:5], 16), int(current[5:7], 16)
            tr, tg, tb = int(target[1:3], 16), int(target[3:5], 16), int(target[5:7], 16)
            r = int(cr + (tr - cr) * factor)
            g = int(cg + (tg - cg) * factor)
            b = int(cb + (tb - cb) * factor)
            return f"#{r:02x}{g:02x}{b:02x}"
        except (ValueError, IndexError):
            return target

    def _update_trail(self, marker):
        marker.trail.append((marker.x, marker.y))
        if len(marker.trail) > self.config.trail_length:
            marker.trail = marker.trail[-self.config.trail_length:]

    def _handle_freeze(self, marker, tick, now):
        if abs(tick['delta_pct']) > 1.5 and not marker.is_frozen:
            marker.is_frozen = True
            marker.freeze_until = now + 2.0
            marker.state = "frozen"
        if marker.is_frozen and now > marker.freeze_until:
            marker.is_frozen = False

    def get_all_markers(self) -> List[MarkerData]:
        return list(self.markers.values())


# ═══════════════════════════════════════════════════════════════
# SECTION 5: DYNAMIC AXIS SCALER
# ═══════════════════════════════════════════════════════════════

class DynamicAxisScaler:
    """Auto-adjusting Y-axis with anti-flicker"""

    def __init__(self, config: DashboardConfig):
        self.config = config
        self.axes: Dict[str, AxisState] = {}

    def update_axis(self, axis_id: str, data_points: List[float]) -> Tuple[float, float]:
        if axis_id not in self.axes:
            self.axes[axis_id] = AxisState()

        axis = self.axes[axis_id]
        now = time.time()

        if not data_points:
            return axis.current_min, axis.current_max

        data_min = min(data_points)
        data_max = max(data_points)
        data_range = data_max - data_min
        padding = max(data_range * self.config.y_axis_padding_pct, 0.01)
        target_min = data_min - padding
        target_max = data_max + padding

        current_range = axis.current_max - axis.current_min
        change_mag = abs((target_max - target_min) - current_range) / max(current_range, 0.001)

        axis.smoothing_buffer.append((target_min, target_max))

        if now < axis.locked_until:
            if data_min < axis.current_min:
                axis.current_min = data_min - padding
            if data_max > axis.current_max:
                axis.current_max = data_max + padding
            return axis.current_min, axis.current_max

        if change_mag < self.config.anti_flicker_threshold:
            return axis.current_min, axis.current_max

        if len(axis.smoothing_buffer) >= 3:
            buf = list(axis.smoothing_buffer)
            smoothed_min = np.mean([b[0] for b in buf])
            smoothed_max = np.mean([b[1] for b in buf])
        else:
            smoothed_min, smoothed_max = target_min, target_max

        sf = self.config.y_axis_smoothing_factor
        axis.current_min += (smoothed_min - axis.current_min) * sf
        axis.current_max += (smoothed_max - axis.current_max) * sf

        if data_min < axis.current_min:
            axis.current_min = data_min - padding * 1.5
        if data_max > axis.current_max:
            axis.current_max = data_max + padding * 1.5

        if change_mag > 0.1:
            axis.locked_until = now + self.config.scale_lock_duration_seconds

        return axis.current_min, axis.current_max


# ═══════════════════════════════════════════════════════════════
# SECTION 6: VISUALIZATION RENDERER (Plotly 6.x compatible)
# ═══════════════════════════════════════════════════════════════

class DashboardRenderer:
    """Creates Plotly figures — fully compatible with Plotly 6.x"""

    def __init__(self, config: DashboardConfig):
        self.config = config
        self.axis_scaler = DynamicAxisScaler(config)

    def render_main_canvas(self, markers: List[MarkerData], tick_data: Dict) -> go.Figure:
        fig = go.Figure()

        if not markers:
            return self._empty_figure("Waiting for data...")

        prices = [m.price for m in markers]
        y_min, y_max = self.axis_scaler.update_axis("main", prices)

        outline_markers = []
        solid_markers = []
        frozen_markers = []
        pulse_markers = []

        for marker in markers:
            if marker.is_frozen:
                frozen_markers.append(marker)
            elif marker.is_outline:
                outline_markers.append(marker)
            elif marker.state == "pulsing":
                pulse_markers.append(marker)
            else:
                solid_markers.append(marker)

        # Glow layer
        all_active = solid_markers + pulse_markers + outline_markers
        if all_active:
            fig.add_trace(go.Scatter(
                x=list(range(len(all_active))),
                y=[m.price for m in all_active],
                mode='markers',
                marker=dict(
                    size=[m.size * 2.2 for m in all_active],
                    color=[f"rgba({int(m.color[1:3],16)},{int(m.color[3:5],16)},{int(m.color[5:7],16)},0.08)"
                           for m in all_active],
                    line=dict(width=0),
                ),
                showlegend=False,
                hoverinfo='skip',
            ))

        # Solid markers
        if solid_markers:
            fig.add_trace(self._create_marker_trace(solid_markers))

        # Pulsing markers
        if pulse_markers:
            for pm in pulse_markers:
                pm.size *= (1 + 0.2 * math.sin(pm.pulse_phase))
            fig.add_trace(self._create_marker_trace(pulse_markers))

        # Outline markers
        if outline_markers:
            fig.add_trace(self._create_outline_trace(outline_markers))

        # Frozen markers
        if frozen_markers:
            fig.add_trace(self._create_frozen_trace(frozen_markers))

        first_tick = tick_data.get(list(tick_data.keys())[0], {})

        fig.update_layout(
            plot_bgcolor=self.config.color_background,
            paper_bgcolor=self.config.color_background,
            font=dict(color='#cccccc', family='Arial, sans-serif', size=12),
            height=self.config.canvas_height,
            margin=dict(l=70, r=30, t=60, b=50),
            title=dict(
                text=(
                    f"<b>LIVE MARKET FLOW</b>  "
                    f"<span style='font-size:11px;color:#666'>"
                    f"Regime: {first_tick.get('regime', 'normal').upper()} "
                    f"│ Tick: {first_tick.get('tick', 0)} "
                    f"│ {datetime.now().strftime('%H:%M:%S')}</span>"
                ),
                font=dict(size=16, color='#ffffff', family='Arial, sans-serif'),
                x=0.01,
            ),
            xaxis=dict(
                showgrid=True, gridcolor=self.config.color_grid, gridwidth=1,
                zeroline=False, showticklabels=False,
                range=[-1, len(markers) + 1],
            ),
            yaxis=dict(
                showgrid=True, gridcolor=self.config.color_grid, gridwidth=1,
                zeroline=False,
                title=dict(text="Price Level", font=dict(size=11)),
                range=[y_min, y_max],
                tickformat=',.2f',
            ),
            showlegend=False,
            dragmode=False,
        )

        return fig

    def _create_marker_trace(self, markers):
        hover_texts = []
        for m in markers:
            arrow = "▲" if m.delta_pct >= 0 else "▼"
            flow_arrow = "⬆" if m.flow_direction == "inflow" else ("⬇" if m.flow_direction == "outflow" else "◆")
            state_icon = {'growing': '📈', 'shrinking': '📉', 'drifting': '〰️', 'pulsing': '💫',
                          'exploding': '💥', 'frozen': '❄️', 'outline': '⭕', 'fading': '👻'}.get(m.state, '●')
            hover_texts.append(
                f"<b>{m.instrument}</b><br>"
                f"Price: ${m.price:,.4f}<br>"
                f"Delta: {arrow} {m.delta_pct:+.3f}%<br>"
                f"Momentum: {m.momentum:+.4f}<br>"
                f"Flow: {flow_arrow} {m.flow_intensity:.1%}<br>"
                f"Signal: {m.signal.upper()}<br>"
                f"State: {state_icon} {m.state}"
            )

        return go.Scatter(
            x=list(range(len(markers))),
            y=[m.price for m in markers],
            mode='markers+text',
            marker=dict(
                size=[m.size for m in markers],
                color=[m.color for m in markers],
                opacity=[m.opacity for m in markers],
                line=dict(width=1, color='rgba(255,255,255,0.3)'),
            ),
            text=[m.instrument.split('/')[0] for m in markers],
            textposition='top center',
            textfont=dict(size=9, color='#aaaaaa', family='Arial'),
            hovertext=hover_texts,
            hoverinfo='text',
        )

    def _create_outline_trace(self, markers):
        border_colors = [self.config.color_reversal if m.in_reversal else self.config.color_outline for m in markers]
        hover_texts = [
            f"<b>{m.instrument} ⭕</b><br>Price: ${m.price:,.4f}<br>"
            f"{'🔄 REVERSAL' if m.in_reversal else '⚠️ CAUTIOUS'}<br>"
            f"Delta: {m.delta_pct:+.3f}%"
            for m in markers
        ]

        return go.Scatter(
            x=list(range(len(markers))),
            y=[m.price for m in markers],
            mode='markers+text',
            marker=dict(
                size=[m.size for m in markers],
                color='rgba(0,0,0,0)',
                line=dict(width=3, color=border_colors),
            ),
            text=[m.instrument.split('/')[0] for m in markers],
            textposition='top center',
            textfont=dict(size=9, color='#ff00ff', family='Arial'),
            hovertext=hover_texts,
            hoverinfo='text',
        )

    def _create_frozen_trace(self, markers):
        return go.Scatter(
            x=list(range(len(markers))),
            y=[m.price for m in markers],
            mode='markers+text',
            marker=dict(
                size=[m.size * 1.3 for m in markers],
                color=[m.color for m in markers],
                opacity=0.9,
                line=dict(width=3, color='#ffffff'),
                symbol='diamond',
            ),
            text=[f"❄️{m.instrument.split('/')[0]}" for m in markers],
            textposition='top center',
            textfont=dict(size=10, color='#ffffff', family='Arial'),
            hoverinfo='text',
            hovertext=[f"<b>{m.instrument} ❄️ FROZEN</b><br>Delta: {m.delta_pct:+.3f}%" for m in markers],
        )

    def render_flow_panel(self, markers: List[MarkerData]) -> go.Figure:
        fig = go.Figure()
        if not markers:
            return self._empty_figure("No flow data")

        sorted_m = sorted(markers, key=lambda m: m.flow_intensity, reverse=True)
        instruments = [m.instrument for m in sorted_m]
        intensities = [m.flow_intensity for m in sorted_m]
        colors = []
        for m in sorted_m:
            a = 0.4 + m.flow_intensity * 0.5
            if m.flow_direction == 'inflow':
                colors.append(f'rgba(0, 255, 136, {a})')
            elif m.flow_direction == 'outflow':
                colors.append(f'rgba(255, 107, 107, {a})')
            else:
                colors.append('rgba(136, 136, 136, 0.5)')

        fig.add_trace(go.Bar(
            x=intensities, y=instruments, orientation='h',
            marker=dict(color=colors, line=dict(width=1, color='rgba(255,255,255,0.1)')),
            text=[f"{i:.0%}" for i in intensities],
            textposition='auto',
            textfont=dict(color='#ffffff', size=10, family='Arial'),
        ))

        fig.update_layout(
            plot_bgcolor=self.config.color_background,
            paper_bgcolor=self.config.color_background,
            font=dict(color='#cccccc', size=10, family='Arial'),
            height=500, margin=dict(l=80, r=20, t=40, b=30),
            title=dict(text="<b>FLOW INTENSITY</b>", font=dict(size=13, color='#ffffff')),
            xaxis=dict(range=[0, 1], showgrid=True, gridcolor=self.config.color_grid, tickformat='.0%'),
            yaxis=dict(showgrid=False, autorange='reversed'),
            bargap=0.15,
        )
        return fig

    def render_momentum_panel(self, markers: List[MarkerData]) -> go.Figure:
        fig = go.Figure()
        if not markers:
            return self._empty_figure("No momentum data")

        sorted_m = sorted(markers, key=lambda m: m.momentum, reverse=True)
        instruments = [m.instrument for m in sorted_m]
        momentums = [m.momentum for m in sorted_m]
        cfg = self.config
        colors = [
            cfg.color_strong_buy if m.momentum > 0.2 else
            cfg.color_buy if m.momentum > 0.05 else
            cfg.color_strong_sell if m.momentum < -0.2 else
            cfg.color_sell if m.momentum < -0.05 else
            cfg.color_neutral
            for m in sorted_m
        ]

        fig.add_trace(go.Bar(
            x=momentums, y=instruments, orientation='h',
            marker=dict(color=colors, line=dict(width=0)),
            text=[f"{m:+.3f}" for m in momentums],
            textposition='auto',
            textfont=dict(color='#ffffff', size=10, family='Arial'),
        ))

        fig.update_layout(
            plot_bgcolor=self.config.color_background,
            paper_bgcolor=self.config.color_background,
            font=dict(color='#cccccc', size=10, family='Arial'),
            height=500, margin=dict(l=80, r=20, t=40, b=30),
            title=dict(text="<b>MOMENTUM</b>", font=dict(size=13, color='#ffffff')),
            xaxis=dict(showgrid=True, gridcolor=self.config.color_grid,
                       zeroline=True, zerolinecolor='#444', zerolinewidth=2),
            yaxis=dict(showgrid=False, autorange='reversed'),
            bargap=0.15,
        )
        return fig

    def render_delta_heatmap(self, markers: List[MarkerData], history_len: int = 20) -> go.Figure:
        """Plotly 6.x compatible heatmap"""
        fig = go.Figure()
        if not markers:
            return self._empty_figure("No delta data")

        instruments = [m.instrument for m in markers]
        z_data = []
        for m in markers:
            row = []
            base_delta = m.delta_pct
            for i in range(history_len):
                noise = np.random.normal(0, abs(base_delta) * 0.3 + 0.05)
                val = base_delta * (1 - i * 0.04) + noise
                row.append(round(val, 3))
            z_data.append(row[::-1])

        x_labels = [f"t-{history_len - i}" for i in range(history_len)]

        # Plotly 6.x compatible — no nested dicts in colorbar
        fig.add_trace(go.Heatmap(
            z=z_data,
            y=instruments,
            x=x_labels,
            colorscale=[
                [0.0, '#FF0040'],
                [0.25, '#FF6B6B'],
                [0.5, '#1a1a2e'],
                [0.75, '#00CC66'],
                [1.0, '#00FF88'],
            ],
            zmid=0,
            showscale=True,
            colorbar=dict(
                title=dict(text='Δ%', font=dict(color='#cccccc', size=11)),
                tickfont=dict(color='#cccccc', size=10),
            ),
            hovertemplate='%{y}<br>%{x}<br>Delta: %{z:+.3f}%<extra></extra>',
        ))

        fig.update_layout(
            plot_bgcolor=self.config.color_background,
            paper_bgcolor=self.config.color_background,
            font=dict(color='#cccccc', size=10, family='Arial'),
            height=400, margin=dict(l=80, r=20, t=40, b=40),
            title=dict(text="<b>DELTA HEATMAP</b>", font=dict(size=13, color='#ffffff')),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=False, autorange='reversed'),
        )
        return fig

    def render_signal_summary(self, markers: List[MarkerData]) -> go.Figure:
        fig = go.Figure()

        signal_counts = {}
        for m in markers:
            signal_counts[m.signal] = signal_counts.get(m.signal, 0) + 1

        signal_order = ['strong_buy', 'buy', 'cautious_buy', 'neutral',
                        'cautious_sell', 'sell', 'strong_sell', 'reversal']
        signal_colors = {
            'strong_buy': self.config.color_strong_buy, 'buy': self.config.color_buy,
            'cautious_buy': self.config.color_cautious, 'neutral': self.config.color_neutral,
            'cautious_sell': '#FFB347', 'sell': self.config.color_sell,
            'strong_sell': self.config.color_strong_sell, 'reversal': self.config.color_reversal,
        }

        labels, values, colors = [], [], []
        for signal in signal_order:
            count = signal_counts.get(signal, 0)
            if count > 0:
                labels.append(signal.replace('_', ' ').upper())
                values.append(count)
                colors.append(signal_colors.get(signal, '#888'))

        if not labels:
            return self._empty_figure("No signals")

        fig.add_trace(go.Pie(
            labels=labels, values=values,
            marker=dict(colors=colors, line=dict(width=2, color='#0a0a1a')),
            textinfo='label+value',
            textfont=dict(size=11, color='#ffffff', family='Arial'),
            hole=0.4,
        ))

        fig.update_layout(
            plot_bgcolor=self.config.color_background,
            paper_bgcolor=self.config.color_background,
            font=dict(color='#cccccc', family='Arial'),
            height=350, margin=dict(l=20, r=20, t=40, b=20),
            title=dict(text="<b>SIGNAL DISTRIBUTION</b>", font=dict(size=13, color='#ffffff')),
            showlegend=False,
        )
        return fig

    def _empty_figure(self, message):
        fig = go.Figure()
        fig.add_annotation(text=message, xref="paper", yref="paper", x=0.5, y=0.5,
                           showarrow=False, font=dict(size=16, color='#666'))
        fig.update_layout(plot_bgcolor=self.config.color_background,
                          paper_bgcolor=self.config.color_background, height=400)
        return fig


# ═══════════════════════════════════════════════════════════════
# SECTION 7: DATA TABLE GENERATOR
# ═══════════════════════════════════════════════════════════════

class DataTableGenerator:

    @staticmethod
    def create_market_table(markers: List[MarkerData]) -> pd.DataFrame:
        if not markers:
            return pd.DataFrame()

        rows = []
        for m in markers:
            delta_arrow = "▲" if m.delta_pct >= 0 else "▼"
            flow_arrow = "⬆" if m.flow_direction == "inflow" else ("⬇" if m.flow_direction == "outflow" else "◆")
            state_icon = {'growing': '📈', 'shrinking': '📉', 'drifting': '〰️', 'pulsing': '💫',
                          'exploding': '💥', 'frozen': '❄️', 'outline': '⭕', 'fading': '👻'}.get(m.state, '●')
            signal_icon = {'strong_buy': '🟢🟢', 'buy': '🟢', 'cautious_buy': '🟡', 'neutral': '⚪',
                           'cautious_sell': '🟠', 'sell': '🔴', 'strong_sell': '🔴🔴', 'reversal': '🔄'}.get(m.signal, '⚪')
            rows.append({
                'Instrument': m.instrument,
                'Price': f"${m.price:,.4f}",
                'Delta': f"{delta_arrow} {m.delta_pct:+.3f}%",
                'Momentum': f"{m.momentum:+.4f}",
                'Flow': f"{flow_arrow} {m.flow_intensity:.0%}",
                'Signal': f"{signal_icon} {m.signal.upper()}",
                'State': f"{state_icon} {m.state}",
                'Size': f"{m.size:.0f}",
            })

        return pd.DataFrame(rows)

    @staticmethod
    def create_signal_summary(markers: List[MarkerData]) -> Dict:
        total = len(markers)
        if total == 0:
            return {}

        signals = [m.signal for m in markers]
        bullish = sum(1 for s in signals if s in ['strong_buy', 'buy', 'cautious_buy'])
        bearish = sum(1 for s in signals if s in ['strong_sell', 'sell', 'cautious_sell'])
        neutral = sum(1 for s in signals if s == 'neutral')
        reversals = sum(1 for s in signals if s == 'reversal')

        return {
            'total': total,
            'bullish': bullish, 'bearish': bearish,
            'neutral': neutral, 'reversals': reversals,
            'bullish_pct': bullish / total * 100,
            'bearish_pct': bearish / total * 100,
            'avg_momentum': np.mean([m.momentum for m in markers]),
            'avg_flow': np.mean([m.flow_intensity for m in markers]),
            'frozen': sum(1 for m in markers if m.is_frozen),
            'outlines': sum(1 for m in markers if m.is_outline),
        }


# ═══════════════════════════════════════════════════════════════
# SECTION 8: CUSTOM CSS
# ═══════════════════════════════════════════════════════════════

def inject_css():
    st.markdown("""
    <style>
        .stApp {
            background-color: #0a0a1a;
        }
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
        }

        /* Header */
        .dash-header {
            background: linear-gradient(135deg, #0a0a1a 0%, #1a1a3e 100%);
            border: 1px solid #2a2a4e;
            border-radius: 12px;
            padding: 18px 28px;
            margin-bottom: 16px;
            text-align: center;
        }
        .dash-header h1 {
            color: #00FF88;
            font-family: 'Arial', sans-serif;
            font-size: 1.8em;
            margin: 0;
            text-shadow: 0 0 20px rgba(0, 255, 136, 0.3);
        }
        .dash-header p {
            color: #888;
            font-size: 0.85em;
            margin: 5px 0 0 0;
            font-family: 'Arial', sans-serif;
        }

        /* Metric cards */
        .mcard {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border: 1px solid #2a2a4e;
            border-radius: 10px;
            padding: 14px 16px;
            text-align: center;
            transition: border-color 0.3s ease;
        }
        .mcard:hover {
            border-color: #00FF88;
        }
        .mval {
            font-size: 1.5em;
            font-weight: 700;
            font-family: 'Arial', sans-serif;
        }
        .mlab {
            font-size: 0.65em;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 4px;
            font-family: 'Arial', sans-serif;
        }
        .cg { color: #00FF88; }
        .cr { color: #FF6B6B; }
        .cy { color: #FFD700; }
        .cp { color: #FF00FF; }
        .cw { color: #ffffff; }
        .cgr { color: #888888; }

        /* Live dot */
        .live-dot {
            display: inline-block;
            width: 8px; height: 8px;
            border-radius: 50%;
            background: #00FF88;
            margin-right: 8px;
            animation: blink 1.5s infinite;
        }
        @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }

        /* Legend */
        .legend-row {
            background: #1a1a2e;
            border: 1px solid #2a2a4e;
            border-radius: 8px;
            padding: 10px 14px;
            margin: 8px 0 14px 0;
            font-family: 'Arial', sans-serif;
            font-size: 0.8em;
            color: #ccc;
        }
        .ldot {
            display: inline-block;
            width: 10px; height: 10px;
            border-radius: 50%;
            margin-right: 4px;
            vertical-align: middle;
        }
        .litm {
            display: inline-block;
            margin: 2px 10px;
        }

        /* Hide streamlit chrome */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* Fix font globally */
        html, body, [class*="css"] {
            font-family: 'Arial', 'Helvetica Neue', sans-serif;
        }
    </style>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# SECTION 9: UI COMPONENTS
# ═══════════════════════════════════════════════════════════════

def render_header():
    st.markdown("""
    <div class="dash-header">
        <h1>🔮 REAL-TIME MARKET FLOW</h1>
        <p>
            <span class="live-dot"></span>
            Live Animated Visualization &nbsp;│&nbsp;
            WebSocket Stream Simulation &nbsp;│&nbsp;
            Dynamic Scaling &nbsp;│&nbsp;
            Smart Signals
        </p>
    </div>
    """, unsafe_allow_html=True)


def metric_card(label, value, color="cw"):
    return f"""
    <div class="mcard">
        <div class="mval {color}">{value}</div>
        <div class="mlab">{label}</div>
    </div>
    """


def render_legend():
    st.markdown("""
    <div class="legend-row">
        <span class="litm"><span class="ldot" style="background:#00FF88"></span>Strong Buy</span>
        <span class="litm"><span class="ldot" style="background:#00CC66"></span>Buy</span>
        <span class="litm"><span class="ldot" style="background:#FFD700"></span>Cautious</span>
        <span class="litm"><span class="ldot" style="background:#888"></span>Neutral</span>
        <span class="litm"><span class="ldot" style="background:#FF6B6B"></span>Sell</span>
        <span class="litm"><span class="ldot" style="background:#FF0040"></span>Strong Sell</span>
        <span class="litm"><span class="ldot" style="background:#FF00FF"></span>Reversal</span>
        <span class="litm"><span class="ldot" style="background:transparent;border:2px solid #fff"></span>Outline</span>
        <span class="litm">❄️ Frozen</span>
        <span class="litm">💫 Pulsing</span>
        <span class="litm">💥 Exploding</span>
    </div>
    """, unsafe_allow_html=True)


def render_controls():
    with st.sidebar:
        st.markdown("## ⚙️ Controls")

        st.session_state.is_running = st.toggle("▶ Live Stream", value=st.session_state.get('is_running', True))
        st.session_state.update_speed = st.slider("Update Speed (s)", 0.5, 5.0,
                                                   st.session_state.get('update_speed', 2.0), 0.5)

        st.markdown("---")
        st.markdown("## 📊 Panels")
        show_table = st.checkbox("Data Table", value=True)
        show_flow = st.checkbox("Flow Panel", value=True)
        show_momentum = st.checkbox("Momentum Panel", value=True)
        show_heatmap = st.checkbox("Delta Heatmap", value=True)
        show_signals = st.checkbox("Signal Distribution", value=True)

        st.markdown("---")
        st.markdown("## 🎨 Sizing")
        config = st.session_state.config
        config.size_min = st.slider("Min Size", 5, 20, config.size_min)
        config.size_max = st.slider("Max Size", 30, 100, config.size_max)

        st.markdown("---")
        if st.session_state.get('perf_log'):
            avg_ms = np.mean(list(st.session_state.perf_log))
            st.metric("Avg Render", f"{avg_ms:.0f}ms")
        st.metric("Total Ticks", st.session_state.get('tick_count', 0))

    return show_table, show_flow, show_momentum, show_heatmap, show_signals


# ═══════════════════════════════════════════════════════════════
# SECTION 10: MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════

def init_state():
    if 'config' not in st.session_state:
        st.session_state.config = DashboardConfig()
    if 'simulator' not in st.session_state:
        st.session_state.simulator = MarketDataSimulator(st.session_state.config)
    if 'physics' not in st.session_state:
        st.session_state.physics = MarkerPhysicsEngine(st.session_state.config)
    if 'renderer' not in st.session_state:
        st.session_state.renderer = DashboardRenderer(st.session_state.config)
    if 'tick_count' not in st.session_state:
        st.session_state.tick_count = 0
    if 'is_running' not in st.session_state:
        st.session_state.is_running = True
    if 'update_speed' not in st.session_state:
        st.session_state.update_speed = 2.0
    if 'perf_log' not in st.session_state:
        st.session_state.perf_log = deque(maxlen=100)


def run_dashboard():
    inject_css()
    init_state()
    render_header()

    show_table, show_flow, show_momentum, show_heatmap, show_signals = render_controls()

    render_start = time.time()

    simulator = st.session_state.simulator
    physics = st.session_state.physics
    renderer = st.session_state.renderer

    tick_data = simulator.generate_tick()
    st.session_state.tick_count += 1

    for instrument, data in tick_data.items():
        physics.create_or_update_marker(instrument, data)

    markers = physics.get_all_markers()
    summary = DataTableGenerator.create_signal_summary(markers)

    # ── Top Metrics ──
    if summary:
        cols = st.columns(8)
        with cols[0]:
            st.markdown(metric_card("Instruments", str(summary['total']), "cw"), unsafe_allow_html=True)
        with cols[1]:
            st.markdown(metric_card("Bullish", f"{summary['bullish']} ({summary['bullish_pct']:.0f}%)", "cg"), unsafe_allow_html=True)
        with cols[2]:
            st.markdown(metric_card("Bearish", f"{summary['bearish']} ({summary['bearish_pct']:.0f}%)", "cr"), unsafe_allow_html=True)
        with cols[3]:
            st.markdown(metric_card("Neutral", str(summary['neutral']), "cgr"), unsafe_allow_html=True)
        with cols[4]:
            st.markdown(metric_card("Reversals", str(summary['reversals']), "cp"), unsafe_allow_html=True)
        with cols[5]:
            mc = "cg" if summary['avg_momentum'] > 0 else "cr"
            st.markdown(metric_card("Momentum", f"{summary['avg_momentum']:+.3f}", mc), unsafe_allow_html=True)
        with cols[6]:
            st.markdown(metric_card("Avg Flow", f"{summary['avg_flow']:.0%}", "cy"), unsafe_allow_html=True)
        with cols[7]:
            first = tick_data.get(list(tick_data.keys())[0], {})
            regime = first.get('regime', 'normal')
            rc = {'normal': 'cw', 'trending_up': 'cg', 'trending_down': 'cr',
                  'volatile': 'cy', 'calm': 'cgr', 'reversal': 'cp'}.get(regime, 'cw')
            st.markdown(metric_card("Regime", regime.upper(), rc), unsafe_allow_html=True)

    # ── Legend ──
    render_legend()

    # ── Main Canvas ──
    main_fig = renderer.render_main_canvas(markers, tick_data)
    st.plotly_chart(main_fig, use_container_width=True, config={'displayModeBar': False})

    # ── Side Panels ──
    if show_flow or show_momentum:
        c1, c2 = st.columns(2)
        if show_flow:
            with c1:
                st.plotly_chart(renderer.render_flow_panel(markers), use_container_width=True,
                                config={'displayModeBar': False})
        if show_momentum:
            with c2:
                st.plotly_chart(renderer.render_momentum_panel(markers), use_container_width=True,
                                config={'displayModeBar': False})

    # ── Heatmap + Signals ──
    if show_heatmap or show_signals:
        c1, c2 = st.columns([2, 1])
        if show_heatmap:
            with c1:
                st.plotly_chart(renderer.render_delta_heatmap(markers), use_container_width=True,
                                config={'displayModeBar': False})
        if show_signals:
            with c2:
                st.plotly_chart(renderer.render_signal_summary(markers), use_container_width=True,
                                config={'displayModeBar': False})

    # ── Data Table ──
    if show_table:
        st.markdown("### 📋 Live Market Data")
        tdf = DataTableGenerator.create_market_table(markers)
        if not tdf.empty:
            st.dataframe(tdf, use_container_width=True, hide_index=True, height=400)

    # ── Performance ──
    render_ms = (time.time() - render_start) * 1000
    st.session_state.perf_log.append(render_ms)

    st.markdown(f"""
    <div style="text-align:center;padding:8px;color:#444;font-size:0.75em;font-family:Arial,sans-serif">
        Render: {render_ms:.0f}ms │ Tick: {st.session_state.tick_count} │
        Markers: {len(markers)} │ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </div>
    """, unsafe_allow_html=True)

    # ── Auto Refresh ──
    if st.session_state.is_running:
        time.sleep(st.session_state.update_speed)
        st.rerun()


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════

run_dashboard()
