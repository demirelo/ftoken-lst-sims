# Structural Risk Analysis: fToken vs LST

**A Comparative Value-at-Risk Study of Floor-Backed Tokens Against Liquid Staking Tokens**

**Generated:** 2025-12-03  
**Simulation Engine:** Monte Carlo (500 paths × 180 days)  
**Framework:** Based on *Structural Solvency and Risk Topology* specification

---

## Executive Summary

This report presents a quantitative comparison between two distinct classes of crypto-native instruments:

1. **Liquid Staking Tokens (LSTs)** — Stochastic yield-bearing instruments (e.g., stETH, sAVAX) that provide efficient exposure to underlying staking yield with full participation in market beta.

2. **Floor-Backed Tokens (fTokens)** — Deterministic, structured instruments (e.g., fETH, fAVAX) that reshape the payoff profile by enforcing a non-decreasing floor price through a solvency invariant.

### The Core Trade-Off

| Dimension | LST | fToken |
|-----------|-----|--------|
| **Return Source** | Staking yield (~5% APY) | Fee accumulation (volume-dependent) |
| **Downside in ETH** | Depeg risk (2-7% in stress) | Structurally censored at floor |
| **USD Exposure** | Full underlying beta | Full underlying beta |
| **Credit Topology** | External liquidation risk | Native, non-liquidatable |
| **Best Use Case** | Maximum beta + yield | Defensive tranche, safe collateral |

### Key Simulation Results

| Scenario | fToken Return | LST Return | fToken VaR (95%) | LST Max Depeg |
|----------|---------------|------------|------------------|---------------|
| **Crypto Winter** | +1.1% | +2.5% | +1.0% | 2.7% |
| **Crab Market** | +14.9% | +2.5% | +14.0% | 0.9% |
| **Super Cycle** | +64.5% | +2.5% | +62.0% | 0.5% |

**Critical Insight**: In the reserve numeraire (ETH/AVAX), fToken floor-relative VaR is **zero by construction**. The simulation confirms 0% of paths breach the solvency invariant (FPR < 1.0).

---

## 1. Theoretical Framework

### 1.1 The Solvency Invariant

The floor price is not a policy parameter—it is a **programmatic computation** from on-chain state:

$$P_f = \left\lfloor \frac{L_f - D}{S_0} \right\rfloor_{\text{tick}}$$

Where:
- $L_f$ = Floor reserves (in ETH/AVAX)
- $D$ = Outstanding debt from credit facility  
- $S_0$ = Tier-0 (floor) supply

The solvency invariant is:

$$L_f - D \geq P_f \cdot S_0$$

**This invariant is preserved by construction** as long as:
1. Loans are issued only when headroom $H = (L_f - D) - P_f S_0 \geq \Delta D$
2. Tier merges occur only when safe-merge conditions hold
3. No bad debt is incurred (structurally impossible—see Section 4)

### 1.2 Floor Protection Ratio (FPR)

The FPR is the unified solvency metric:

$$\text{FPR} = \frac{L_f - D}{P_f \cdot S_0} = 1 + \frac{H}{P_f \cdot S_0}$$

| FPR Zone | Threshold | Interpretation |
|----------|-----------|----------------|
| **Green** | ≥ 1.10 | Healthy overcollateralization |
| **Yellow** | 1.05 – 1.10 | Caution; monitor closely |
| **Red** | < 1.05 | Circuit breakers activate |

### 1.3 LST Risk Model

For LSTs, returns decompose as:

$$R_{\text{LST}} = R_U + y + \Delta e$$

Where:
- $R_U$ = Underlying return (zero in ETH terms)
- $y$ = Staking yield (≈5% APY)
- $\Delta e$ = Depeg shock (correlated with stress)

**Depeg risk is regime-dependent**: Historical analysis shows 2-7% depegs for major LSTs during acute stress (e.g., 2022 Celsius/3AC unwind).

---

## 2. Simulation Parameters

### 2.1 Protocol Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **LTV** | 90% | Maximum borrowing against floor value |
| **α_f (Fee to Floor)** | 65% | 65% of fees → floor reserves |
| **Buy/Sell Fee** | 0.5% | Per-transaction fee |
| **Loan Origination Fee** | 2% | One-time fee, no interest |
| **LRE Threshold** | 10% premium | Triggers liquidity reallocation |
| **Coverage Buffer** | 5% | Required FPR buffer above 1.0 |
| **Tick Size** | 1% | Floor price increment granularity |
| **Tier Schedule** | Harmonic | $M_i = \kappa / i$ for O(m log m) scaling |

