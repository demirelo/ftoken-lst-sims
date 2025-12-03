# Fee Routing Sensitivity Analysis Results

## Executive Summary

**Test Date**: 2025-12-03
**Objective**: Evaluate impact of fee-to-floor ratio (alpha_f) on system performance and LRE activation

**Scenario**: Super Cycle (70% annualized growth, 70% volatility, 90 days, 300 paths)

## Configuration

| Parameter | Value |
|-----------|-------|
| **alpha_f Range** | 40% - 90% |
| **Market Regime** | Super Cycle (strong bull) |
| **Volume** | 100k daily mean (baseline) |
| **LRE Threshold** | 2.0x |
| **Debt Cap** | 50% |

## Results Summary

| Metric | alpha_f = 40% | alpha_f = 65% | alpha_f = 90% |
|--------|---------------|---------------|---------------|
| **fToken Mean Return** | +47.8% | +52.2% | +53.4% |
| **fToken VaR (95%)** | -18.1% | -23.7% | -29.5% |
| **Floor Growth** | +24.4% | +26.1% | +29.0% |
| **LRE Events** | 0.0 | 0.0 | 0.0 |
| **Min FPR (5th pctl)** | 1.050 | 1.050 | 1.050 |

## Key Findings

### 1. Higher alpha_f → Higher Returns **BUT** Higher Risk

**Trend**: As more fees go to floor backing (90% vs 40%):
- **Mean returns increase**: +47.8% → +53.4% (+5.6pp improvement)
- **Floor growth increases**: +24.4% → +29.0% (+4.6pp)
- **VaR WORSENS**: -18.1% → -29.5% (+11.4pp tail risk)

**Explanation**:
- More fees → faster floor elevation → higher mean returns
- But governance buffer reduced → less cushion in downside scenarios
- Trade-off between return maximization and risk management

### 2. LRE Still Did Not Activate

**Result**: 0 LRE events across all alpha_f values

**Why**:
Even with 40% fee-to-floor (60% to governance/buffer), LRE didn't trigger because:
1. **Greedy floor policy** still consumes available headroom for merges
2. **Credit facility** competes for premium liquidity  
3. **LRE threshold = 2.0x** requires very high premium/floor ratio
4. **Volume insufficient** to build substantial premium tier

### 3. Optimal Balance: alpha_f ≈ 65-70%

**Rationale**:
- **65%** provides balanced performance:
  - Strong returns (+52.2%)
  - Manageable VaR (-23.7%)
  - Good floor growth (+26.1%)
  - Governance receives meaningful revenue (35%)

- **40%** is too conservative:
  - Lower returns (+47.8%)
  - Excessive governance allocation (60%)
  - Floor growth limited

- **90%** is too aggressive:
  - Highest tail risk (-29.5% VaR)
  - Minimal governance revenue (10%)
  - Marginal return improvement over 65%

## Recommendations

### For Production Deployment

1. **Recommended alpha_f: 65-70%**
   - Balances return optimization with governance sustainability
   - Provides safety margin without excessive conservatism

2. **For LRE Activation**
   
   Current approach (fee routing alone) is insufficient. For active LRE, protocols should:
   
   **Option A: Lower LRE Threshold**
   - Reduce from 2.0x to 1.3-1.5x
   - More sensitive to premium accumulation
   - Tested in LTV scenarios (still no activation)
   
   **Option B: Higher Volumes**
   - Would need 4-5x baseline volume (400-500k daily)
   - Generates sufficient premium tier depth
   - Tested in LTV99 scenario (still no activation)
   
   **Option C: Modify Floor Elevation Policy** ⭐ **RECOMMENDED**
   - Implement "LRE-first" policy:
     ```
     if can_perform_lre():
         perform_lre()
     elif headroom > elevation_threshold:
         raise_floor()
     ```
   - Prioritize LRE over greedy floor raises
   - Allows premium to accumulate before being merged
   
   **Option D: Separate Fee Streams**
   - Route buy/sell fees → floor (alpha_f = 70%)
   - Route loan origination fees → premium buffer (100%)
   - Creates dedicated premium accumulation source

3. **Dynamic alpha_f Based on FPR**
   ```
   if FPR > 1.15:    # Green zone, healthy
       alpha_f = 0.80  # Aggressive floor growth
   elif FPR > 1.10:  # Yellow zone
       alpha_f = 0.70  # Balanced
   elif FPR > 1.05:  # Orange zone
       alpha_f = 0.60  # Conservative
   else:             # Red zone
       alpha_f = 0.50  # Maximum safety
   ```

### For Governance Revenue

| alpha_f | Floor Allocation | Governance Revenue |
|---------|------------------|-------------------|
| 40% | 40% | **60%** (max revenue) |
| 65% | 65% | **35%** (balanced) |
| 90% | 90% | **10%** (minimal) |

**Trade-off**: Governance revenue vs protocol growth rate

- **High governance revenue** (40-50% alpha_f):
  - Sustainable protocol operations
  - Treasury building
  - Development funding
  - **BUT**: Slower floor growth, lower user returns

- **High floor allocation** (80-90% alpha_f):
  - Maximum user value capture
  - Rapid floor elevation
  - Competitive positioning
  - **BUT**: Governance underfunded, tail risk exposure

## Visualization

See [`fee_routing_sensitivity.png`](./fee_routing_sensitivity.png) for graphical comparison across alpha_f values.

## Conclusion

**Fee routing alone does not enable LRE activation** under current model assumptions (greedy floor policy, standard volumes).

**Recommended approach**:
1. Set **alpha_f = 65-70%** for production
2. Implement **LRE-first policy** to prioritize reallocation over merges
3. Consider **dynamic alpha_f** based on FPR zones
4. Test with **10x higher volumes** if targeting frequent LRE

The simulation confirms that **fee routing is primarily a governance/user value split mechanism**, not an LRE activation lever.
