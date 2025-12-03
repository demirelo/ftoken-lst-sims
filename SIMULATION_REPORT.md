# fTOKEN vs LST Monte Carlo Simulation: Final Report

This walkthrough documents the complete Monte Carlo simulation framework comparing Liquid Staking Tokens (LSTs) and Floor-Backed Tokens (fTOKENs) across three market regimes.

## Executive Summary

**Framework**: 1,000 paths × 90 days, implemented Digital Twin with bonding curve, mint/burn mechanics, and all critical smart contract invariants.

| Metric | Crypto Winter | Crab Market | Super Cycle |
| :--- | :--- | :--- | :--- |
| **LST 95% VaR (USD)** | -60.3% | -28.0% | -40.8% |
| **fTOKEN 95% VaR (USD)** | -57.9% | -23.2% | -31.0% |
| **fTOKEN Downside Protection** | +2.4% | +4.8% | +9.8% |
| **Insolvency Prob (FPR < 1.0)** | 0.00% | 0.00% | 0.00% |
| **Prob FPR < 1.05** | 100.0% | 100.0% | 100.0% |

## Key Findings

### 1. Digital Twin & Capital Efficiency

We implemented a **Digital Twin** model with a linear bonding curve (`P = P_f + slope * S_premium`) and full mint/burn mechanics:

- **Upside Capture**: Premium supply allows fTOKENs to trade above floor. In Super Cycle, this captures significant upside (VaR -31.0% vs LST -40.8%) while maintaining 100% solvency.
- **Solvency Constraint**: The simulation confirms **Sells must be rejected** if they violate `L_f - D >= P_f * S_total`. Without this check, "capital efficiency" would drain floor reserves → 100% insolvency.
- **O(m log m) Growth**: Harmonic tier schedule (`M_i = κ * S_base / i`) enables sustainable floor elevation as `Liability ~ O(m log m)` per Appendix B.

### 2. The "Greedy Floor" Dynamic

`Prob FPR < 1.05 = 100%` across all scenarios because the logic raises the floor whenever `H >= ΔP * S_total`. This "greedy" policy:
- **Maximizes floor price** for holders by consuming all available headroom
- **Minimizes buffer**, naturally driving FPR → 1.0
- Aligns with fee-routing parameter `α_f = 1.0` (all fees to floor)

**Governance Implication**: A conservative policy (e.g., target FPR = 1.15) would result in a lower floor but higher solvency buffer and credit capacity.

### 3. Solvency is Robust Under Credit Stress & Liquidity Lag

We modeled **endogenous credit risk** (2% origination fee, loan demand) and **batched fee injection** (FloorElevationManager):

- **Liquidity Lag**: Fees accumulate in pending bucket, only injected when threshold met. Creates lag where new loans might consume headroom before fees replenish it.
- **Robustness**: System remained **100% solvent** because `fToken` enforces strict check: loans rejected if `H + ΔH < 0`, excluding pending fees.
- **Critical Insight**: If protocol counted pending fees as backing for new loans, it would face **20-40% insolvency risk** (from earlier tests). **Strict accounting is essential**.

### 4. Downside Protection: 2-10% Improvement vs LST

fTOKENs consistently outperform LSTs in downside scenarios:
- **Crypto Winter**: 2.4% better (USD VaR improvement)
- **Crab Market**: 4.8% better
- **Super Cycle**: 9.8% better

The improvement comes from:
1. Floor ratchets upward with fees/volume (non-decreasing)
2. Premium supply absorbs volatility above floor
3. Solvency checks prevent reserve depletion

### 5. Numeraire Matters: AVAX Floor ≠ USD Floor

While fTOKENs protect AVAX-denominated value, **USD VaR is dominated by AVAX beta**:
- Floor is in AVAX, not USD
- If AVAX crashes 70%, both LST and fTOKEN lose ~70% USD value
- fTOKEN improvement (2-10%) is from floor elevation in AVAX, not USD hedging

**For institutional allocators**: Floor protection is best suited for AVAX-denominated mandates or paired with external USD hedging.

## Scenario Analysis

### Crypto Winter (Bear Market, High Stress)
- AVAX: μ = -0.8 (80% annualized downtrend), σ = 0.8
- LST depeg: 1% daily probability, -5% mean shock
- Result: fTOKEN VaR -57.9% vs LST -60.3% (+2.4% protection)
- FPR remains above 1.0 despite severe drawdown and credit demand

### Crab Market (Sideways, Low Activity)
- AVAX: μ = +0.05 (slight drift), σ = 0.4
- Low volume → slow floor elevation
- Result: fTOKEN VaR -23.2% vs LST -28.0% (+4.8% protection)
- Floor growth limited by fee flow, not headroom

### Super Cycle (Bull Market, High Volatility)
- AVAX: μ = 1.2 (120% annualized uptrend), σ = 0.9
- High volume → fast floor elevation + premium expansion
- Result: fTOKEN VaR -31.0% vs LST -40.8% (+9.8% protection)
- **Best relative performance**: Premium captures upside, floor protects pullbacks

## Smart Contract Invariant Verification

All **critical solvency invariants** from `floors-sc` are correctly implemented:

### ✅ Core Invariant: `L_f - D >= P_f * S_0`
- Enforced via FPR calculation and headroom checks
- Verified across 3,000 simulated paths (1,000 per scenario)

### ✅ Sell Solvency Check
- Rejects sells if `new_reserves - debt < new_liability`
- Matches `Floor_v1.sol::sellTo` behavior

### ✅ Loan Headroom Check
- Only approves loans if `H + ΔH >= 0`
- Excludes pending fees (strict)
- Matches `Floor_v1.sol::increaseDebt` behavior

### ✅ Batched Fee Injection
- Fees → pending bucket → reserves (when threshold met)
- Matches `FloorElevationManager_v1.sol::elevateFloor`

### ✅ Harmonic Tier Scaling
- `M_i = κ * S_base / i` → `O(m log m)` total work
- Enables sustainable floor growth over many merges

**See [`invariant_comparison.md`](file:///Users/oemer.demirel/.gemini/antigravity/brain/9d03ed09-06f1-429d-8c1b-a15a54783dd0/invariant_comparison.md) for detailed comparison.**
![Crypto Winter Paths](/Users/oemer.demirel/.gemini/antigravity/brain/9d03ed09-06f1-429d-8c1b-a15a54783dd0/crypto_winter_paths.png)

### Crab Market
Low volatility, flat drift. LSTs slightly outperform due to staking yield. fTOKEN floor growth is slow due to low trading volume (fees).
![Crab Market Paths](/Users/oemer.demirel/.gemini/antigravity/brain/9d03ed09-06f1-429d-8c1b-a15a54783dd0/crab_market_paths.png)

### Super Cycle
High volatility, positive drift. High trading volumes generate significant fees, allowing the fTOKEN floor to rise rapidly, keeping pace with or slightly outperforming LST risk-adjusted metrics in the tail.
![Super Cycle Paths](/Users/oemer.demirel/.gemini/antigravity/brain/9d03ed09-06f1-429d-8c1b-a15a54783dd0/super_cycle_paths.png)

## Conclusion
The simulation validates the core "Risk Topology" thesis:
- **LSTs** are superior for pure yield and beta.
- **fTOKENs** provide structural protection in the *native* unit, but this does not translate to USD protection without external hedging.
- The **Solvency Invariant** is robust even under stress, provided the floor raising logic respects the headroom constraint.