### 2.2 Scenario Definitions

| Scenario | μ (drift) | σ (vol) | Daily Volume | Buy/Sell Ratio | Depeg Prob |
|----------|-----------|---------|--------------|----------------|------------|
| **Crypto Winter** | -0.8 | 0.7 | 500 ETH | 45/55 | 0.5%/day |
| **Crab Market** | 0.0 | 0.5 | 1,000 ETH | 50/50 | 0.3%/day |
| **Super Cycle** | +0.8 | 0.7 | 2,500 ETH | 65/35 | 0.2%/day |

### 2.3 Volume Summary (180 days, per path)

| Scenario | Total Buys | Total Sells | Total Loans | Net Flow |
|----------|------------|-------------|-------------|----------|
| **Crypto Winter** | 40,471 ETH | 49,498 ETH | 3,610 ETH | -9,027 ETH |
| **Crab Market** | 89,966 ETH | 90,020 ETH | 14,374 ETH | -54 ETH |
| **Super Cycle** | 292,519 ETH | 157,383 ETH | 26,953 ETH | +135,136 ETH |

---

## 3. Risk Metrics Comparison

### 3.1 Return Distribution (ETH-Denominated)

*All returns are measured in the reserve numeraire (ETH/AVAX), not USD.*

| Scenario | Instrument | Mean | Std Dev | VaR (95%) | CVaR (95%) |
|----------|------------|------|---------|-----------|------------|
| **Crypto Winter** | fToken | +1.1% | 0.2% | +1.0% | +1.0% |
| | LST | +2.5% | 0.0% | +2.5% | +2.5% |
| **Crab Market** | fToken | +14.9% | 0.8% | +14.0% | +13.9% |
| | LST | +2.5% | 0.0% | +2.5% | +2.5% |
| **Super Cycle** | fToken | +64.5% | 1.4% | +62.0% | +61.7% |
| | LST | +2.5% | 0.0% | +2.5% | +2.5% |

### 3.2 Interpretation

**Crypto Winter**: LST outperforms (+2.5% vs +1.1%) because:
- Low trading volume → fewer fees → slower floor elevation
- LST staking yield continues regardless of market conditions
- However, fToken provides structural downside protection if USD exposure matters

**Crab Market**: fToken significantly outperforms (+14.9% vs +2.5%) because:
- Moderate volume generates consistent fees
- Floor elevation compounds over 180 days
- LST only earns fixed staking yield

**Super Cycle**: fToken dominates (+64.5% vs +2.5%) because:
- High volume generates substantial fees
- 65% of fees compound into floor reserves
- Tier merges accelerate floor growth

### 3.3 The Numeraire Question

A critical caveat from the structural specification:

> *"A floor denominated in AVAX or ETH protects value in units of the underlying, not in USD. For institutional allocators, USD VaR and cross-asset correlation matter."*

Both fToken and LST carry **identical USD exposure** to the underlying. In a -75% crypto winter:
- sAVAX holder: Loses ~75% in USD terms
- fAVAX holder: Loses ~75% in USD terms (but has more AVAX)

The floor protects **ETH/AVAX-denominated value**, not USD value.

---

## 4. Credit Facility Analysis

### 4.1 Why Bad Debt Is Structurally Impossible

This is the key innovation of floor-backed credit:

**Traditional Lending (LST as collateral)**:
```
Day 1:  Deposit 100 stETH ($100k) → Borrow $75k → LTV = 75%
Day 30: ETH drops 40% → stETH = $60k → LTV = 125% → LIQUIDATED
```

**fToken Native Credit**:
```
Day 1:  Lock 100 fTokens (floor = 1.0 ETH) → Collateral = 100 ETH
        Borrow 90 ETH → LTV = 90%

Day 30: Floor rises to 1.1 ETH → Collateral = 110 ETH
        Debt still = 90 ETH → LTV = 81.8% (safer!)

Day 60: Floor rises to 1.2 ETH → Collateral = 120 ETH
        Debt still = 90 ETH → LTV = 75% (even safer!)
```

**The loan is self-healing** because:
1. Collateral (fTokens) can only increase in floor value
2. Debt (ETH) is fixed with no interest
3. LTV automatically improves as floor rises

**Implications**:
- No liquidation cascades during market stress
- No procyclical selling pressure
- Credit facility is risk-free for the protocol
- 2% origination fee is pure profit

### 4.2 Credit Facility Metrics

