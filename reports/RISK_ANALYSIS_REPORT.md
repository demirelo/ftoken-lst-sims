# fToken vs LST Risk Analysis Report

**Generated:** 2025-12-04  
**Simulation Engine:** Monte Carlo with 500 paths per scenario  
**Horizon:** 365 days (1 year)

---

## Executive Summary

This report compares the risk-return profile of **fTokens** (floor-backed tokens with deterministic floor growth) against **Liquid Staking Tokens (LSTs)** under various market conditions over a 1-year horizon.

### Key Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| **LTV (Loan-to-Value)** | 70% | Standard borrowing against fToken collateral |
| **Fee to Floor Ratio** | 70% | Portion of fees directed to floor reserves |
| **LRE Threshold** | 2x premium | Triggers liquidity reallocation |
| **Debt Cap** | 50% | Maximum debt as % of floor liquidity |
| **Coverage Buffer** | 5% | Required FPR buffer above 1.0 |
| **Buy Fee** | 0.5% | Buy transaction fee |
| **Sell Fee** | 0.5% | Sell transaction fee |
| **Origination Fee** | 2% | Loan origination fee |
| **LST Yield** | 5% APY | Staking yield benchmark |

---

## Scenario Definitions

### Market Scenarios (365 days)

| Scenario | Description | Daily Volume | Drift (μ) | Volatility (σ) |
|----------|-------------|--------------|-----------|----------------|
| **Super Cycle** | Strong bull market | 150k ETH | +70% | 70% |
| **Crab Market** | Sideways, moderate vol | 20k ETH | +5% | 40% |
| **Crypto Winter** | Severe bear market | 30k ETH | -80% | 80% |

### Depeg Risk Parameters

| Scenario | Depeg Prob | Depeg Severity |
|----------|------------|----------------|
| Super Cycle | 0.2%/day | -2% |
| Crab Market | 0.1%/day | -3% |
| Crypto Winter | 1.0%/day | -5% |

---

## Risk Metrics Comparison (1 Year)

### Return Distribution (365 days, USD-denominated)

| Scenario | Instrument | Mean Return | VaR (95%) |
|----------|------------|-------------|-----------|
| **Super Cycle** | fToken USD | **+242.6%** | -18.7% |
| | LST USD | +102.9% | -47.8% |
| | fToken Floor (ETH) | **+73.3%** | +44.0% |
| **Crab Market** | fToken USD | **+58.3%** | -27.6% |
| | LST USD | +14.2% | -46.3% |
| | fToken Floor (ETH) | **+46.3%** | +22.0% |
| **Crypto Winter** | fToken USD | -32.6% | -86.4% |
| | LST USD | -49.7% | -90.4% |
| | fToken Floor (ETH) | **+43.0%** | +17.0% |

**Key Insights:**
- **fToken Floor always positive**: +43-73% over 1 year across all scenarios
- **fToken outperforms LST** in USD terms in all scenarios
- **VaR improvement**: fToken USD VaR is better than LST in all scenarios

---

## Floor Protection Ratio (FPR) Analysis

| Scenario | Min FPR (5th %ile) | Final FPR (Mean) | Prob FPR < 1.0 |
|----------|-------------------|------------------|----------------|
| Super Cycle | 1.182 | 4.20 | **0.0%** |
| Crab Market | 1.248 | 4.98 | **0.0%** |
| Crypto Winter | 1.140 | 4.10 | **0.0%** |

**FPR Zones:**
- Green: FPR ≥ 1.10
- Yellow: 1.05 ≤ FPR < 1.10  
- Red: FPR < 1.05

> **0% insolvency** across all 1,500 simulation paths. FPR never dropped below 1.14 even in extreme bear market conditions.

---

## Floor Elevation (1 Year)

| Scenario | Mean Growth | Growth (5th %ile) | Annualized |
|----------|-------------|-------------------|------------|
| Super Cycle | **+73.3%** | +44.0% | 73% |
| Crab Market | **+46.3%** | +22.0% | 46% |
| Crypto Winter | **+43.0%** | +17.0% | 43% |

The floor appreciates significantly over a full year due to cumulative fee generation. Even in the worst 5% of outcomes, floor growth remains strongly positive (+17-44%).

---

## Credit Facility Metrics (1 Year)

