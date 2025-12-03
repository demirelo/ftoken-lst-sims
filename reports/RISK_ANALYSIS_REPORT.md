# fToken vs LST Risk Analysis Report

**Generated:** 2025-12-03 22:19  
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
| **Coverage Buffer** | 0.1% | Required FPR buffer above 1.0 |
| **Buy/Sell Fee** | 0.5% | Transaction fees |
| **LST Yield** | 3% APY | Staking yield benchmark |

---

## Scenario Definitions & Volume

| Scenario | Description | Avg Daily Buy | Avg Daily Sell | Net Flow | Avg Daily Loans |
|----------|-------------|---------------|----------------|----------|----------------|
| **Crypto Winter** | Severe bear market with -75% drawdown | 225 ETH | 275 ETH | -50 ETH | 365 ETH |
| **Crab Market** | Sideways market with moderate volatility | 750 ETH | 750 ETH | +1 ETH | 400 ETH |
| **Super Cycle** | Strong bull market with high activity | 1,950 ETH | 1,051 ETH | +899 ETH | 677 ETH |

### Total Volume Summary (per path, 180 days)

*All values in ETH/AVAX (reserve currency)*

| Scenario | Total Buys | Total Sells | Total Loans | Net Volume |
|----------|------------|-------------|-------------|------------|
| Crypto Winter | 40,528 ETH | 49,455 ETH | 65,779 ETH | -8,927 ETH |
| Crab Market | 135,078 ETH | 134,965 ETH | 71,948 ETH | +113 ETH |
| Super Cycle | 351,021 ETH | 189,259 ETH | 121,903 ETH | +161,762 ETH |

---

## Risk Metrics Comparison

*All returns are in ETH/AVAX terms (not USD). Both instruments give underlying exposure.*

### Return Distribution

| Scenario | Instrument | Mean Return | Std Dev | VaR (95%) | CVaR (95%) | Max Depeg |
|----------|------------|-------------|---------|-----------|------------|-----------|
| Crypto Winter | **fToken** | +4.0% | 0.0% | +4.0% | +4.0% | 0% |
| | LST | +1.3% | 0.0% | +1.3% | +1.3% | 0.4% |
| Crab Market | **fToken** | +6.0% | 0.0% | +6.0% | +6.0% | 0% |
| | LST | +1.3% | 0.0% | +1.3% | +1.3% | 0.1% |
| Super Cycle | **fToken** | +27.3% | 2.2% | +24.0% | +23.3% | 0% |
| | LST | +1.3% | 0.0% | +1.3% | +1.3% | 0.0% |

---

## Floor Protection Ratio (FPR) Analysis

The FPR measures protocol solvency: FPR ≥ 1.0 means all floor redemptions can be honored.

| Scenario | Min FPR (5th %ile) | Mean Min FPR | Final FPR (Mean) | Paths FPR < 1.0 |
|----------|-------------------|--------------|------------------|-----------------|
| Crypto Winter | 1.200 | 1.200 | 2.272 | 0.0% |
| Crab Market | 1.200 | 1.200 | 2.260 | 0.0% |
| Super Cycle | 1.200 | 1.200 | 1.639 | 0.0% |

---

## Credit Facility Risk (90% LTV)

### No Liquidation, No Bad Debt

The fToken credit facility has **no liquidation mechanism**:

1. **Borrower locks fTokens** → borrows ETH at 90% LTV (of floor value)
2. **fTokens stay locked** until borrower repays debt
3. **No interest** → debt is fixed in ETH terms
4. **If borrower walks away** → fTokens remain locked, debt stays on books

**From the protocol's perspective:**
- Locked fTokens are still there (cannot be redeemed)
- Outstanding debt is still owed
- **No bad debt** because collateral isn't liquidated or written off
- Protocol simply holds the locked tokens indefinitely

**Example: Borrower Default Scenario**
```
Day 1:  Borrower locks 100 fTokens, borrows 90 ETH
        Protocol state: locked=100, debt=90 ETH

Day 30: Borrower loses 90 ETH elsewhere, can't repay
        Protocol state: locked=100, debt=90 ETH (unchanged!)
        
Forever: fTokens stay locked, debt stays on books
         FPR unaffected because locked tokens don't need floor backing
```