| Scenario | Total Loans | LRE Events | Protocol Revenue |
|----------|-------------|------------|------------------|
| **Crypto Winter** | 3,610 ETH | 128.6 | 72.2 ETH (fees) |
| **Crab Market** | 14,374 ETH | 140.0 | 287.5 ETH (fees) |
| **Super Cycle** | 26,953 ETH | 173.7 | 539.1 ETH (fees) |

### 4.3 Headroom and Credit Capacity

Per the structural specification:

$$H = (L_f - D) - P_f S_0$$

Headroom emerges **after** floor elevation, not as an alternative use of funds:
1. Fees accrue → deployed to $L_f$
2. Floor rises as $(L_f - D)/S_0$ crosses tick thresholds
3. Headroom = surplus above floor obligations
4. Credit capacity per token increases

**Governance trade-off**: High credit utilization keeps $H$ near zero, potentially stalling tier merges. Conservative utilization leaves buffer for faster floor elevation.

---

## 5. Floor Elevation & Tier Mechanics

### 5.1 Elevation Results

| Scenario | Floor Growth | Tier Merges | Avg Merge/Month |
|----------|--------------|-------------|-----------------|
| **Crypto Winter** | +1.1% | 1 | 0.2 |
| **Crab Market** | +14.9% | 15 | 2.5 |
| **Super Cycle** | +64.5% | 64 | 10.7 |

### 5.2 Safe-Merge Mechanics

When floor price reaches tier boundary, absorption occurs only if:

$$L_f - D \geq P_{new} \cdot (S_0 + M_{tier})$$

This ensures solvency is never compromised by tier merges.

### 5.3 Harmonic Tier Schedule

The simulation uses harmonic-capacity tiers:

$$M_i = \frac{\kappa \cdot S_{base}}{i}$$

This achieves **O(m log m)** elevation cost vs **O(m²)** for constant-capacity tiers:

| Merges | Constant-Capacity Cost | Harmonic Cost | Ratio |
|--------|------------------------|---------------|-------|
| 10 | ~55 units | ~29 units | 1.9x |
| 50 | ~1,275 units | ~196 units | 6.5x |
| 100 | ~5,050 units | ~518 units | 9.8x |

This keeps floor elevation economically feasible over multi-year horizons.

---

## 6. Solvency Analysis

### 6.1 FPR Distribution

| Scenario | Min FPR (5th %ile) | Mean Min FPR | Final FPR (Mean) | Paths < 1.0 |
|----------|-------------------|--------------|------------------|-------------|
| **Crypto Winter** | 1.000 | 1.000 | 1.057 | 0.0% |
| **Crab Market** | 1.000 | 1.000 | 1.055 | 0.0% |
| **Super Cycle** | 1.000 | 1.000 | 1.053 | 0.0% |

### 6.2 Interpretation

**FPR never breaches 1.0** across all 1,500 simulation paths because:
1. Safe-merge conditions are enforced
2. Credit issuance is bounded by headroom
3. Bad debt is structurally impossible
4. Fee flow continuously replenishes reserves

The final FPR of ~1.05 reflects the 5% coverage buffer enforced by protocol rules.

---

## 7. LST Depeg Analysis

### 7.1 Depeg Statistics

| Scenario | Mean Events | Max Events | Probability | Max Depeg |
|----------|-------------|------------|-------------|-----------|
| **Crypto Winter** | 0.9 | 5 | 58.4% | 2.7% |
| **Crab Market** | 0.5 | 4 | 42.0% | 0.9% |
| **Super Cycle** | 0.4 | 4 | 30.8% | 0.5% |

### 7.2 Depeg Risk in Context

Per the structural specification:

> *"Depegs tend to occur during market downturns. The depeg component and the underlying return are positively correlated in the tails, which is exactly the regime where VaR matters most."*

Crypto Winter shows highest depeg risk (2.7% max) precisely when protection matters most. fTokens provide structural immunity to this risk channel.

---

## 8. Strategic Implications

### 8.1 When to Use fTokens

**Optimal for**:
- Defensive portfolio tranches
- High-quality collateral requirements
- Treasuries needing non-liquidatable leverage
- Long-term accumulation strategies (looping)
- Institutional mandates prohibiting liquidation exposure

**Key insight**: fTokens turn protocol activity into structural protection, rather than just yield.

### 8.2 When to Use LSTs

**Optimal for**:
- Maximum beta exposure
- Passive yield generation
- Short-term holding periods
- Situations where depeg risk is acceptable

### 8.3 Entry Basis Consideration

A critical point from the specification:

