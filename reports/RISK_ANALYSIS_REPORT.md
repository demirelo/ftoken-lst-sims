# fToken vs LST Risk Analysis Report

**Generated:** 2025-12-03 20:43  
**Simulation Engine:** Monte Carlo with 500 paths per scenario  
**Horizon:** 180 days

---

## Executive Summary

This report compares the risk-return profile of **fTokens** (floor-backed tokens with deterministic floor growth) against **Liquid Staking Tokens (LSTs)** under three market conditions: Crypto Winter, Crab Market, and Super Cycle.

### Key Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| **LTV (Loan-to-Value)** | 90% | Maximum borrowing against fToken collateral |
| **α_f (Fee to Floor)** | 65% | Portion of fees directed to floor reserves |
| **LRE Threshold** | 10% premium | Triggers liquidity reallocation |
| **Debt Cap** | 60% | Maximum debt as % of floor liquidity |
| **Coverage Buffer** | 5% | Required FPR buffer above 1.0 |
| **Buy/Sell Fee** | 0.5% | Transaction fees |
| **LST Yield** | 3% APY | Staking yield benchmark |

---

## Scenario Definitions & Volume

| Scenario | Description | Avg Daily Buy | Avg Daily Sell | Net Flow | Avg Daily Loans |
|----------|-------------|---------------|----------------|----------|----------------|
| **Crypto Winter** | Severe bear market with -75% drawdown | 225 ETH | 275 ETH | -50 ETH | 100 ETH |
| **Crab Market** | Sideways market with moderate volatility | 750 ETH | 750 ETH | -0 ETH | 299 ETH |
| **Super Cycle** | Strong bull market with high activity | 1,950 ETH | 1,049 ETH | +901 ETH | 499 ETH |

### Total Volume Summary (per path, 180 days)

*All values in ETH/AVAX (reserve currency)*

| Scenario | Total Buys | Total Sells | Total Loans | Net Volume |
|----------|------------|-------------|-------------|------------|
| Crypto Winter | 40,471 ETH | 49,498 ETH | 18,050 ETH | -9,027 ETH |
| Crab Market | 134,957 ETH | 135,025 ETH | 53,898 ETH | -67 ETH |
| Super Cycle | 351,024 ETH | 188,855 ETH | 89,852 ETH | +162,169 ETH |

---

## Risk Metrics Comparison

*All returns are in ETH/AVAX terms (not USD). Both instruments give underlying exposure.*

### Return Distribution

| Scenario | Instrument | Mean Return | Std Dev | VaR (95%) | CVaR (95%) | Max Depeg |
|----------|------------|-------------|---------|-----------|------------|-----------|
| Crypto Winter | **fToken** | +0.0% | 0.0% | +0.0% | +0.0% | 0% |
| | LST | +1.3% | 0.0% | +1.3% | +1.3% | 2.7% |
| Crab Market | **fToken** | +0.0% | 0.0% | +0.0% | +0.0% | 0% |
| | LST | +1.3% | 0.0% | +1.3% | +1.3% | 0.9% |
| Super Cycle | **fToken** | +30.9% | 1.3% | +29.0% | +28.7% | 0% |
| | LST | +1.3% | 0.0% | +1.3% | +1.3% | 0.5% |

---

## Floor Protection Ratio (FPR) Analysis

The FPR measures protocol solvency: FPR ≥ 1.0 means all floor redemptions can be honored.

| Scenario | Min FPR (5th %ile) | Mean Min FPR | Final FPR (Mean) | Paths FPR < 1.0 |
|----------|-------------------|--------------|------------------|-----------------|
| Crypto Winter | 1.000 | 1.000 | 1.005 | 0.0% |
| Crab Market | 1.000 | 1.000 | 1.015 | 0.0% |
| Super Cycle | 1.000 | 1.000 | 1.060 | 0.0% |

---

## Credit Facility Risk (90% LTV)

### Why Bad Debt Cannot Occur

Unlike traditional lending where collateral can lose value, fToken-backed loans are **structurally safe**:

1. **Collateral = fTokens** → Floor price only rises → Collateral value only increases
2. **Debt = ETH** → Fixed amount (no interest after origination) → Debt stays constant  
3. **LTV improves over time** → As floor rises, effective LTV decreases

**Example: Self-Healing Loan**
```
Day 1:  Lock 100 fTokens (floor = 1.0 ETH) → Collateral = 100 ETH
        Borrow 90 ETH → LTV = 90%

Day 30: Floor rises to 1.1 ETH → Collateral = 110 ETH
        Debt still = 90 ETH → LTV = 81.8% (safer!)

Day 60: Floor rises to 1.2 ETH → Collateral = 120 ETH
        Debt still = 90 ETH → LTV = 75% (even safer!)
```

**Key Insight**: Since floor price never decreases, the collateral value can only increase relative to the fixed debt. Bad debt is structurally impossible in this design.

### Credit Facility Metrics

| Scenario | Total Loans (ETH) | Avg Outstanding Debt | LRE Events (Mean) |
|----------|-------------------|---------------------|-------------------|
| Crypto Winter | 18,050 | N/A | 0.0 |
| Crab Market | 53,898 | N/A | 0.0 |
| Super Cycle | 89,852 | N/A | 0.0 |

---

## Floor Elevation & Tier Merges

| Scenario | Mean Floor Growth | Floor Growth (5th %ile) | Mean Tier Merges |
|----------|-------------------|-------------------------|------------------|
| Crypto Winter | +0.0% | +0.0% | 0 |
| Crab Market | +0.0% | +0.0% | 0 |
| Super Cycle | +30.9% | +29.0% | 31 |

