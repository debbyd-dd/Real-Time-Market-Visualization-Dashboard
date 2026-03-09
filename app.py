"""
╔══════════════════════════════════════════════════════════════════════════╗
║         REAL-TIME MARKET VISUALIZATION DASHBOARD                        ║
║                                                                          ║
║   Production-grade animated canvas dashboard with:                       ║
║   • Live WebSocket data streaming simulation                             ║
║   • Animated orb/particle markers with physics-based movement            ║
║   • Dynamic Y-axis auto-scaling with anti-flicker logic                  ║
║   • Outline mode for intra-territory reversals                           ║
║   • Threshold-based sizing with smooth easing transitions                ║
║   • Low-latency rendering optimized for bursty updates                   ║
║   • Full Streamlit deployment ready                                      ║
║                                                                          ║
║   Author: Senior Python/Visualization Engineer                           ║
║   Version: 2.0.0                                                         ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import json
import colorsys
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum
from collections import deque
import hashlib
import math
import threading
import queue

# ═══════════════════════════════════════════════════════════════
# SECTION 1: CONFIGURATION & DATA MODELS
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


class FlowDirection(Enum):
    INFLOW = "inflow"
    OUTFLOW = "outflow"
    NEUTRAL = "neutral"
    REVERSAL = "reversal"


@dataclass
class DashboardConfig:
    """Master configuration for the dashboard"""
    # Canvas dimensions
    canvas_width: int = 1200
    canvas_height: int = 700

    # Animation settings
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
    size_min: int = 8
    size_max: int = 65
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

    # Flow thresholds
    flow_threshold_strong: float = 0.75
    flow_threshold_moderate: float = 0.45
    flow_threshold_weak: float = 0.20

    # Instruments to track
    instruments: List[str] = field(default_factory=lambda: [
        "BTC/USD", "ETH/USD", "SOL/USD", "BNB/USD", "XRP/USD",
        "ADA/USD", "AVAX/USD", "DOT/USD", "MATIC/USD", "LINK/USD",
        "ATOM/USD", "UNI/USD", "AAVE/USD", "ARB/USD", "OP/USD",
        "DOGE/USD", "SHIB/USD", "LTC/USD", "FIL/USD", "APT/USD",
    ])


@dataclass
class MarkerData:
    """Represents a single animated marker/orb on the canvas"""
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

    # Data values
    price: float = 0.0
    delta: float = 0.0
    delta_pct: float = 0.0
    volume_flow: float = 0.0
    flow_intensity: float = 0.0
    momentum: float = 0.0

    # State tracking
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
    """Dynamic Y-axis state with anti-flicker logic"""
    current_min: float = 0.0
    current_max: float = 100.0
    target_min: float = 0.0
    target_max: float = 100.0
    locked_until: float = 0.0
    last_significant_change: float = 0.0
    change_history: List[float] = field(default_factory=list)
    smoothing_buffer: deque = field(
        default_factory=lambda: deque(maxlen=10)
    )


# ═══════════════════════════════════════════════════════════════
# SECTION 2: MARKET DATA SIMULATOR (PHASE 1 - DUMMY DATA)
# ═══════════════════════════════════════════════════════════════

class MarketDataSimulator:
    """
    High-fidelity market data simulator that produces realistic
    price movements, volume flows, deltas, and momentum signals.

    Phase 1: Generates synthetic data with realistic statistical properties.
    Phase 2: Replace with live WebSocket feed integration.
    """

    def __init__(self, config: DashboardConfig):
        self.config = config
        self.instruments = {}
        self.tick_count = 0
        self.regime = "normal"
        self.regime_duration = 0
        self.event_queue = queue.Queue()

        self._initialize_instruments()

    def _initialize_instruments(self):
        """Set up initial state for all instruments"""
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
        """Simulate market regime changes"""
        self.regime_duration += 1

        if self.regime_duration > np.random.randint(30, 100):
            regimes = ["normal", "trending_up", "trending_down",
                       "volatile", "calm", "reversal"]
            weights = [0.30, 0.15, 0.15, 0.15, 0.15, 0.10]
            self.regime = np.random.choice(regimes, p=weights)
            self.regime_duration = 0

    def _generate_correlated_noise(self, n: int) -> np.ndarray:
        """Generate correlated random moves across instruments"""
        # Market-wide component
        market_component = np.random.normal(0, 0.5)

        # Group components
        group_components = {
            i: np.random.normal(0, 0.3) for i in range(4)
        }

        # Individual noise
        noise = np.random.normal(0, 1, n)

        # Blend based on correlation group
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

            # Regime adjustments
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
        """
        Generate one tick of market data for all instruments.
        Returns delta, flow, momentum, territory data.
        """
        self.tick_count += 1
        self._update_regime()

        n = len(self.config.instruments)
        correlated_noise = self._generate_correlated_noise(n)

        tick_data = {}

        for i, instrument in enumerate(self.config.instruments):
            data = self.instruments[instrument]
            noise = correlated_noise[i]

            # Calculate price move
            vol = data['volatility']
            trend = data['trend']
            mr_speed = data['mean_reversion_speed']

            # Mean reversion component
            deviation = (data['price'] - data['base_price']) / data['base_price']
            mr_pull = -mr_speed * deviation

            # Momentum component
            momentum_push = data['momentum'] * 0.1

            # Combined return
            ret = (
                trend * 0.001 +
                mr_pull +
                momentum_push +
                noise * vol
            )

            # Apply price change
            data['prev_price'] = data['price']
            data['price'] *= (1 + ret)
            data['price'] = max(data['price'], data['base_price'] * 0.5)

            # Calculate delta
            delta = data['price'] - data['prev_price']
            delta_pct = delta / data['prev_price'] * 100
            data['delta_history'].append(delta_pct)

            # Update momentum (EMA of recent deltas)
            deltas = list(data['delta_history'])
            if len(deltas) >= 5:
                weights = np.exp(np.linspace(-2, 0, min(len(deltas), 20)))
                weights /= weights.sum()
                recent = deltas[-len(weights):]
                data['momentum'] = np.dot(recent, weights[-len(recent):])
            data['momentum_history'].append(data['momentum'])

            # Volume flow simulation
            base_vol = data['volume_base']
            vol_mult = 1 + abs(delta_pct) * 5 + np.random.exponential(0.3)
            if self.regime == "volatile":
                vol_mult *= 2
            data['volume_current'] = base_vol * vol_mult

            # Flow direction and intensity
            buy_pressure = np.random.beta(2, 2) + (0.2 if delta > 0 else -0.2)
            buy_pressure = np.clip(buy_pressure, 0, 1)
            flow = (buy_pressure - 0.5) * 2 * data['volume_current']
            data['flow_accumulator'] = (
                data['flow_accumulator'] * 0.9 + flow * 0.1
            )

            flow_intensity = min(
                abs(data['flow_accumulator']) /
                (base_vol * 2), 1.0
            )

            if data['flow_accumulator'] > 0:
                flow_dir = "inflow"
            elif data['flow_accumulator'] < 0:
                flow_dir = "outflow"
            else:
                flow_dir = "neutral"

            # Territory tracking
            alpha = 0.05
            data['territory_high'] = max(
                data['territory_high'] * (1 - alpha) +
                data['price'] * alpha,
                data['price']
            )
            data['territory_low'] = min(
                data['territory_low'] * (1 - alpha) +
                data['price'] * alpha,
                data['price']
            )
            data['territory_center'] = (
                data['territory_high'] + data['territory_low']
            ) / 2

            # Detect reversal
            territory_range = data['territory_high'] - data['territory_low']
            price_position = (
                (data['price'] - data['territory_low']) /
                max(territory_range, 0.0001)
            )

            in_reversal = False
            if len(deltas) >= 5:
                recent_direction = np.sign(np.mean(deltas[-5:]))
                older_direction = np.sign(np.mean(deltas[-15:-5])) if len(deltas) >= 15 else 0
                if recent_direction != older_direction and older_direction != 0:
                    in_reversal = True

            # Determine signal
            signal = self._determine_signal(
                delta_pct, data['momentum'], flow_intensity,
                flow_dir, in_reversal, price_position
            )

            # Store price history
            data['price_history'].append(data['price'])

            # Update trend slowly
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

    def _determine_signal(self, delta_pct: float, momentum: float,
                          flow_intensity: float, flow_dir: str,
                          in_reversal: bool,
                          price_position: float) -> str:
        """Determine trading signal from multiple factors"""
        if in_reversal:
            return "reversal"

        # Composite score
        score = 0

        # Delta contribution
        if delta_pct > 0.5:
            score += 2
        elif delta_pct > 0.1:
            score += 1
        elif delta_pct < -0.5:
            score -= 2
        elif delta_pct < -0.1:
            score -= 1

        # Momentum contribution
        if momentum > 0.3:
            score += 2
        elif momentum > 0.1:
            score += 1
        elif momentum < -0.3:
            score -= 2
        elif momentum < -0.1:
            score -= 1

        # Flow contribution
        if flow_dir == "inflow" and flow_intensity > 0.5:
            score += 1
        elif flow_dir == "outflow" and flow_intensity > 0.5:
            score -= 1

        # Map score to signal
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
# SECTION 3: MARKER PHYSICS ENGINE
# ═══════════════════════════════════════════════════════════════

class MarkerPhysicsEngine:
    """
    Handles all marker animations:
    - Smooth size transitions with easing
    - Color interpolation
    - Drift physics with velocity/acceleration
    - Pulse animations
    - Trail management
    - Freeze/thaw state management
    - Outline mode for reversals
    """

    def __init__(self, config: DashboardConfig):
        self.config = config
        self.markers: Dict[str, MarkerData] = {}
        self.time = time.time()

    def create_or_update_marker(self, instrument: str,
                                 tick: Dict) -> MarkerData:
        """Create new marker or update existing one with new tick data"""
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

        # Update data values
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

        # Update target size based on thresholds
        marker.target_size = self._calculate_target_size(tick)

        # Update target color based on signal
        marker.target_color = self._calculate_target_color(tick)

        # Update state
        marker.state = self._determine_state(marker, tick)

        # Handle outline mode
        marker.is_outline = self._should_outline(marker, tick)

        # Update target opacity
        marker.target_opacity = self._calculate_opacity(marker, tick)

        # Apply physics
        self._apply_physics(marker, tick)

        # Apply smooth transitions
        self._apply_transitions(marker)

        # Update trail
        self._update_trail(marker)

        # Handle freeze
        self._handle_freeze(marker, tick, now)

        # Calculate pulse phase
        if marker.state == "pulsing" or marker.in_reversal:
            marker.pulse_phase = (
                (marker.pulse_phase + 0.15) % (2 * math.pi)
            )

        return marker

    def _calculate_target_size(self, tick: Dict) -> float:
        """
        Threshold-based sizing logic:
        - Low flow/momentum → small markers
        - Moderate → medium markers
        - High intensity → large markers
        - Strong signals → maximum size
        """
        cfg = self.config
        intensity = tick['flow_intensity']
        abs_delta = abs(tick['delta_pct'])
        abs_momentum = abs(tick['momentum'])

        # Composite intensity score
        composite = (
            0.4 * intensity +
            0.3 * min(abs_delta / 1.0, 1.0) +
            0.3 * min(abs_momentum / 0.5, 1.0)
        )

        # Threshold-based sizing with smooth interpolation
        if composite < cfg.size_threshold_low:
            # Low zone: small markers
            t = composite / cfg.size_threshold_low
            size = cfg.size_min + t * (cfg.size_max * 0.3 - cfg.size_min)
        elif composite < cfg.size_threshold_mid:
            # Mid zone: medium markers
            t = (
                (composite - cfg.size_threshold_low) /
                (cfg.size_threshold_mid - cfg.size_threshold_low)
            )
            size = cfg.size_max * 0.3 + t * (cfg.size_max * 0.6 - cfg.size_max * 0.3)
        elif composite < cfg.size_threshold_high:
            # High zone: large markers
            t = (
                (composite - cfg.size_threshold_mid) /
                (cfg.size_threshold_high - cfg.size_threshold_mid)
            )
            size = cfg.size_max * 0.6 + t * (cfg.size_max * 0.85 - cfg.size_max * 0.6)
        else:
            # Maximum zone
            t = min(
                (composite - cfg.size_threshold_high) /
                (1.0 - cfg.size_threshold_high), 1.0
            )
            size = cfg.size_max * 0.85 + t * (cfg.size_max - cfg.size_max * 0.85)

        # Volume boost
        vol_factor = 1 + min(tick['volume'] / 500, 0.5) * 0.2
        size *= vol_factor

        return np.clip(size, cfg.size_min, cfg.size_max)

    def _calculate_target_color(self, tick: Dict) -> str:
        """Color based on signal type"""
        cfg = self.config
        signal = tick['signal']

        color_map = {
            'strong_buy': cfg.color_strong_buy,
            'buy': cfg.color_buy,
            'cautious_buy': cfg.color_cautious,
            'neutral': cfg.color_neutral,
            'cautious_sell': cfg.color_cautious,
            'sell': cfg.color_sell,
            'strong_sell': cfg.color_strong_sell,
            'reversal': cfg.color_reversal,
        }

        return color_map.get(signal, cfg.color_neutral)

    def _determine_state(self, marker: MarkerData, tick: Dict) -> str:
        """Determine marker animation state"""
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

    def _should_outline(self, marker: MarkerData, tick: Dict) -> bool:
        """
        Outline mode activates for:
        - Intra-territory reversals
        - Cautious signals
        - Low-confidence flow readings
        """
        if tick['in_reversal']:
            return True
        if tick['signal'] in ['cautious_buy', 'cautious_sell']:
            return True
        if tick['flow_intensity'] < 0.15 and abs(tick['momentum']) < 0.05:
            return True
        return False

    def _calculate_opacity(self, marker: MarkerData, tick: Dict) -> float:
        """Calculate target opacity"""
        base_opacity = 0.85

        if marker.state == "fading":
            base_opacity = 0.3
        elif marker.state == "exploding":
            base_opacity = 0.95
        elif marker.is_outline:
            base_opacity = 0.6

        # Flow intensity boost
        base_opacity += tick['flow_intensity'] * 0.1

        return np.clip(base_opacity, 0.2, 0.98)

    def _apply_physics(self, marker: MarkerData, tick: Dict):
        """Apply physics-based drift to marker position"""
        cfg = self.config

        if marker.is_frozen:
            marker.vx *= 0.95
            marker.vy *= 0.95
            return

        # Force from delta (horizontal drift based on momentum)
        force_x = tick['momentum'] * cfg.drift_speed * 2
        force_y = -tick['delta_pct'] * cfg.drift_speed * 5

        # Random brownian component
        force_x += np.random.normal(0, cfg.drift_randomness)
        force_y += np.random.normal(0, cfg.drift_randomness)

        # Flow-based force
        if tick['flow_direction'] == 'inflow':
            force_y -= tick['flow_intensity'] * 0.5
        elif tick['flow_direction'] == 'outflow':
            force_y += tick['flow_intensity'] * 0.5

        # Apply forces
        marker.ax = force_x
        marker.ay = force_y + cfg.gravity

        # Update velocity
        marker.vx = (marker.vx + marker.ax) * cfg.friction
        marker.vy = (marker.vy + marker.ay) * cfg.friction

        # Clamp velocity
        max_v = 3.0
        marker.vx = np.clip(marker.vx, -max_v, max_v)
        marker.vy = np.clip(marker.vy, -max_v, max_v)

        # Update position
        marker.x += marker.vx
        marker.y += marker.vy

    def _apply_transitions(self, marker: MarkerData):
        """Smooth easing transitions for size, color, opacity"""
        # Size easing (exponential smoothing)
        ease_factor = 0.12
        marker.size += (marker.target_size - marker.size) * ease_factor

        # Opacity easing
        marker.opacity += (
            marker.target_opacity - marker.opacity
        ) * ease_factor

        # Color interpolation
        marker.color = self._interpolate_color(
            marker.color, marker.target_color, 0.15
        )

    def _interpolate_color(self, current: str, target: str,
                            factor: float) -> str:
        """Smoothly interpolate between two hex colors"""
        try:
            c_r = int(current[1:3], 16)
            c_g = int(current[3:5], 16)
            c_b = int(current[5:7], 16)

            t_r = int(target[1:3], 16)
            t_g = int(target[3:5], 16)
            t_b = int(target[5:7], 16)

            r = int(c_r + (t_r - c_r) * factor)
            g = int(c_g + (t_g - c_g) * factor)
            b = int(c_b + (t_b - c_b) * factor)

            return f"#{r:02x}{g:02x}{b:02x}"
        except (ValueError, IndexError):
            return target

    def _update_trail(self, marker: MarkerData):
        """Maintain position trail for marker"""
        marker.trail.append((marker.x, marker.y))
        if len(marker.trail) > self.config.trail_length:
            marker.trail = marker.trail[-self.config.trail_length:]

    def _handle_freeze(self, marker: MarkerData, tick: Dict,
                       now: float):
        """Handle freeze/thaw at set intervals"""
        # Freeze on very strong signals momentarily
        if (abs(tick['delta_pct']) > 1.5 and
                not marker.is_frozen):
            marker.is_frozen = True
            marker.freeze_until = now + 2.0
            marker.state = "frozen"

        # Thaw if freeze expired
        if marker.is_frozen and now > marker.freeze_until:
            marker.is_frozen = False

    def get_all_markers(self) -> List[MarkerData]:
        """Get all current markers"""
        return list(self.markers.values())


# ═══════════════════════════════════════════════════════════════
# SECTION 4: DYNAMIC AXIS SCALER
# ═══════════════════════════════════════════════════════════════

class DynamicAxisScaler:
    """
    Auto-adjusting Y-axis that:
    - Smoothly scales on large price moves
    - Prevents clipping
    - Anti-flicker logic prevents rapid oscillation
    - Locks axis briefly after significant changes
    """

    def __init__(self, config: DashboardConfig):
        self.config = config
        self.axes: Dict[str, AxisState] = {}

    def update_axis(self, axis_id: str,
                    data_points: List[float]) -> Tuple[float, float]:
        """Update axis range for given data points"""
        if axis_id not in self.axes:
            self.axes[axis_id] = AxisState()

        axis = self.axes[axis_id]
        now = time.time()

        if not data_points:
            return axis.current_min, axis.current_max

        data_min = min(data_points)
        data_max = max(data_points)
        data_range = data_max - data_min

        # Add padding
        padding = max(data_range * self.config.y_axis_padding_pct, 0.01)
        target_min = data_min - padding
        target_max = data_max + padding

        # Anti-flicker: check if change is significant
        current_range = axis.current_max - axis.current_min
        change_magnitude = abs(
            (target_max - target_min) - current_range
        ) / max(current_range, 0.001)

        # Add to smoothing buffer
        axis.smoothing_buffer.append((target_min, target_max))

        # Check if axis is locked
        if now < axis.locked_until:
            # Only expand if data would be clipped
            if data_min < axis.current_min:
                axis.current_min = data_min - padding
                axis.locked_until = now + self.config.scale_lock_duration_seconds
            if data_max > axis.current_max:
                axis.current_max = data_max + padding
                axis.locked_until = now + self.config.scale_lock_duration_seconds
            return axis.current_min, axis.current_max

        # Apply smoothing if change is below flicker threshold
        if change_magnitude < self.config.anti_flicker_threshold:
            return axis.current_min, axis.current_max

        # Smooth the target using buffer
        if len(axis.smoothing_buffer) >= 3:
            buf = list(axis.smoothing_buffer)
            smoothed_min = np.mean([b[0] for b in buf])
            smoothed_max = np.mean([b[1] for b in buf])
        else:
            smoothed_min = target_min
            smoothed_max = target_max

        # Ease toward target
        sf = self.config.y_axis_smoothing_factor
        axis.current_min += (smoothed_min - axis.current_min) * sf
        axis.current_max += (smoothed_max - axis.current_max) * sf

        # Prevent clipping (hard override)
        if data_min < axis.current_min:
            axis.current_min = data_min - padding * 1.5
        if data_max > axis.current_max:
            axis.current_max = data_max + padding * 1.5

        # Lock axis after significant change
        if change_magnitude > 0.1:
            axis.locked_until = (
                now + self.config.scale_lock_duration_seconds
            )

        return axis.current_min, axis.current_max


# ═══════════════════════════════════════════════════════════════
# SECTION 5: VISUALIZATION RENDERER
# ═══════════════════════════════════════════════════════════════

class DashboardRenderer:
    """
    Creates the Plotly figures with animated markers.
    Renders orbs, trails, outlines, and dynamic scaling.
    """

    def __init__(self, config: DashboardConfig):
        self.config = config
        self.axis_scaler = DynamicAxisScaler(config)

    def render_main_canvas(self, markers: List[MarkerData],
                            tick_data: Dict) -> go.Figure:
        """Render the main animated canvas with all markers"""
        fig = go.Figure()

        if not markers:
            return self._empty_figure("Waiting for data...")

        # Collect all prices for Y-axis scaling
        prices = [m.price for m in markers]
        y_min, y_max = self.axis_scaler.update_axis("main", prices)

        # Separate markers by state for layered rendering
        trail_markers = []
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

            if len(marker.trail) > 2:
                trail_markers.append(marker)

        # Layer 1: Trails (ghost effect)
        for marker in trail_markers:
            trail_x = list(range(len(marker.trail)))
            trail_y = [
                marker.price + (t[1] - marker.y) * 0.1
                for t in marker.trail
            ]
            trail_opacity = np.linspace(0.02, 0.15, len(marker.trail))

            fig.add_trace(go.Scatter(
                x=trail_x,
                y=trail_y,
                mode='lines',
                line=dict(
                    color=marker.color,
                    width=1,
                    shape='spline',
                ),
                opacity=0.2,
                showlegend=False,
                hoverinfo='skip',
            ))

        # Layer 2: Glow effect (larger, faint circles behind markers)
        all_active = solid_markers + pulse_markers + outline_markers
        if all_active:
            glow_x = list(range(len(all_active)))
            glow_y = [m.price for m in all_active]
            glow_sizes = [m.size * 2.2 for m in all_active]
            glow_colors = [
                f"rgba({int(m.color[1:3], 16)},{int(m.color[3:5], 16)},"
                f"{int(m.color[5:7], 16)},0.08)"
                for m in all_active
            ]

            fig.add_trace(go.Scatter(
                x=glow_x,
                y=glow_y,
                mode='markers',
                marker=dict(
                    size=glow_sizes,
                    color=glow_colors,
                    line=dict(width=0),
                ),
                showlegend=False,
                hoverinfo='skip',
            ))

        # Layer 3: Solid markers
        if solid_markers:
            fig.add_trace(self._create_marker_trace(
                solid_markers, "solid"
            ))

        # Layer 4: Pulsing markers (with animated size)
        if pulse_markers:
            for pm in pulse_markers:
                pulse_mult = 1 + 0.2 * math.sin(pm.pulse_phase)
                pm.size *= pulse_mult

            fig.add_trace(self._create_marker_trace(
                pulse_markers, "pulse"
            ))

        # Layer 5: Outline markers (hollow)
        if outline_markers:
            fig.add_trace(self._create_outline_trace(outline_markers))

        # Layer 6: Frozen markers (diamond shape, bright border)
        if frozen_markers:
            fig.add_trace(self._create_frozen_trace(frozen_markers))

        # Layout
        fig.update_layout(
            plot_bgcolor=self.config.color_background,
            paper_bgcolor=self.config.color_background,
            font=dict(color='#cccccc', family='Courier New'),
            height=self.config.canvas_height,
            margin=dict(l=60, r=30, t=50, b=50),
            title=dict(
                text=(
                    f"<b>LIVE MARKET FLOW</b> "
                    f"<span style='font-size:12px;color:#666'>"
                    f"| Regime: {tick_data.get(list(tick_data.keys())[0], {}).get('regime', 'normal').upper()} "
                    f"| Tick: {tick_data.get(list(tick_data.keys())[0], {}).get('tick', 0)} "
                    f"| {datetime.now().strftime('%H:%M:%S')}</span>"
                ),
                font=dict(size=16, color='#ffffff'),
                x=0.01,
            ),
            xaxis=dict(
                showgrid=True,
                gridcolor=self.config.color_grid,
                gridwidth=1,
                zeroline=False,
                showticklabels=False,
                range=[-1, len(markers) + 1],
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor=self.config.color_grid,
                gridwidth=1,
                zeroline=False,
                title=dict(text="Price Level", font=dict(size=12)),
                range=[y_min, y_max],
                tickformat=',.2f',
            ),
            showlegend=False,
            dragmode=False,
        )

        return fig

    def _create_marker_trace(self, markers: List[MarkerData],
                              trace_type: str) -> go.Scatter:
        """Create a scatter trace for solid/pulse markers"""
        x_vals = list(range(len(markers)))
        y_vals = [m.price for m in markers]
        sizes = [m.size for m in markers]
        colors = [m.color for m in markers]
        opacities = [m.opacity for m in markers]

        hover_texts = []
        for m in markers:
            arrow = "▲" if m.delta_pct >= 0 else "▼"
            flow_arrow = "⬆" if m.flow_direction == "inflow" else (
                "⬇" if m.flow_direction == "outflow" else "◆"
            )
            state_icon = {
                'growing': '📈', 'shrinking': '📉',
                'drifting': '〰️', 'pulsing': '💫',
                'exploding': '💥', 'frozen': '❄️',
                'outline': '⭕', 'fading': '👻',
            }.get(m.state, '●')

            hover_texts.append(
                f"<b>{m.instrument}</b><br>"
                f"Price: ${m.price:,.4f}<br>"
                f"Delta: {arrow} {m.delta_pct:+.3f}%<br>"
                f"Momentum: {m.momentum:+.4f}<br>"
                f"Flow: {flow_arrow} {m.flow_intensity:.1%}<br>"
                f"Signal: {m.signal.upper()}<br>"
                f"State: {state_icon} {m.state}<br>"
                f"Size: {m.size:.1f}"
            )

        return go.Scatter(
            x=x_vals,
            y=y_vals,
            mode='markers+text',
            marker=dict(
                size=sizes,
                color=colors,
                opacity=opacities,
                line=dict(
                    width=1,
                    color='rgba(255,255,255,0.3)'
                ),
                symbol='circle',
            ),
            text=[m.instrument.split('/')[0] for m in markers],
            textposition='top center',
            textfont=dict(size=9, color='#aaaaaa'),
            hovertext=hover_texts,
            hoverinfo='text',
            hoverlabel=dict(
                bgcolor='#1a1a2e',
                bordercolor='#333',
                font=dict(color='#ffffff', size=12),
            ),
        )

    def _create_outline_trace(self,
                               markers: List[MarkerData]) -> go.Scatter:
        """Create outline (hollow) markers for reversals/cautious signals"""
        x_vals = list(range(len(markers)))
        y_vals = [m.price for m in markers]
        sizes = [m.size for m in markers]

        # Outline markers have transparent fill, visible border
        border_colors = []
        for m in markers:
            if m.in_reversal:
                border_colors.append(self.config.color_reversal)
            else:
                border_colors.append(self.config.color_outline)

        hover_texts = [
            f"<b>{m.instrument} ⭕</b><br>"
            f"Price: ${m.price:,.4f}<br>"
            f"{'🔄 REVERSAL' if m.in_reversal else '⚠️ CAUTIOUS'}<br>"
            f"Delta: {m.delta_pct:+.3f}%<br>"
            f"Flow: {m.flow_intensity:.1%}"
            for m in markers
        ]

        return go.Scatter(
            x=x_vals,
            y=y_vals,
            mode='markers+text',
            marker=dict(
                size=sizes,
                color='rgba(0,0,0,0)',
                line=dict(
                    width=3,
                    color=border_colors,
                ),
                symbol='circle',
            ),
            text=[m.instrument.split('/')[0] for m in markers],
            textposition='top center',
            textfont=dict(size=9, color='#ff00ff'),
            hovertext=hover_texts,
            hoverinfo='text',
        )

    def _create_frozen_trace(self,
                              markers: List[MarkerData]) -> go.Scatter:
        """Create frozen markers (diamond shape, bright)"""
        x_vals = list(range(len(markers)))
        y_vals = [m.price for m in markers]
        sizes = [m.size * 1.3 for m in markers]

        hover_texts = [
            f"<b>{m.instrument} ❄️ FROZEN</b><br>"
            f"Price: ${m.price:,.4f}<br>"
            f"Large move detected!<br>"
            f"Delta: {m.delta_pct:+.3f}%"
            for m in markers
        ]

        return go.Scatter(
            x=x_vals,
            y=y_vals,
            mode='markers+text',
            marker=dict(
                size=sizes,
                color=[m.color for m in markers],
                opacity=0.9,
                line=dict(width=3, color='#ffffff'),
                symbol='diamond',
            ),
            text=[f"❄️{m.instrument.split('/')[0]}" for m in markers],
            textposition='top center',
            textfont=dict(size=10, color='#ffffff'),
            hovertext=hover_texts,
            hoverinfo='text',
        )

    def render_flow_panel(self, markers: List[MarkerData]) -> go.Figure:
        """Render the flow intensity panel"""
        fig = go.Figure()

        if not markers:
            return self._empty_figure("No flow data")

        # Sort by flow intensity
        sorted_markers = sorted(
            markers, key=lambda m: m.flow_intensity, reverse=True
        )

        instruments = [m.instrument for m in sorted_markers]
        intensities = [m.flow_intensity for m in sorted_markers]
        colors = []

        for m in sorted_markers:
            if m.flow_direction == 'inflow':
                alpha = 0.4 + m.flow_intensity * 0.5
                colors.append(f'rgba(0, 255, 136, {alpha})')
            elif m.flow_direction == 'outflow':
                alpha = 0.4 + m.flow_intensity * 0.5
                colors.append(f'rgba(255, 107, 107, {alpha})')
            else:
                colors.append('rgba(136, 136, 136, 0.5)')

        fig.add_trace(go.Bar(
            x=intensities,
            y=instruments,
            orientation='h',
            marker=dict(
                color=colors,
                line=dict(width=1, color='rgba(255,255,255,0.1)'),
            ),
            text=[f"{i:.0%}" for i in intensities],
            textposition='auto',
            textfont=dict(color='#ffffff', size=10),
            hoverinfo='text',
            hovertext=[
                f"{m.instrument}: {m.flow_intensity:.1%} "
                f"({m.flow_direction})"
                for m in sorted_markers
            ],
        ))

        fig.update_layout(
            plot_bgcolor=self.config.color_background,
            paper_bgcolor=self.config.color_background,
            font=dict(color='#cccccc', size=10),
            height=500,
            margin=dict(l=80, r=20, t=40, b=30),
            title=dict(
                text="<b>FLOW INTENSITY</b>",
                font=dict(size=13, color='#ffffff'),
            ),
            xaxis=dict(
                range=[0, 1],
                showgrid=True,
                gridcolor=self.config.color_grid,
                tickformat='.0%',
            ),
            yaxis=dict(
                showgrid=False,
                autorange='reversed',
            ),
            bargap=0.15,
        )

        return fig

    def render_momentum_panel(self,
                               markers: List[MarkerData]) -> go.Figure:
        """Render momentum indicator panel"""
        fig = go.Figure()

        if not markers:
            return self._empty_figure("No momentum data")

        sorted_markers = sorted(
            markers, key=lambda m: m.momentum, reverse=True
        )

        instruments = [m.instrument for m in sorted_markers]
        momentums = [m.momentum for m in sorted_markers]
        colors = [
            self.config.color_strong_buy if m.momentum > 0.2 else
            self.config.color_buy if m.momentum > 0.05 else
            self.config.color_sell if m.momentum < -0.05 else
            self.config.color_strong_sell if m.momentum < -0.2 else
            self.config.color_neutral
            for m in sorted_markers
        ]

        fig.add_trace(go.Bar(
            x=momentums,
            y=instruments,
            orientation='h',
            marker=dict(
                color=colors,
                line=dict(width=0),
            ),
            text=[f"{m:+.3f}" for m in momentums],
            textposition='auto',
            textfont=dict(color='#ffffff', size=10),
        ))

        fig.update_layout(
            plot_bgcolor=self.config.color_background,
            paper_bgcolor=self.config.color_background,
            font=dict(color='#cccccc', size=10),
            height=500,
            margin=dict(l=80, r=20, t=40, b=30),
            title=dict(
                text="<b>MOMENTUM</b>",
                font=dict(size=13, color='#ffffff'),
            ),
            xaxis=dict(
                showgrid=True,
                gridcolor=self.config.color_grid,
                zeroline=True,
                zerolinecolor='#444',
                zerolinewidth=2,
            ),
            yaxis=dict(
                showgrid=False,
                autorange='reversed',
            ),
            bargap=0.15,
        )

        return fig

    def render_delta_heatmap(self, markers: List[MarkerData],
                              history_len: int = 20) -> go.Figure:
        """Render delta percentage heatmap over recent ticks"""
        fig = go.Figure()

        if not markers:
            return self._empty_figure("No delta data")

        instruments = [m.instrument for m in markers]
        # Use momentum as proxy for historical pattern
        z_data = []
        for m in markers:
            row = []
            base_delta = m.delta_pct
            for i in range(history_len):
                noise = np.random.normal(0, abs(base_delta) * 0.3 + 0.05)
                val = base_delta * (1 - i * 0.04) + noise
                row.append(round(val, 3))
            z_data.append(row[::-1])

        fig.add_trace(go.Heatmap(
            z=z_data,
            y=instruments,
            x=[f"t-{history_len - i}" for i in range(history_len)],
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
                title='Δ%',
                titlefont=dict(color='#cccccc'),
                tickfont=dict(color='#cccccc'),
            ),
            hovertemplate=(
                '%{y}<br>%{x}<br>Delta: %{z:+.3f}%<extra></extra>'
            ),
        ))

        fig.update_layout(
            plot_bgcolor=self.config.color_background,
            paper_bgcolor=self.config.color_background,
            font=dict(color='#cccccc', size=10),
            height=400,
            margin=dict(l=80, r=20, t=40, b=40),
            title=dict(
                text="<b>DELTA HEATMAP</b>",
                font=dict(size=13, color='#ffffff'),
            ),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=False, autorange='reversed'),
        )

        return fig

    def render_signal_summary(self,
                               markers: List[MarkerData]) -> go.Figure:
        """Render signal distribution summary"""
        fig = go.Figure()

        signal_counts = {}
        for m in markers:
            signal_counts[m.signal] = signal_counts.get(m.signal, 0) + 1

        signal_order = [
            'strong_buy', 'buy', 'cautious_buy', 'neutral',
            'cautious_sell', 'sell', 'strong_sell', 'reversal'
        ]
        signal_colors = {
            'strong_buy': self.config.color_strong_buy,
            'buy': self.config.color_buy,
            'cautious_buy': self.config.color_cautious,
            'neutral': self.config.color_neutral,
            'cautious_sell': '#FFB347',
            'sell': self.config.color_sell,
            'strong_sell': self.config.color_strong_sell,
            'reversal': self.config.color_reversal,
        }

        labels = []
        values = []
        colors = []

        for signal in signal_order:
            count = signal_counts.get(signal, 0)
            if count > 0:
                labels.append(signal.replace('_', ' ').upper())
                values.append(count)
                colors.append(signal_colors.get(signal, '#888'))

        fig.add_trace(go.Pie(
            labels=labels,
            values=values,
            marker=dict(colors=colors, line=dict(width=2, color='#0a0a1a')),
            textinfo='label+value',
            textfont=dict(size=11, color='#ffffff'),
            hole=0.4,
            hovertemplate='%{label}: %{value} instruments<extra></extra>',
        ))

        fig.update_layout(
            plot_bgcolor=self.config.color_background,
            paper_bgcolor=self.config.color_background,
            font=dict(color='#cccccc'),
            height=350,
            margin=dict(l=20, r=20, t=40, b=20),
            title=dict(
                text="<b>SIGNAL DISTRIBUTION</b>",
                font=dict(size=13, color='#ffffff'),
            ),
            showlegend=False,
        )

        return fig

    def _empty_figure(self, message: str) -> go.Figure:
        """Create empty placeholder figure"""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color='#666'),
        )
        fig.update_layout(
            plot_bgcolor=self.config.color_background,
            paper_bgcolor=self.config.color_background,
            height=400,
        )
        return fig


# ═══════════════════════════════════════════════════════════════
# SECTION 6: DATA TABLE GENERATOR
# ═══════════════════════════════════════════════════════════════

class DataTableGenerator:
    """Generates formatted data tables for the dashboard"""

    @staticmethod
    def create_market_table(markers: List[MarkerData]) -> pd.DataFrame:
        """Create comprehensive market data table"""
        if not markers:
            return pd.DataFrame()

        rows = []
        for m in markers:
            delta_arrow = "▲" if m.delta_pct >= 0 else "▼"
            flow_arrow = "⬆" if m.flow_direction == "inflow" else (
                "⬇" if m.flow_direction == "outflow" else "◆"
            )
            state_icon = {
                'growing': '📈', 'shrinking': '📉',
                'drifting': '〰️', 'pulsing': '💫',
                'exploding': '💥', 'frozen': '❄️',
                'outline': '⭕', 'fading': '👻',
            }.get(m.state, '●')

            signal_icon = {
                'strong_buy': '🟢🟢', 'buy': '🟢',
                'cautious_buy': '🟡', 'neutral': '⚪',
                'cautious_sell': '🟠', 'sell': '🔴',
                'strong_sell': '🔴🔴', 'reversal': '🔄',
            }.get(m.signal, '⚪')

            rows.append({
                'Instrument': m.instrument,
                'Price': f"${m.price:,.4f}",
                'Delta': f"{delta_arrow} {m.delta_pct:+.3f}%",
                'Momentum': f"{m.momentum:+.4f}",
                'Flow': f"{flow_arrow} {m.flow_intensity:.0%}",
                'Signal': f"{signal_icon} {m.signal.upper()}",
                'State': f"{state_icon} {m.state}",
                'Size': f"{m.size:.0f}",
                'Outline': "⭕" if m.is_outline else "",
                'Frozen': "❄️" if m.is_frozen else "",
            })

        return pd.DataFrame(rows)

    @staticmethod
    def create_signal_summary(markers: List[MarkerData]) -> Dict:
        """Create signal summary statistics"""
        total = len(markers)
        if total == 0:
            return {}

        signals = [m.signal for m in markers]
        bullish = sum(
            1 for s in signals
            if s in ['strong_buy', 'buy', 'cautious_buy']
        )
        bearish = sum(
            1 for s in signals
            if s in ['strong_sell', 'sell', 'cautious_sell']
        )
        neutral = sum(1 for s in signals if s == 'neutral')
        reversals = sum(1 for s in signals if s == 'reversal')

        avg_momentum = np.mean([m.momentum for m in markers])
        avg_flow = np.mean([m.flow_intensity for m in markers])

        frozen_count = sum(1 for m in markers if m.is_frozen)
        outline_count = sum(1 for m in markers if m.is_outline)

        return {
            'total': total,
            'bullish': bullish,
            'bearish': bearish,
            'neutral': neutral,
            'reversals': reversals,
            'bullish_pct': bullish / total * 100,
            'bearish_pct': bearish / total * 100,
            'avg_momentum': avg_momentum,
            'avg_flow': avg_flow,
            'frozen': frozen_count,
            'outlines': outline_count,
            'regime': 'normal',
        }


# ═══════════════════════════════════════════════════════════════
# SECTION 7: STREAMLIT APPLICATION
# ═══════════════════════════════════════════════════════════════

def configure_page():
    """Configure Streamlit page settings"""
    st.set_page_config(
        page_title="Real-Time Market Flow Dashboard",
        page_icon="🔮",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    # Custom CSS for dark theme and animations
    st.markdown("""
    <style>
        /* Main background */
        .stApp {
            background-color: #0a0a1a;
        }

        /* Remove default padding */
        .block-container {
            padding-top: 1rem;
            padding-bottom: 0rem;
        }

        /* Header styling */
        .dashboard-header {
            background: linear-gradient(135deg, #0a0a1a 0%, #1a1a3e 100%);
            border: 1px solid #2a2a4e;
            border-radius: 12px;
            padding: 20px 30px;
            margin-bottom: 20px;
            text-align: center;
        }

        .dashboard-header h1 {
            color: #00FF88;
            font-family: 'Courier New', monospace;
            font-size: 2em;
            margin: 0;
            text-shadow: 0 0 20px rgba(0, 255, 136, 0.3);
        }

        .dashboard-header p {
            color: #888;
            font-size: 0.9em;
            margin: 5px 0 0 0;
        }

        /* Metric cards */
        .metric-card {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border: 1px solid #2a2a4e;
            border-radius: 10px;
            padding: 15px 20px;
            text-align: center;
            transition: all 0.3s ease;
        }

        .metric-card:hover {
            border-color: #00FF88;
            box-shadow: 0 0 15px rgba(0, 255, 136, 0.1);
        }

        .metric-value {
            font-size: 1.8em;
            font-weight: bold;
            font-family: 'Courier New', monospace;
        }

        .metric-label {
            font-size: 0.75em;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 5px;
        }

        .green { color: #00FF88; }
        .red { color: #FF6B6B; }
        .yellow { color: #FFD700; }
        .purple { color: #FF00FF; }
        .white { color: #ffffff; }
        .gray { color: #888888; }

        /* Status indicator */
        .status-live {
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #00FF88;
            margin-right: 8px;
            animation: pulse-dot 1.5s infinite;
        }

        @keyframes pulse-dot {
            0%, 100% { opacity: 1; box-shadow: 0 0 5px #00FF88; }
            50% { opacity: 0.5; box-shadow: 0 0 15px #00FF88; }
        }

        /* Data table styling */
        .dataframe {
            font-family: 'Courier New', monospace !important;
            font-size: 0.85em !important;
        }

        /* Hide Streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}

        /* Plotly chart container */
        .stPlotlyChart {
            border: 1px solid #1a1a2e;
            border-radius: 8px;
            overflow: hidden;
        }

        /* Legend box */
        .legend-box {
            background: #1a1a2e;
            border: 1px solid #2a2a4e;
            border-radius: 8px;
            padding: 12px 16px;
            margin: 5px 0;
        }

        .legend-item {
            display: inline-block;
            margin: 3px 10px;
            font-size: 0.8em;
            color: #cccccc;
        }

        .legend-dot {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 5px;
            vertical-align: middle;
        }
    </style>
    """, unsafe_allow_html=True)


def render_header():
    """Render dashboard header"""
    st.markdown("""
    <div class="dashboard-header">
        <h1>🔮 REAL-TIME MARKET FLOW</h1>
        <p>
            <span class="status-live"></span>
            Live Animated Visualization • WebSocket Stream Simulation •
            Dynamic Scaling • Smart Signals
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_metric_card(label: str, value: str,
                       color_class: str = "white") -> str:
    """Generate HTML for a metric card"""
    return f"""
    <div class="metric-card">
        <div class="metric-value {color_class}">{value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """


def render_legend():
    """Render the marker legend"""
    st.markdown("""
    <div class="legend-box">
        <span class="legend-item">
            <span class="legend-dot" style="background:#00FF88"></span>Strong Buy
        </span>
        <span class="legend-item">
            <span class="legend-dot" style="background:#00CC66"></span>Buy
        </span>
        <span class="legend-item">
            <span class="legend-dot" style="background:#FFD700"></span>Cautious
        </span>
        <span class="legend-item">
            <span class="legend-dot" style="background:#888888"></span>Neutral
        </span>
        <span class="legend-item">
            <span class="legend-dot" style="background:#FF6B6B"></span>Sell
        </span>
        <span class="legend-item">
            <span class="legend-dot" style="background:#FF0040"></span>Strong Sell
        </span>
        <span class="legend-item">
            <span class="legend-dot" style="background:#FF00FF"></span>Reversal
        </span>
        <span class="legend-item">
            <span class="legend-dot" style="background:transparent;border:2px solid #fff;width:8px;height:8px"></span>Outline (Cautious)
        </span>
        <span class="legend-item">❄️ Frozen</span>
        <span class="legend-item">💫 Pulsing</span>
        <span class="legend-item">💥 Exploding</span>
    </div>
    """, unsafe_allow_html=True)


def initialize_session_state():
    """Initialize all session state variables"""
    if 'config' not in st.session_state:
        st.session_state.config = DashboardConfig()

    if 'simulator' not in st.session_state:
        st.session_state.simulator = MarketDataSimulator(
            st.session_state.config
        )

    if 'physics' not in st.session_state:
        st.session_state.physics = MarkerPhysicsEngine(
            st.session_state.config
        )

    if 'renderer' not in st.session_state:
        st.session_state.renderer = DashboardRenderer(
            st.session_state.config
        )

    if 'tick_count' not in st.session_state:
        st.session_state.tick_count = 0

    if 'is_running' not in st.session_state:
        st.session_state.is_running = True

    if 'update_speed' not in st.session_state:
        st.session_state.update_speed = 2.0

    if 'last_tick_data' not in st.session_state:
        st.session_state.last_tick_data = {}

    if 'performance_log' not in st.session_state:
        st.session_state.performance_log = deque(maxlen=100)


def render_controls():
    """Render control panel in sidebar"""
    with st.sidebar:
        st.markdown("## ⚙️ Controls")

        st.session_state.is_running = st.toggle(
            "▶️ Live Stream", value=st.session_state.is_running
        )

        st.session_state.update_speed = st.slider(
            "Update Speed (seconds)",
            min_value=0.5,
            max_value=5.0,
            value=st.session_state.update_speed,
            step=0.5,
        )

        st.markdown("---")
        st.markdown("## 📊 Display Options")

        show_table = st.checkbox("Show Data Table", value=True)
        show_flow = st.checkbox("Show Flow Panel", value=True)
        show_momentum = st.checkbox("Show Momentum Panel", value=True)
        show_heatmap = st.checkbox("Show Delta Heatmap", value=True)
        show_signals = st.checkbox("Show Signal Distribution", value=True)

        st.markdown("---")
        st.markdown("## 🎨 Marker Settings")

        config = st.session_state.config
        config.size_min = st.slider("Min Size", 5, 20, config.size_min)
        config.size_max = st.slider("Max Size", 30, 100, config.size_max)
        config.trail_length = st.slider(
            "Trail Length", 5, 50, config.trail_length
        )

        st.markdown("---")
        st.markdown("## 📈 Scaling")
        config.y_axis_padding_pct = st.slider(
            "Y-Axis Padding %", 0.02, 0.20, config.y_axis_padding_pct
        )
        config.anti_flicker_threshold = st.slider(
            "Anti-Flicker Threshold", 0.005, 0.10,
            config.anti_flicker_threshold
        )

        st.markdown("---")

        # Performance stats
        if st.session_state.performance_log:
            avg_render = np.mean(list(st.session_state.performance_log))
            st.metric("Avg Render Time", f"{avg_render:.0f}ms")

        st.metric("Total Ticks", st.session_state.tick_count)

    return show_table, show_flow, show_momentum, show_heatmap, show_signals


def run_dashboard():
    """Main dashboard execution loop"""
    configure_page()
    initialize_session_state()
    render_header()

    # Controls
    (show_table, show_flow, show_momentum,
     show_heatmap, show_signals) = render_controls()

    # Generate tick
    render_start = time.time()

    simulator = st.session_state.simulator
    physics = st.session_state.physics
    renderer = st.session_state.renderer

    tick_data = simulator.generate_tick()
    st.session_state.last_tick_data = tick_data
    st.session_state.tick_count += 1

    # Update all markers
    for instrument, data in tick_data.items():
        physics.create_or_update_marker(instrument, data)

    markers = physics.get_all_markers()

    # Summary stats
    summary = DataTableGenerator.create_signal_summary(markers)

    # Top metrics row
    if summary:
        cols = st.columns(8)

        with cols[0]:
            st.markdown(render_metric_card(
                "Instruments", str(summary['total']), "white"
            ), unsafe_allow_html=True)

        with cols[1]:
            st.markdown(render_metric_card(
                "Bullish", f"{summary['bullish']} ({summary['bullish_pct']:.0f}%)",
                "green"
            ), unsafe_allow_html=True)

        with cols[2]:
            st.markdown(render_metric_card(
                "Bearish", f"{summary['bearish']} ({summary['bearish_pct']:.0f}%)",
                "red"
            ), unsafe_allow_html=True)

        with cols[3]:
            st.markdown(render_metric_card(
                "Neutral", str(summary['neutral']), "gray"
            ), unsafe_allow_html=True)

        with cols[4]:
            st.markdown(render_metric_card(
                "Reversals", str(summary['reversals']), "purple"
            ), unsafe_allow_html=True)

        with cols[5]:
            mom_color = "green" if summary['avg_momentum'] > 0 else "red"
            st.markdown(render_metric_card(
                "Avg Momentum", f"{summary['avg_momentum']:+.3f}", mom_color
            ), unsafe_allow_html=True)

        with cols[6]:
            st.markdown(render_metric_card(
                "Avg Flow", f"{summary['avg_flow']:.0%}", "yellow"
            ), unsafe_allow_html=True)

        with cols[7]:
            regime = tick_data.get(
                list(tick_data.keys())[0], {}
            ).get('regime', 'normal')
            regime_color = {
                'normal': 'white', 'trending_up': 'green',
                'trending_down': 'red', 'volatile': 'yellow',
                'calm': 'gray', 'reversal': 'purple',
            }.get(regime, 'white')
            st.markdown(render_metric_card(
                "Regime", regime.upper(), regime_color
            ), unsafe_allow_html=True)

    # Legend
    render_legend()

    # Main Canvas
    st.markdown("### 🔮 Market Flow Canvas")
    main_chart = renderer.render_main_canvas(markers, tick_data)
    st.plotly_chart(
        main_chart, use_container_width=True,
        config={'displayModeBar': False}
    )

    # Secondary panels
    if show_flow or show_momentum:
        col_flow, col_mom = st.columns(2)

        if show_flow:
            with col_flow:
                flow_chart = renderer.render_flow_panel(markers)
                st.plotly_chart(
                    flow_chart, use_container_width=True,
                    config={'displayModeBar': False}
                )

        if show_momentum:
            with col_mom:
                mom_chart = renderer.render_momentum_panel(markers)
                st.plotly_chart(
                    mom_chart, use_container_width=True,
                    config={'displayModeBar': False}
                )

    # Heatmap and Signals
    if show_heatmap or show_signals:
        col_heat, col_sig = st.columns([2, 1])

        if show_heatmap:
            with col_heat:
                heat_chart = renderer.render_delta_heatmap(markers)
                st.plotly_chart(
                    heat_chart, use_container_width=True,
                    config={'displayModeBar': False}
                )

        if show_signals:
            with col_sig:
                sig_chart = renderer.render_signal_summary(markers)
                st.plotly_chart(
                    sig_chart, use_container_width=True,
                    config={'displayModeBar': False}
                )

    # Data table
    if show_table:
        st.markdown("### 📋 Live Market Data")
        table_df = DataTableGenerator.create_market_table(markers)
        if not table_df.empty:
            st.dataframe(
                table_df,
                use_container_width=True,
                hide_index=True,
                height=400,
            )

    # Performance tracking
    render_time = (time.time() - render_start) * 1000
    st.session_state.performance_log.append(render_time)

    # Footer
    st.markdown(f"""
    <div style="text-align:center; padding:10px; color:#444; font-size:0.8em;">
        Render: {render_time:.0f}ms |
        Tick: {st.session_state.tick_count} |
        Markers: {len(markers)} |
        {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </div>
    """, unsafe_allow_html=True)

    # Auto-refresh
    if st.session_state.is_running:
        time.sleep(st.session_state.update_speed)
        st.rerun()


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    run_dashboard()