| Scenario | Supply Growth | Lock Ratio | Final Debt | Active Loans |
|----------|---------------|------------|------------|--------------|
| Super Cycle | +46.2% | 53.4% | 979k ETH | High |
| Crab Market | +6.2% | 51.0% | 579k ETH | Moderate |
| Crypto Winter | +9.5% | 34.2% | 209k ETH | Low |

### Why No Bad Debt

The fToken credit facility has **no liquidation mechanism** and **no bad debt**:

1. **Collateral = fTokens** → floor price ONLY rises → collateral value ONLY increases
2. **Debt = ETH** → fixed amount (no interest) → debt stays constant
3. **LTV improves over time** → as floor rises, effective LTV decreases

---

## LST Depeg Risk (1 Year)

| Scenario | Mean Depeg Events | Annual Impact |
|----------|-------------------|---------------|
| Super Cycle | 1.2 | -2.4% |
| Crab Market | 0.4 | -1.2% |
| Crypto Winter | **7.6** | **-38%** |

Depeg risk is **stress-correlated**: probability increases 10x during market crashes. Over a full year of crypto winter, average 7.6 depeg events significantly drag LST returns.

---

## Key Findings (1-Year Horizon)

### 1. Structural Solvency

- **0% insolvency** across all 1,500 paths (3 scenarios × 500 paths)
- FPR maintained above 1.14 even in extreme 80% drawdown scenarios
- Floor grows even during severe bear markets (+43% in crypto winter)

### 2. fToken vs LST Returns

| Scenario | fToken USD | LST USD | fToken Advantage |
|----------|------------|---------|------------------|
| Super Cycle | +242.6% | +102.9% | **+139.7%** |
| Crab Market | +58.3% | +14.2% | **+44.1%** |
| Crypto Winter | -32.6% | -49.7% | **+17.1%** |

### 3. Floor as a Hedge

The floor provides a natural hedge against underlying price decline:
- In crypto winter, underlying dropped ~80% but floor rose +43%
- Net effect: fToken USD only -32.6% vs LST -49.7%

### 4. Risk-Adjusted Performance

| Metric | fToken | LST | Winner |
|--------|--------|-----|--------|
| Sharpe Ratio | Higher | Lower | fToken |
| Max Drawdown | Limited | Unlimited | fToken |
| VaR (95%) | Better | Worse | fToken |
| Tail Risk | Bounded | Unbounded | fToken |

---

## Agent-Based Model Results (1 Year)

The agent-based model simulates heterogeneous market participants with distinct trading behaviors, providing a realistic view of market dynamics with organic buy/sell pressure.

### Agent Population (2000 Agents)

| Agent Type | Count | Behavior |
|------------|-------|----------|
| **LeverageSeeker** | 300 | Aggressive looping at low premium, profit-taking at high premium |
| **YieldSeeker** | 900 | Core holders seeking stable yield, rebalances portfolio |
| **DATAgent** | 400 | Fair-value investors, buy undervalued, sell overvalued |
| **Arbitrageur** | 200 | Short-term speculators, time-based exits |
| **FloorHolder** | 200 | Long-term capital efficiency users |

### Churn Dynamics

The model includes realistic market churn:
- **Profit-taking exits**: Agents exit probabilistically after achieving 25%+ returns
- **Stop-loss exits**: Agents cut losses at -15% drawdown
- **Time-based exits**: Maximum 45-day holding periods trigger exits
- **New entrants**: Fresh capital with ~$180 ETH mean enters to replace exits

### Agent Model Results (365 days, 100 paths)

| Scenario | Floor Growth | Supply Growth | Daily Volume | Min FPR (5th) |
|----------|--------------|---------------|--------------|---------------|
| **Super Cycle** | **+3.8%** | +27.3% | 13,624 ETH | 1.113 |
| **Crab Market** | **+3.3%** | +26.9% | 14,689 ETH | 1.113 |
| **Crypto Winter** | **+4.8%** | +22.5% | 21,079 ETH | 1.113 |

### Agent Model Key Insights

1. **Bear Market Paradox**: Crypto Winter shows the *highest* floor growth (+4.8%) because panic selling drives higher turnover (churn) and fee generation (21k ETH/day vs 14k).
2. **HODL Effect**: In Super Cycle, agents hold for profits, reducing turnover and fees, leading to slightly lower floor growth (+3.8%).
3. **Supply Stability**: Supply grows ~22-27% annually, driven by new entrants replacing exiting agents.
4. **0% Insolvency**: FPR maintained above 1.11 in all scenarios.

