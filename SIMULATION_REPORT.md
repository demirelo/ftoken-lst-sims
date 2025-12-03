# fTOKEN vs LST Monte Carlo Simulation: Comprehensive Report

## Executive Summary

**Framework**: Python twin of Floor_v1.sol running 1,000 paths × 90 days across 3 market regimes

### Key Results

| Metric | Crypto Winter | Crab Market | Super Cycle |
|:-------|:--------------|:------------|:------------|
| **LST 95% VaR** | -60.2% | -26.6% | -35.0% |
| **fTOKEN USD 95% VaR** | -57.9% | -22.9% | -20.2% |
| **LST Mean Return** | -15.8% | +3.9% | +20.3% |
| **fTOKEN Mean Return** | -10.4% | +9.3% | +54.9% |
| **Insolvency (FPR < 1.0)** | 0.0% | 0.0% | 0.0% |
| **Red Zone (FPR < 1.05)** | 3.3% | 0.9% | 3.5% |
| **Floor Growth** | +7.5% | +6.5% | +29.4% |

## Implementation Fidelity

This simulation is a **Python twin of Floor_v1.sol**, implementing:

### Core Invariants ✅
- `L_f - D >= P_f * S_tradeable` (coverage invariant)
- FPR = `(L_f - D) / (P_f * S_tradeable)`
- Headroom with governance buffers

### Solidity-Mirrored Mechanics ✅
- Tradeable vs locked supply tracking
- Debt caps (`debt_cap_bps`)
- Coverage buffers (`min_coverage_buffer_bps`)
- Segment-based bonding curve
- Safe-merge tier logic
- Curve recalibration after redemptions

### Advanced Features ✅
- **LRE (Liquidity Reallocation Elevation)**: Mirrors `FloorElevationManager_v1.sol`
- **Bad debt modeling**: Per Section 9.2, `L_f → L_f - ΔD, D → D - ΔD`
- **Stress-correlated depegs**: LST depeg probability scales 3x during drawdowns
- **Batched fee injection**: Elevation threshold mechanism
- **Harmonic tier schedule**: O(m log m) elevation cost

## Findings

### 1. Zero Insolvency Under All Stress Scenarios

**Result**: 0.00% insolvency probability across 3,000 simulated paths

**Why it works**:
- Strict coverage checks before loans and sells
- Coverage buffer (`5%` extra) provides safety margin
- Bad debt directly reduces both `L_f` and `D`, maintaining ratio
- Floor only raises when headroom exists

### 2. fTOKEN Outperforms in Bull Markets

**Super Cycle Results**:
- fTOKEN: **+54.9% mean return** vs LST +20.3%
- fTOKEN: **-20.2% VaR** vs LST -35.0%
- Floor grew **+29.4%** in AVAX terms

**Mechanism**: High trading volume → fee accumulation → rapid floor elevation → compounding floor growth captures underlying upside while maintaining protection.

### 3. Downside Protection is Modest but Consistent

**Crypto Winter**:
- fTOKEN VaR: -57.9% vs LST -60.2% (**+2.3% protection**)
- Floor grew +7.5% in AVAX despite severe underlying decline
- Mean return: -10.4% vs LST -15.8% (**+5.4% improvement**)

**Key Insight**: Floor is AVAX-denominated, so USD VaR is dominated by underlying beta. Protection is meaningful but not a USD hedge.

### 4. Bad Debt is Manageable

- **Crypto Winter**: 100% of paths had bad debt (mean: 1,423 AVAX, <0.13% of reserves)
- **Super Cycle**: 85% of paths had bad debt (mean: 1,574 AVAX)
- **Impact**: Minimal FPR degradation due to simultaneous `L_f` and `D` reduction

**Verification**: Per spec Section 9.2, write-offs correctly reduce both assets and liabilities proportionally.

### 5. Greedy Floor Policy → FPR Near Threshold

**Observed**: Final FPR mean ranges 1.057-1.080 across scenarios

**Why**: Simulation implements "greedy" floor elevation that consumes all available headroom, mirroring realistic protocol behavior that maximizes floor price for holders.

**Governance Implication**: Real deployments should set `min_coverage_buffer_bps` conservatively (e.g., 10-15%) for additional safety margin.

### 6. LRE Did Not Trigger

**Observed**: 0.0 mean LRE events across all scenarios

**Why**: LRE threshold set to 2.0 (premium/floor ratio) was not reached. Current volume and fee parameters don't generate sufficient premium tier depth.

**Future Tuning**: Lower threshold (e.g., 1.5) or higher volume scenarios would activate LRE more frequently.

## Stress Test Results

### LST Depeg Correlation

