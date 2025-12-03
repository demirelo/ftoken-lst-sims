# fToken vs LST Risk Analysis Report

**Generated:** 2025-12-03 16:28  
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
| **LST Yield** | 5% APY | Staking yield benchmark |

---

## Scenario Definitions & Volume

| Scenario | Description | Avg Daily Buy | Avg Daily Sell | Net Flow | Avg Daily Loans |
|----------|-------------|---------------|----------------|----------|----------------|
| **Crypto Winter** | Severe bear market with -75% drawdown | 225 ETH | 275 ETH | -50 ETH | 20 ETH |
| **Crab Market** | Sideways market with moderate volatility | 500 ETH | 500 ETH | -0 ETH | 80 ETH |
| **Super Cycle** | Strong bull market with high activity | 1,625 ETH | 874 ETH | +751 ETH | 150 ETH |

### Total Volume Summary (per path, 180 days)

*All values in ETH/AVAX (reserve currency)*

| Scenario | Total Buys | Total Sells | Total Loans | Net Volume |
|----------|------------|-------------|-------------|------------|
| Crypto Winter | 40,471 ETH | 49,498 ETH | 3,610 ETH | -9,027 ETH |
| Crab Market | 89,966 ETH | 90,020 ETH | 14,374 ETH | -54 ETH |
| Super Cycle | 292,519 ETH | 157,383 ETH | 26,953 ETH | +135,136 ETH |

---

## Risk Metrics Comparison

*All returns are in ETH/AVAX terms (not USD). Both instruments give underlying exposure.*

### Return Distribution

| Scenario | Instrument | Mean Return | Std Dev | VaR (95%) | CVaR (95%) | Max Depeg |
|----------|------------|-------------|---------|-----------|------------|-----------|
| Crypto Winter | **fToken** | +1.1% | 0.2% | +1.0% | +1.0% | 0% |
| | LST | +2.5% | 0.0% | +2.5% | +2.5% | 2.7% |
| Crab Market | **fToken** | +14.9% | 0.8% | +14.0% | +13.9% | 0% |
| | LST | +2.5% | 0.0% | +2.5% | +2.5% | 0.9% |
| Super Cycle | **fToken** | +64.5% | 1.4% | +62.0% | +61.7% | 0% |
| | LST | +2.5% | 0.0% | +2.5% | +2.5% | 0.5% |

---

## Floor Protection Ratio (FPR) Analysis

The FPR measures protocol solvency: FPR ≥ 1.0 means all floor redemptions can be honored.

| Scenario | Min FPR (5th %ile) | Mean Min FPR | Final FPR (Mean) | Paths FPR < 1.0 |
|----------|-------------------|--------------|------------------|-----------------|
| Crypto Winter | 1.000 | 1.000 | 1.057 | 0.0% |
| Crab Market | 1.000 | 1.000 | 1.055 | 0.0% |
| Super Cycle | 1.000 | 1.000 | 1.053 | 0.0% |

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
| Crypto Winter | 3,610 | N/A | 128.6 |
| Crab Market | 14,374 | N/A | 140.0 |
| Super Cycle | 26,953 | N/A | 173.7 |

---

## Floor Elevation & Tier Merges

| Scenario | Mean Floor Growth | Floor Growth (5th %ile) | Mean Tier Merges |
|----------|-------------------|-------------------------|------------------|
| Crypto Winter | +1.1% | +1.0% | 1 |
| Crab Market | +14.9% | +14.0% | 15 |
| Super Cycle | +64.5% | +62.0% | 64 |

---

## LST Depeg Risk

| Scenario | Mean Depeg Events | Max Depeg Events | Depeg Probability |
|----------|-------------------|------------------|-------------------|
| Crypto Winter | 0.9 | 5 | 58.4% |
| Crab Market | 0.5 | 4 | 42.0% |
| Super Cycle | 0.4 | 4 | 30.8% |

---

## Key Findings

### 1. Downside Protection (in ETH terms)
- **fToken floor guarantee** provides deterministic protection: floor price only increases
- **LST** earns staking yield but faces depeg risk up to 1.3% below fair value

### 2. Risk-Adjusted Returns (in ETH terms)
- **fToken** returns come from fee accumulation: higher volume → faster floor growth
- **LST** returns come from staking yield (~5% APY), reduced by depeg events
- Both instruments carry underlying (ETH/AVAX) USD price risk equally

### 3. Protocol Solvency
- FPR maintained above 1.00 across all scenarios (5th percentile)
- Safe-merge mechanism successfully absorbs premium tiers into floor

### 4. Credit Facility (90% LTV)
- Higher LTV increases bad debt risk in volatile scenarios
- LRE mechanism actively manages premium liquidity

---

## Methodology

### Simulation Framework
- **Price Model:** Geometric Brownian Motion for underlying; LST tracks ETH 1:1 with yield
- **LST Model:** 5% APY yield + Poisson-distributed depegs (temporary discounts)
- **Fee Model:** 0.5% buy fee, 0.5% sell fee, 65% to floor
- **Loan Origination:** 2% fee
- **Floor Elevation:** Automatic when pending fees exceed threshold; includes safe-merge checks
- **Credit Facility:** 90% LTV with 30% loss-given-default

### Risk Metrics
- **VaR (95%):** 5th percentile of return distribution
- **CVaR (95%):** Expected return given VaR breach (tail risk)
- **FPR:** (Reserves - Debt) / (Floor Price × Tradeable Supply)

---

## Appendix: Detailed Statistics


### Crypto Winter

**fToken Return Distribution:**
- Mean: +1.06%
- Median: +1.00%
- Std Dev: 0.23%
- Min: +1.00%
- Max: +2.00%
- Skewness: 3.86

**LST Return Distribution:**
- Mean: +2.50%
- Median: +2.50%
- Std Dev: 0.00%
- Min: +2.50%
- Max: +2.50%


### Crab Market

**fToken Return Distribution:**
- Mean: +14.92%
- Median: +15.00%
- Std Dev: 0.79%
- Min: +13.00%
- Max: +17.00%
- Skewness: 0.09

**LST Return Distribution:**
- Mean: +2.50%
- Median: +2.50%
- Std Dev: 0.00%
- Min: +2.50%
- Max: +2.50%


### Super Cycle

**fToken Return Distribution:**
- Mean: +64.47%
- Median: +65.00%
- Std Dev: 1.42%
- Min: +60.00%
- Max: +69.00%
- Skewness: -0.16

**LST Return Distribution:**
- Mean: +2.50%
- Median: +2.50%
- Std Dev: 0.00%
- Min: +2.50%
- Max: +2.50%