> **Key Insight:** Floor growth is counter-cyclical in the agent model. Panic selling in bear markets generates more fees than passive holding in bull markets.

---

## Simulation Comparison

| Aspect | Fixed-Volume Model | Agent-Based Model (2000) |
|--------|-------------------|--------------------------|
| **Volume** | Assumed (20-150k ETH/day) | Emergent (14-21k ETH/day) |
| **Floor Growth** | +43-73%/year | **+3.3-4.8%/year** |
| **Supply Growth** | +6-46%/year | +22-27%/year |
| **Insolvency** | 0% | 0% |
| **Best Use** | Capacity stress testing | Realistic market dynamics |

> **Volume vs Floor Growth Formula:**
> ```
> Annual Floor Growth ≈ (Daily Volume × 365 × 0.5% fee × 70% to floor) / Supply
> Example: (25,000 × 365 × 0.005 × 0.7) / 1,000,000 = 3.2%
> ```

---

## Methodology

### Simulation Framework

- **Price Model:** Geometric Brownian Motion
- **Volume Model:** Stress-adjusted (50% reduction in bear markets)
- **Loan Lifecycle:** Target lock ratio + probabilistic repayments + top-ups
- **Leverage Looping:** Premium-dependent probability
- **Fee Routing:** 70% to floor, 30% to governance

### Key Assumptions

1. **Loan Duration:** ~40-50 days average
2. **Leverage Participation:** 0.5-4% of tradeable supply per day
3. **Market Impact:** Not modeled for individual trades
4. **No Interest:** Loans have no interest accrual

---

## Appendix: 1-Year Comparison Table

| Metric | Super Cycle | Crab Market | Crypto Winter |
|--------|-------------|-------------|---------------|
| **Duration** | 365 days | 365 days | 365 days |
| **Drift (μ)** | +70% | +5% | -80% |
| **Volatility (σ)** | 70% | 40% | 80% |
| **Floor Growth** | +73.3% | +46.3% | +43.0% |
| **Floor VaR** | +44.0% | +22.0% | +17.0% |
| **Supply Growth** | +46.2% | +6.2% | +9.5% |
| **Lock Ratio** | 53.4% | 51.0% | 34.2% |
| **Final FPR** | 4.20 | 4.98 | 4.10 |
| **Min FPR (5th)** | 1.182 | 1.248 | 1.140 |
| **Insolvency** | 0.0% | 0.0% | 0.0% |
| **fToken USD** | +242.6% | +58.3% | -32.6% |
| **LST USD** | +102.9% | +14.2% | -49.7% |
| **Depeg Events** | 1.2 | 0.4 | 7.6 |

---

## Running the Simulations

### Fixed-Volume Model (Stress Testing)

```python
from sims.engine import SimulationEngine
from sims.scenarios import get_scenario

# Get scenario and run 1-year simulation
config = get_scenario('super_cycle')
config['horizon_days'] = 365
config['n_paths'] = 500

engine = SimulationEngine(config)
paths = engine.run()
```

### Agent-Based Model (Market Dynamics)

```python
from sims.agent_engine import AgentSimulationEngine, AgentSimConfig, ChurnConfig
from sims.agents import create_population

# Configure agent churn
churn = ChurnConfig(
    enabled=True,
    profit_exit_threshold=0.25,
    base_exit_probability=0.02,
    maintain_population=True,
)

config = AgentSimConfig(
    n_paths=200,
    horizon_days=365,
    churn_config=churn,
)

# Create 1000 agents
pop = {
    'LeverageSeeker': {'count': 150, 'initial_eth': 120},
    'YieldSeeker': {'count': 450, 'initial_eth': 80},
    'DAT': {'count': 200, 'initial_eth': 100},
    'Arbitrageur': {'count': 100, 'initial_eth': 150},
    'FloorHolder': {'count': 100, 'initial_eth': 120},
}
agents = create_population(pop)

engine = AgentSimulationEngine(config, agents)
paths = engine.run()
```

### Key Files

- `sims/models.py` - fToken model with loan lifecycle
- `sims/engine.py` - Fixed-volume Monte Carlo engine
- `sims/agent_engine.py` - Agent-based simulation engine
- `sims/agents.py` - Agent types and behaviors
- `sims/scenarios.py` - Scenario configurations

---

*Generated with two simulation approaches: (1) Fixed-volume Monte Carlo (500 paths, stress testing) and (2) Agent-based model (1000 agents, 200 paths, market dynamics). Horizon: 365 days.*
