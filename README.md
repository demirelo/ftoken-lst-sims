# fToken / Floors Market Simulation

This repository contains the **Agent-Based Simulation Framework** for the **Floors Protocol** (fToken). It models the economic dynamics, solvency mechanics, and risk profile of floor-backed tokens compared to traditional Liquid Staking Tokens (LSTs).

## What is an fToken?

An **fToken** is a yield-bearing asset backed by a **rising price floor**. Unlike LSTs which offer a fixed staking yield, fTokens capture volatility to drive floor appreciation.

### Core Mechanics

1.  **Ratchet Mechanism**: The floor price is mathematically defined to **only increase**, never decrease. It is backed 100% by reserves in the smart contract.
2.  **Volatility Harvesting**: Every transaction (buy/sell) and every loan origination generates fees.
3.  **Fee Routing**: **70% of all fees** are directed to the floor reserves, permanently raising the floor price.
4.  **Credit Facility**: Users can borrow ETH against their fTokens at 0% interest, with no liquidation risk as long as the floor supports the loan.

### The Value Proposition

*   **Bull Market**: Captures upside like ETH + amplifies returns via floor growth.
*   **Bear Market**: Provides a hard floor that cushions downside (e.g., if ETH drops 80%, fToken might only drop 30% due to the rising floor).
*   **Yield**: Generates "organic yield" from trading volume, often outperforming LST staking yields in active markets.

---

## Simulation Framework

This project uses an **Agent-Based Model (ABM)** to simulate realistic market dynamics. Instead of assuming fixed volumes, we model 2,000 individual agents with distinct psychological profiles and trading strategies.

### Agent Types

| Agent | % of Pop | Behavior |
|-------|----------|----------|
| **YieldSeeker** | 45% | Core holders seeking stable yield. Rebalances portfolio periodically. |
| **DATAgent** | 20% | Value investors. Buys when price < fair value, sells when overvalued. |
| **LeverageSeeker** | 15% | Aggressive traders. Loops leverage (borrow ETH -> buy fToken) when premium is low. |
| **Arbitrageur** | 10% | Short-term speculators exploiting price inefficiencies. |
| **FloorHolder** | 10% | Long-term holders utilizing the credit facility for capital efficiency. |

### Scenarios

We test the protocol under three distinct 1-year market regimes:
1.  **Super Cycle**: Strong bull market (+70% drift), high volume.
2.  **Crab Market**: Sideways market (+5% drift), moderate volume.
3.  **Crypto Winter**: Severe bear market (-80% crash), panic selling volume.

---

## Repository Structure

```
├── sims/                   # Core simulation logic
│   ├── agent_engine.py     # Agent-based simulation engine (main loop)
│   ├── agents.py           # Agent definitions and behavioral logic
│   ├── models.py           # fToken smart contract logic (bonding curve, loans)
│   ├── scenarios.py        # Market scenario configurations
│   └── analysis.py         # Metrics and plotting utilities
│
├── reports/                # Generated analysis reports
│   └── RISK_ANALYSIS_REPORT.md  # Comprehensive risk & return analysis
│
├── tests/                  # Unit and integration tests
│   ├── test_models.py      # Tests for fToken mechanics
│   └── test_agents.py      # Tests for agent behaviors
│
├── main.py                 # Entry point to run simulations
├── generate_risk_report.py # Script to generate the full risk report
└── Structural_Solvency.md  # Deep dive into the mathematical framework
```

## Getting Started

### Prerequisites

- Python 3.10+
- Virtual environment recommended

### Installation

```bash
# Clone the repo
git clone <repo-url>
cd ftoken-lst-sims

# Create virtual env
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running Simulations

To run the full agent-based simulation and generate the risk report:

```bash
python generate_risk_report.py
```

To run a specific scenario or experiment, you can use `main.py`:

```bash
python main.py --scenario super_cycle --agents 2000 --days 365
```

## Key Findings

Based on 1-year simulations with 2,000 agents:

1.  **fToken Outperforms LST**: With LST yields at ~2.6%, fToken floor growth (+3.0-5.0%) consistently generates higher total returns.
2.  **Counter-Cyclical Growth**: Floor growth is highest in **Crypto Winter** (+5.0%) due to panic selling volume generating massive fees.
3.  **Solvency**: The protocol maintained **0% insolvency** across all simulations, even during 80% market drawdowns.

See [RISK_ANALYSIS_REPORT.md](reports/RISK_ANALYSIS_REPORT.md) for the full analysis.