**Why this works:**
- Locked tokens reduce `tradeable_supply`
- Coverage invariant: `(reserves - debt) ≥ floor × tradeable`
- Locked tokens don't count toward `tradeable`, so coverage is maintained
- The protocol can wait indefinitely for repayment

### Credit Facility Metrics

| Scenario | Total Loans (ETH) | Avg Outstanding Debt | LRE Events (Mean) |
|----------|-------------------|---------------------|-------------------|
| Crypto Winter | 65,779 | N/A | 0.0 |
| Crab Market | 71,948 | N/A | 0.0 |
| Super Cycle | 121,903 | N/A | 7.9 |

---

## Floor Elevation & Tier Merges

| Scenario | Mean Floor Growth | Floor Growth (5th %ile) | Mean Tier Merges |
|----------|-------------------|-------------------------|------------------|
| Crypto Winter | +4.0% | +4.0% | 1 |
| Crab Market | +6.0% | +6.0% | 4 |
| Super Cycle | +27.3% | +24.0% | 26 |

### How Floor Growth Works

**Fee-driven floor elevation:**
1. Trading fees (0.5%) + loan origination fees (2%) accumulate
2. 65% of fees → floor reserves
3. When threshold met → floor price is elevated

**Headroom (for borrowers):**
When floor rises, locked collateral is worth more:
```
Before: 100 locked tokens × 1.0 floor = 100 ETH collateral
        Debt = 90 ETH → LTV = 90%
        
After floor rises to 1.10:
        100 locked tokens × 1.1 floor = 110 ETH collateral  
        Debt = 90 ETH → LTV = 81.8%
        
Headroom = (110 × 90%) - 90 = 9 ETH (can top-up)
```

**Virtuous cycle:**
- Fees → floor elevation → headroom created
- Borrowers top-up (pay 2% origination fee)
- More fees → more elevation → more headroom → repeat

**Loan Activity Model:**
- ~85% of floor supply locked as collateral (limited by debt cap)
- Borrowers top-up when floor rises (borrow the headroom)
- This generates continuous fee revenue

**Floor Growth Formula:**
```
floor_growth = total_fees_to_floor / avg_tradeable_supply
```

**Example (Crab Market):**
- Trading fees: 270,000 ETH × 0.5% × 65% = 878 ETH
- Loan fees: 60,000 ETH × 2% × 65% = 780 ETH  
- Total fees to floor: ~1,658 ETH
- Avg tradeable: ~25,000 (declines due to sells/merges)
- Floor growth: 1,658 / 25,000 ≈ 6.6%

---

## Premium Token Mechanics

### Coverage Invariant

All tokens (floor AND premium) require floor backing:
```
required = floor_price × tradeable_supply
```

Where `tradeable = total_supply - locked_supply` includes BOTH floor and premium tokens.

### Premium Buys Create Headroom

When buying at premium price (above floor):
```
Buy 1000 ETH at 1.05 ETH/token:
  → Mint ~950 tokens (after fees)
  → Reserves += 1000 ETH
  → Required += 950 ETH (tokens × floor_price)
  → Headroom created = 1000 - 950 = 50 ETH (the premium!)
```

Only the **premium portion** (price - floor) creates headroom, not the full amount.

### Locking Premium Tokens

When you lock a premium token as collateral:
- **Collateral value** = floor_price (not market price)
- **Borrowable** = floor_price × LTV

Example: Mint at 1.05 ETH, lock, borrow at 90% LTV:
```
Floor value: 1.0 ETH
Borrowable: 0.9 ETH (90% of floor, not market)
Premium (0.05 ETH): Acts as "equity" above floor
```

### Floor Supply Recalibration

When sells reduce `total_supply` below `floor_supply`:
1. `floor_supply` shrinks to match `total_supply`
2. Next buy enters the **premium tier** (above floor price)
3. This enables **faster floor growth** (premium headroom)

```
Before sell: total=100k, floor=100k, premium=0
After sell:  total=80k,  floor=80k,  premium=0  (recalibrated)
After buy:   total=81k,  floor=80k,  premium=1k (premium tier!)
```

---

## LST Depeg Risk

| Scenario | Mean Depeg Events | Max Depeg Events | Depeg Probability |
|----------|-------------------|------------------|-------------------|
| Crypto Winter | 1.4 | 6 | 76.6% |
| Crab Market | 0.4 | 3 | 29.4% |
| Super Cycle | 0.1 | 3 | 9.2% |

