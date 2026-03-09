# 🔮 Real-Time Market Flow Dashboard

Production-grade animated canvas dashboard with live market data visualization.

## Features

- **Live WebSocket Simulation** - High-fidelity market data with correlated instruments, regime changes, and realistic volume patterns
- **Animated Orb Markers** - Physics-based particles that grow, shrink, drift, pulse, freeze, and explode based on market signals
- **Dynamic Y-Axis Scaling** - Auto-adjusts on large moves with anti-flicker logic and scale locking to prevent visual jitter
- **Outline Mode** - Hollow markers for intra-territory reversals and cautious signals
- **Threshold-Based Sizing** - 4-tier sizing logic (low/mid/high/max) with smooth easing transitions between states
- **Low-Latency Rendering** - Optimized for bursty updates with sub-100ms render times
- **6 Visualization Panels** - Main canvas, flow intensity, momentum, delta heatmap, signal distribution, live data table

## Quick Start

```bash
pip install -r requirements.txt
streamlit run app.py