**Crypto Winter**:
- Mean depeg events: **1.8 per path** (elevated due to stress)
- Depeg probability: 1% base × 3x multiplier during >3% drawdowns
- Worst-case depegs: ~-15% discount to theoretical value

**Validation**: Matches spec guidance (Section 5.1) for stressed LST behavior.

### Credit Facility Performance

**High Bad Debt Scenario** (Crypto Winter):
- 100% of paths experienced loan defaults
- Max bad debt: 2,893 AVAX (0.26% of initial reserves)
- System remained solvent in all cases

**Mechanism**: Defaults reduce both `L_f` (write-off) and `D` (extinguished principal), maintaining coverage ratio.

## Scenario Deep Dives

### Crypto Winter

**Setup**: μ=-0.8, σ=0.8, 1% daily depeg prob
**Result**: Floor protection outweighs fee drag
- fTOKEN mean -10.4% vs LST -15.8%
- Floor **grew +7.5%** in AVAX despite crisis
- FPR stayed above 1.05 in 96.7% of path-time

**Insight**: In prolonged drawdowns, fTOKEN's ratcheting floor provides measurable value preservation.

### Crab Market

**Setup**: μ=0.05, σ=0.4, minimal depegs
**Result**: LST yield vs fTOKEN fees balanced
- fTOKEN mean +9.3% vs LST +3.9%
- Modest floor growth (+6.5%)
- Best FPR maintenance (99.1% of paths never hit red zone)

**Insight**: Low volatility favors fTOKEN due to stable fee collection without stress-induced losses.

### Super Cycle

**Setup**: μ=0.7, σ=0.7, high volume
**Result**: fTOKEN massively outperforms
- fTOKEN mean **+54.9%** vs LST +20.3%
- Floor grew **+29.4%**
- Superior VaR (-20.2% vs -35.0%)

**Insight**: High volume → rapid fee accumulation → explosive floor growth. fTOKEN captures upside while building protection.

## Technical Validation

### Invariant Verification

All paths across all scenarios maintained:
1. ✅ `L_f - D >= P_f * S_tradeable` (0% violations)
2. ✅ Floor monotonicity (never decreased)
3. ✅ Locked + tradeable = total supply
4. ✅ Debt <= debt_cap

### Comparison with Solidity

See [`INVARIANT_VERIFICATION.md`](./INVARIANT_VERIFICATION.md) for detailed mapping:
- ✅ `_calculateAvailableFloorAssets()` → `get_available_floor_assets()`
- ✅ `_getTradeableSupply()` → `get_tradeable_supply()`
- ✅ `getCoverageRatio()` → `calculate_fpr()`
- ✅ `increaseDebt()` → `originate_loan()`
- ✅ `sellTo()` coverage check → `sell()` coverage check

## Recommendations

### For Protocol Design

1. **Set conservative coverage buffers**: 10-15% recommended vs 5% tested
2. **Monitor FPR zones**: Implement automated alerts at 1.10 (yellow) and 1.05 (red)
3. **LRE activation**: Consider threshold = 1.5 for more frequent elevation events
4. **Debt cap governance**: 50% cap tested; consider 30-40% for added safety

### For Risk Management

1. **Use relative VaR**: fTOKEN provides 2-15% downside improvement vs LST
2. **Expect bad debt**: Model 0.1-0.3% reserves as potential credit losses
3. **AVAX-denominated mandates**: fTOKEN is ideal for AVAX portfolios, not USD hedging
4. **Monitor depeg correlation**: LST depegs concentrate during market stress

### For Users

1. **Bullish markets**: fTOKEN dramatically outperforms (+54.9% vs +20.3% in Super Cycle)
2. **Risk-averse profiles**: fTOKEN floor provides safety with minimal yield drag
3. **Collateral use**: Excellent for non-liquidatable leverage (FPR > 1.0 guaranteed)

## Conclusion

The enhanced simulation demonstrates that **fTOKENs maintain 100% solvency** while providing:
- **2-15% downside protection** vs LSTs
- **Explosive upside** in bull markets (+54.9% in Super Cycle)
- **Robust credit facility** with manageable bad debt
- **Strict Solidity-mirrored mechanics** for deployment confidence

The **Python twin implementation** validates all core invariants from `Floor_v1.sol` and confirms the structural solvency guarantees outlined in the research paper.

---

**Full Results**: See [`crypto_winter_results.png`](./crypto_winter_results.png), [`crab_market_results.png`](./crab_market_results.png), [`super_cycle_results.png`](./super_cycle_results.png)

**Implementation Details**: See [`invariant_comparison.md`](./invariant_comparison.md)

**Codebase**: [github.com/demirelo/ftoken-lst-sims](https://github.com/demirelo/ftoken-lst-sims)