---

## Key Findings

### 1. Fee-Driven Floor Growth with Loan Top-ups

The simulation models realistic floor token holder behavior:
- **85% of floor supply locked** as loan collateral
- Initial borrowing at **90% LTV** against floor value
- **Top-up** when floor rises (borrow the newly created headroom)

**The virtuous cycle:**
```
1. Fees accumulate (trading + loan origination)
2. 65% of fees → floor reserves → floor elevation
3. Floor rises → locked collateral worth more
4. Borrowers can top-up (borrow headroom at 2% fee)
5. More fees → repeat
```

**Headroom example (floor rises 10%):**
```
Before: 100 tokens × 1.0 floor = 100 ETH collateral, 90 ETH debt (90% LTV)
After:  100 tokens × 1.1 floor = 110 ETH collateral, 90 ETH debt (82% LTV)
Headroom = (110 × 90%) - 90 = 9 ETH available to borrow
```

**Key insight:** Floor growth is driven by fees ÷ tradeable supply. As tradeable supply decreases (from sells and tier merges), the same fee amount produces larger floor growth.

### 2. Downside Protection (in ETH terms)
- **fToken floor guarantee** provides deterministic protection: floor price only increases
- **LST** earns staking yield but faces depeg risk up to 0.1% below fair value

### 3. Risk-Adjusted Returns (in ETH terms)
- **fToken** returns depend on **both** fee volume **and** loan activity
- **LST** returns come from staking yield (~2.6% APY), reduced by depeg events
- Both instruments carry underlying (ETH/AVAX) USD price risk equally

### 4. Protocol Solvency
- FPR maintained above 1.20 across all scenarios (5th percentile)
- Safe-merge mechanism successfully absorbs premium tiers into floor

### 5. Credit Facility (90% LTV)
- **No liquidation, no bad debt**: Locked fTokens stay locked; debt stays on books until repaid
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

**Value-at-Risk (VaR) at 95%:**
- The 5th percentile of the return distribution
- Interpretation: "With 95% confidence, returns will be at least this value"
- Calculation: Sort all path returns, take the value at the 5th percentile
- Example: VaR(95%) = +4.0% means 95% of paths had returns ≥ +4.0%

**Conditional Value-at-Risk (CVaR) at 95%:**
- Also called "Expected Shortfall"
- The average return of the worst 5% of outcomes
- Captures tail risk better than VaR (what happens in the bad cases)
- Calculation: Average of all returns below the VaR threshold
- Example: CVaR(95%) = +3.5% means when things go bad, average return is +3.5%

**Floor Protection Ratio (FPR):**
- FPR = (Reserves - Debt) / (Floor Price × Tradeable Supply)
- FPR ≥ 1.0 means all floor redemptions can be honored
- Buffer of 0.1% ensures minimal safety margin

**Note on fToken Standard Deviation:**
- fToken returns have low std dev because floor growth is deterministic
- Floor growth = fees / tradeable_supply (driven by trading volume)
- Variation comes from random trading volumes, not price volatility
- This is a feature: predictable floor growth is the value proposition

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
- Mean: +4.00%
- Median: +4.00%
- Std Dev: 0.00%
- Min: +4.00%
- Max: +4.00%
- Skewness: 1.00

**LST Return Distribution:**
- Mean: +1.29%
- Median: +1.29%
- Std Dev: 0.00%
- Min: +1.29%
- Max: +1.29%


### Crab Market

**fToken Return Distribution:**
- Mean: +6.00%
- Median: +6.00%
- Std Dev: 0.00%
- Min: +6.00%
- Max: +6.00%
- Skewness: nan

**LST Return Distribution:**
- Mean: +1.29%
- Median: +1.29%
- Std Dev: 0.00%
- Min: +1.29%
- Max: +1.29%


### Super Cycle

**fToken Return Distribution:**
- Mean: +27.28%
- Median: +27.00%
- Std Dev: 2.21%
- Min: +20.00%
- Max: +33.00%
- Skewness: -0.06

**LST Return Distribution:**
- Mean: +1.29%
- Median: +1.29%
- Std Dev: 0.00%
- Min: +1.29%
- Max: +1.29%

