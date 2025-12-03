# fToken vs LST Risk Analysis Report

**Generated:** 2025-12-03 16:07  
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
| **Buy/Sell Fee** | 2% | Transaction fees |
| **LST Yield** | 5% APY | Staking yield benchmark |

---

## Scenario Definitions & Volume

| Scenario | Description | Avg Daily Buy | Avg Daily Sell | Net Flow | Avg Daily Loans |
|----------|-------------|---------------|----------------|----------|----------------|
| **Crypto Winter** | Severe bear market with -75% drawdown | 225 ETH | 275 ETH | -50 ETH | 20 ETH |
| **Crab Market** | Sideways market with moderate volatility | 500 ETH | 500 ETH | -0 ETH | 80 ETH |
| **Super Cycle** | Strong bull market with high activity | 1,626 ETH | 875 ETH | +751 ETH | 150 ETH |

### Total Volume Summary (per path, 180 days)

*All values in ETH/AVAX (reserve currency)*

| Scenario | Total Buys | Total Sells | Total Loans | Net Volume |
|----------|------------|-------------|-------------|------------|
| Crypto Winter | 40,544 ETH | 49,459 ETH | 3,618 ETH | -8,915 ETH |
| Crab Market | 90,038 ETH | 90,055 ETH | 14,397 ETH | -16 ETH |
| Super Cycle | 292,601 ETH | 157,419 ETH | 27,006 ETH | +135,182 ETH |

---

## Risk Metrics Comparison

### Return Distribution

| Scenario | Instrument | Mean Return | Std Dev | VaR (95%) | CVaR (95%) | Max DD |
|----------|------------|-------------|---------|-----------|------------|--------|
| Crypto Winter | **fToken** | +7.2% | 0.4% | +7.0% | +7.0% | 0% (floor) |
| | LST | -32.4% | 33.7% | -73.0% | -78.2% | 54.5% |
| Crab Market | **fToken** | +32.1% | 2.3% | +29.0% | +28.7% | 0% (floor) |
| | LST | +1.0% | 36.6% | -46.6% | -54.6% | 34.0% |
| Super Cycle | **fToken** | +74.5% | 1.4% | +72.0% | +71.8% | 0% (floor) |
| | LST | +54.9% | 77.7% | -41.0% | -54.3% | 35.7% |

---

## Floor Protection Ratio (FPR) Analysis

The FPR measures protocol solvency: FPR ≥ 1.0 means all floor redemptions can be honored.

| Scenario | Min FPR (5th %ile) | Mean Min FPR | Final FPR (Mean) | Paths FPR < 1.0 |
|----------|-------------------|--------------|------------------|-----------------|
| Crypto Winter | 1.000 | 1.000 | 1.055 | 0.0% |
| Crab Market | 1.000 | 1.000 | 1.054 | 0.0% |
| Super Cycle | 1.001 | 1.002 | 1.053 | 0.0% |

---

## Credit Facility Risk (90% LTV)

### How Bad Debt Events Occur While Invariants Hold

The **solvency invariant** `L_f - D ≥ P_f × S_tradeable` ensures that floor redemptions can always be honored. However, **bad debt events** can still occur through the following mechanism:

1. **Loan Origination**: Borrower locks fTokens as collateral and borrows ETH/AVAX
   - At 90% LTV: 100 fTokens (worth 100 ETH at floor) → 90 ETH loan
   
2. **Price Movement**: Floor price rises (due to fee accumulation)
   - Collateral value increases, loan remains safe
   
3. **Loan Default Scenario**: Borrower defaults when collateral < debt
   - This happens if borrower's external position fails or they simply walk away
   - At 90% LTV, only a 10% move against the position causes underwater
   
4. **Bad Debt Absorption**:
   - Collateral is liquidated at floor price
   - Shortfall (bad debt) is absorbed by reserves: `L_f -= bad_debt_amount`
   - Debt is written off: `D -= loan_amount`
   - Net effect: `L_f - D` decreases by LGD × loan_amount
   
5. **Invariant Still Holds If**:
   - Buffer was sufficient: `(L_f - D) > P_f × S_tradeable × (1 + buffer)`
   - After bad debt: `(L_f - bad_debt - D + loan) ≥ P_f × S_tradeable`
   - The 5% coverage buffer absorbs small bad debt events

**Key Insight**: Bad debt reduces the buffer but doesn't immediately break solvency. Multiple bad debt events or large defaults can eventually breach the invariant.

| Scenario | Bad Debt Events (Mean) | Bad Debt Prob | LRE Events (Mean) |
|----------|------------------------|---------------|-------------------|
| Crypto Winter | 1.18 | 70.2% | 73.8 |
| Crab Market | 2.22 | 89.6% | 62.8 |
| Super Cycle | 2.93 | 94.6% | 173.7 |

---

## Floor Elevation & Tier Merges

| Scenario | Mean Floor Growth | Floor Growth (5th %ile) | Mean Tier Merges |
|----------|-------------------|-------------------------|------------------|
| Crypto Winter | +7.2% | +7.0% | 7 |
| Crab Market | +32.1% | +29.0% | 32 |
| Super Cycle | +74.5% | +72.0% | 75 |

---

## LST Depeg Risk

| Scenario | Mean Depeg Events | Max Depeg Events | Depeg Probability |
|----------|-------------------|------------------|-------------------|
| Crypto Winter | 57.0 | 75 | 100.0% |
| Crab Market | 39.9 | 60 | 100.0% |
| Super Cycle | 49.3 | 68 | 100.0% |

---

## Key Findings

### 1. Downside Protection
- **fToken floor guarantee** provides deterministic downside protection (0% max drawdown from floor)
- **LST** exposed to market volatility with drawdowns up to 41.4% average

### 2. Risk-Adjusted Returns
- In **Crypto Winter**, fToken preserves capital while LST suffers significant losses
- In **Bull Markets**, LST captures more upside, but fToken floor still grows via fees

### 3. Protocol Solvency
- FPR maintained above 1.00 across all scenarios (5th percentile)
- Safe-merge mechanism successfully absorbs premium tiers into floor

### 4. Credit Facility (90% LTV)
- Higher LTV increases bad debt risk in volatile scenarios
- LRE mechanism actively manages premium liquidity

---

## Methodology

### Simulation Framework
- **Price Model:** Geometric Brownian Motion with scenario-specific drift (μ) and volatility (σ)
- **LST Depeg:** Poisson-distributed depeg events with scenario-specific probability
- **Fee Model:** 2% buy fee, 2% sell fee, 65% to floor
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
- Mean: +7.15%
- Median: +7.00%
- Std Dev: 0.40%
- Min: +6.00%
- Max: +8.00%
- Skewness: 1.23

**LST Return Distribution:**
- Mean: -32.42%
- Median: -38.02%
- Std Dev: 33.67%
- Min: -86.96%
- Max: +158.27%


### Crab Market

**fToken Return Distribution:**
- Mean: +32.08%
- Median: +32.00%
- Std Dev: 2.34%
- Min: +26.00%
- Max: +43.00%
- Skewness: 0.74

**LST Return Distribution:**
- Mean: +1.03%
- Median: -5.34%
- Std Dev: 36.60%
- Min: -66.53%
- Max: +150.86%


### Super Cycle

**fToken Return Distribution:**
- Mean: +74.52%
- Median: +75.00%
- Std Dev: 1.35%
- Min: +70.00%
- Max: +78.00%
- Skewness: -0.11

**LST Return Distribution:**
- Mean: +54.87%
- Median: +41.73%
- Std Dev: 77.69%
- Min: -82.69%
- Max: +447.19%