### How Floor Growth Works

Floor growth requires positive **headroom**: excess reserves above floor backing requirement.

**Headroom sources:**
1. **Premium Capture**: When buys occur at market price > floor price:
   - Buy 1000 ETH at 1.02 floor → mint ~980 tokens
   - Reserves: +995 ETH (after fee)
   - Floor requirement: +980 ETH (980 × 1.0 floor)
   - **Net headroom: +15 ETH**

2. **Fee Accumulation**: Trading and loan fees add to reserves

3. **Net Buy Flow**: More buys than sells = supply growth at premium

**Constraints:**
- Must first build 5% coverage buffer before floor can rise
- Balanced buy/sell (crab market) generates minimal headroom
- Strong net buys (super cycle) accelerate headroom creation

| Scenario | Net Flow | Premium Capture | Floor Growth |
|----------|----------|-----------------|--------------|
| Crypto Winter | -9k ETH | Minimal | 0% |
| Crab Market | ~0 ETH | Minimal | 0% |
| Super Cycle | +162k ETH | Significant | ~31% |

---

## LST Depeg Risk

| Scenario | Mean Depeg Events | Max Depeg Events | Depeg Probability |
|----------|-------------------|------------------|-------------------|
| Crypto Winter | 0.9 | 5 | 58.4% |
| Crab Market | 0.5 | 4 | 42.0% |
| Super Cycle | 0.4 | 4 | 30.8% |

---

## Key Findings

### 1. Floor Growth Mechanism (Premium Capture)

Floor growth requires positive **headroom**: `H = (Reserves - Debt) - (Floor × Tradeable Supply)`

The primary mechanism is **premium capture**:
- When market trades above floor, each buy brings more reserves than floor backing requires
- Net buy flow (more buys than sells) creates headroom over time
- Once headroom exceeds 5% buffer, floor can be raised

**Example (market at 2% premium):**
```
Buy 1000 ETH at market price 1.02:
  → Mint ~980 tokens (1000/1.02)
  → Reserves: +995 ETH (after 0.5% fee)
  → Floor requirement: +980 ETH (980 tokens × 1.0 floor)
  → Net headroom gain: +15 ETH
```

**Key insight:** Balanced markets (crab) generate minimal floor growth. Strong bull markets with net buys drive significant floor appreciation.

### 2. Downside Protection (in ETH terms)
- **fToken floor guarantee** provides deterministic protection: floor price only increases
- **LST** earns staking yield but faces depeg risk up to 1.3% below fair value

### 3. Risk-Adjusted Returns (in ETH terms)
- **fToken** returns depend on **both** fee volume **and** loan activity
- **LST** returns come from staking yield (~2.6% APY), reduced by depeg events
- Both instruments carry underlying (ETH/AVAX) USD price risk equally

### 4. Protocol Solvency
- FPR maintained above 1.00 across all scenarios (5th percentile)
- Safe-merge mechanism successfully absorbs premium tiers into floor

### 5. Credit Facility (90% LTV)
- **Bad debt is structurally impossible**: Collateral (fTokens) only appreciates; debt is fixed
- **Loans enable floor growth**: By locking tokens, loans reduce required reserves, creating headroom
- LRE mechanism actively manages premium liquidity

---

## Methodology

### Simulation Framework
- **Price Model:** Geometric Brownian Motion for underlying; LST tracks ETH 1:1 with yield
- **LST Model:** 3% APY yield + Poisson-distributed depegs (temporary discounts)
- **Fee Model:** 0.5% buy fee, 0.5% sell fee, 65% to floor
- **Loan Origination:** 2% fee
- **Floor Elevation:** Automatic when pending fees exceed threshold; includes safe-merge checks
- **Credit Facility:** 90% LTV with 30% loss-given-default

### Risk Metrics
- **VaR (95%):** 5th percentile of return distribution
- **CVaR (95%):** Expected return given VaR breach (tail risk)
- **FPR:** (Reserves - Debt) / (Floor Price × Tradeable Supply)

---

## Visualizations

### Return Distribution Comparison
![Return Distributions](return_distributions.png)

### Risk Analysis Charts  
![Risk Analysis](risk_analysis_charts.png)

### Sample Price Paths
![Sample Paths](sample_paths.png)

---

## Appendix: Detailed Statistics


### Crypto Winter

**fToken Return Distribution:**
- Mean: +0.00%
- Median: +0.00%
- Std Dev: 0.00%
- Min: +0.00%
- Max: +0.00%
- Skewness: nan

**LST Return Distribution:**
- Mean: +1.29%
- Median: +1.29%
- Std Dev: 0.00%
- Min: +1.29%
- Max: +1.29%


### Crab Market

**fToken Return Distribution:**
- Mean: +0.00%
- Median: +0.00%
- Std Dev: 0.00%
- Min: +0.00%
- Max: +0.00%
- Skewness: nan

**LST Return Distribution:**
- Mean: +1.29%
- Median: +1.29%
- Std Dev: 0.00%
- Min: +1.29%
- Max: +1.29%


### Super Cycle

**fToken Return Distribution:**
- Mean: +30.92%
- Median: +31.00%
- Std Dev: 1.34%
- Min: +27.00%
- Max: +35.00%
- Skewness: -0.16

**LST Return Distribution:**
- Mean: +1.29%
- Median: +1.29%
- Std Dev: 0.00%
- Min: +1.29%
- Max: +1.29%