> *"For an actual investor, entry price relative to the floor is a distinct risk dimension... Floor-relative VaR in the reserve numeraire may be close to zero, but investor VaR around their entry basis is not."*

If entering at 10% premium:
- Floor is at 1.0 ETH, market price is 1.1 ETH
- Near-term VaR to floor = 9.1%
- Long-term: floor catches up via elevation

**Recommendation**: Dollar-cost average or enter when premium is within target band.

### 8.4 Native Looping Strategy

The structural specification highlights looping as a powerful application:

$$R_{loop} \approx k \cdot (\Delta\delta + \Delta P_f) - \int_0^T r_{borrow}(t) dt$$

Where:
- $k$ = leverage multiplier
- $\Delta\delta$ = premium change
- $\Delta P_f$ = floor elevation (the structural tailwind)

With 0% ongoing interest (only 2% origination fee), loops are more capital-efficient than LST-based leverage.

---

## 9. Governance Recommendations

### 9.1 Fee Routing Optimization

Current: α_f = 65% to floor

**Recommendation**: Dynamic fee routing based on FPR:
- FPR > 1.15: Reduce α_f to 50%, increase governance share
- FPR 1.05-1.15: Maintain α_f at 65%
- FPR < 1.05: Increase α_f to 80%, prioritize solvency

### 9.2 Credit Utilization Caps

**Recommendation**: Reserve portion of headroom for merges:
- $H_m$ = headroom reserved for next tier merge
- $H_c = H - H_m$ = available for credit
- Ensures floor elevation velocity isn't sacrificed

### 9.3 LRE Threshold Tuning

Current: 10% premium triggers LRE

The simulation shows 128-174 LRE events per path, suggesting active premium management. Consider:
- Tightening to 8% for faster floor elevation
- Or loosening to 15% to preserve premium liquidity

---

## 10. Conclusions

### 10.1 Structural Findings

1. **Floor-relative VaR is zero by construction** in the reserve numeraire, confirmed by 0% insolvency across 1,500 paths.

2. **Bad debt is structurally impossible** because collateral (fTokens) only increases in value while debt (ETH) is fixed.

3. **fToken returns are volume-dependent**: In active markets (Super Cycle), fTokens significantly outperform LSTs (+64.5% vs +2.5%). In quiet markets, LSTs win on yield.

4. **Tier design determines long-term viability**: Harmonic schedules achieve O(m log m) scaling, keeping elevation feasible.

5. **Native credit provides unique value**: Non-liquidatable leverage with self-healing LTV is unavailable in traditional DeFi.

### 10.2 Risk Summary

| Risk Factor | fToken | LST |
|-------------|--------|-----|
| Depeg in ETH terms | None (floor guarantee) | 2-7% in stress |
| USD exposure | Full underlying beta | Full underlying beta |
| Liquidation risk | None (native credit) | Yes (external lending) |
| Smart contract risk | Present | Present |
| Volume dependency | High | None |

### 10.3 Final Recommendation

**For institutional allocators**:
- Use fTokens for defensive tranches and collateral
- Use LSTs for passive yield and maximum upside
- Consider fToken + external hedge for USD floor

**For active participants**:
- Looping strategies benefit from $\Delta P_f$ tailwind
- Enter during low-premium periods
- Monitor FPR for system health

---

## Appendix: Detailed Statistics

### Crypto Winter (180 days)

**fToken Floor Growth Distribution**:
- Mean: +1.06%, Median: +1.00%, Std: 0.23%
- Min: +1.00%, Max: +2.00%
- Skewness: 3.86 (right-tailed due to floor constraint)

**LST Return Distribution**:
- Mean: +2.50%, Std: 0.00%
- Pure staking yield, no variance

### Crab Market (180 days)

**fToken Floor Growth Distribution**:
- Mean: +14.92%, Median: +15.00%, Std: 0.79%
- Min: +13.00%, Max: +17.00%
- Near-symmetric (Skew: 0.09)

### Super Cycle (180 days)

**fToken Floor Growth Distribution**:
- Mean: +64.47%, Median: +65.00%, Std: 1.42%
- Min: +60.00%, Max: +69.00%
- Slight left skew (-0.16) due to tier merge mechanics

---

## References

1. *Structural Solvency and Risk Topology: A Comparative Value-at-Risk Analysis of Floor-Backed Tokens Versus Liquid Staking Tokens* — Foundational specification document

2. Monte Carlo simulation framework implementing Appendix A methodology

3. Harmonic tier schedule per Appendix B (O(m log m) scaling)

---

*Report generated by fToken Risk Analysis Engine v1.0*
