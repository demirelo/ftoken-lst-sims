# The Rising Floor: Allocator Note

## A Comparative Risk Analysis of Floor-Backed Tokens vs Liquid Staking Tokens

---

## Allocator Summary

*This summary is intended for institutional allocators, treasury managers, and risk committees. The full technical analysis follows in the Technical Appendix.*

### What Are fTokens?

Floor-backed tokens (fTokens) are crypto-native instruments that reshape the payoff profile of an underlying asset (ETH, AVAX, etc.) by enforcing a **non-decreasing floor price** through protocol mechanics. Unlike Liquid Staking Tokens (LSTs) which simply wrap staking yield, fTokens convert trading activity into structural downside protection.

### The Core Trade-Off

| Dimension | LST (e.g., stETH, sAVAX) | fToken (e.g., fETH, fAVAX) |
|-----------|--------------------------|----------------------------|
| Return source | Staking yield (2.6% APY) | Fee accumulation (trading + loans) |
| Downside in underlying | Depeg risk (severe in stress) | Structurally censored at floor |
| USD exposure | Full underlying beta | Full underlying beta |
| Leverage topology | External lending → liquidation risk | Native credit → no liquidations |
| Best use case | Maximum beta + passive yield | Defensive tranche, safe collateral |

### Key Simulation Results (365 days, Agent-Based Model)

*Simulation uses 2,000 heterogeneous agents across 500 paths per scenario.*

**USD-Denominated Returns (1 Year):**

| Market Regime | fToken USD | LST USD | fToken Floor (ETH) | Winner |
|---------------|------------|---------|--------------------| -------|
| Super Cycle (+70% drift) | **+77.0%** | +74.4% | +4.1% | fToken |
| Crab Market (+5% drift) | **+8.2%** | +7.7% | +3.0% | fToken |
| Crypto Winter (-80% drift) | **-79.0%** | -79.5% | +5.0% | fToken |

**Under the parameter regime studied here, fTokens outperform LSTs in all three market scenarios.** This result is contingent on: (1) trading volume generating 3-5% annual floor growth, (2) LST yield at 2.6% APY, and (3) 70% of fees routed to floor. Different parameter choices can change the outcome.

**The Counter-Cyclical Floor (Key Insight):** Floor growth is **highest in Crypto Winter (+5.0%)** because panic selling generates more trading volume, which generates more fees, which elevates the floor faster. The USD edge in a one-year bear regime is only about 0.5 percentage points, but the left-tail shape is very different: no depeg channel and improving LTV instead of liquidation cascades.

**Solvency validation:** Across all simulation paths, 0% breached FPR < 1.0. Minimum FPR was 1.113 even in -80% drawdown scenarios.

### Risk-Adjusted Performance

| Metric | fToken | LST | Winner |
|--------|--------|-----|--------|
| Sharpe Ratio | Higher | Lower | fToken |
| Max Drawdown | Limited by floor | Unlimited | fToken |
| VaR (95%) | Better | Worse | fToken |
| Tail Risk | Bounded | Unbounded (depeg) | fToken |
| Simulated Depeg Events (Crypto Winter) | 0 | 7.6 avg | fToken |

*Note: The 7.6 depeg events and associated impact are outputs of the agent-based stress model, not historical measurements. Historically, top-tier LSTs like stETH have seen 2-7% discounts in acute stress; the model uses deliberately conservative stress assumptions.*

### What Treasuries Care About

**1. Numeraire clarity**
- In USD terms, fToken and LST have **identical beta to the underlying** (ETH/AVAX)
- The edge is in: floor-relative risk, risk-adjusted return *for the same underlying exposure*, and elimination of depeg/liquidation modes
- If your mandate is "no underlying beta," neither LSTs nor fTokens solve that—you need a hedge

**2. Counter-cyclical floor growth**
- Floor grows 3-5% annually in ETH terms across all simulated regimes
- Growth is **highest in bear markets** due to panic selling volume
- This is the opposite of LST depeg risk, which is highest in stress

**3. Can we borrow without liquidation risk?**
- fToken native credit: Yes, under specific design constraints (see Design Envelope below)
- Collateral (fTokens) only appreciates; debt (ETH/AVAX) is fixed
- LTV automatically improves over time as floor rises

**4. What can still go wrong?**
- Smart contract risk (both instruments)
- Volume insufficient to generate floor growth exceeding LST yield
- USD value still tracks underlying (floor is in ETH/AVAX, not USD)
- Entry at high premium creates mark-to-market risk until floor catches up

### Design Envelope: When "No Liquidation, No Bad Debt" Holds

The "no liquidation, no bad debt" result holds only under strict design constraints:
1. **Collateral type:** fTokens only (floor value as collateral basis)
2. **Loan denomination:** Reserve asset only (ETH/AVAX)
3. **Reserve rehypothecation:** Zero, or only into instruments with negligible loss probability
4. **No senior external liabilities**

### Recommendations

**For allocators seeking risk-adjusted performance:** Consider fTokens
- Superior risk-adjusted returns in simulated regimes
- Counter-cyclical floor growth provides natural hedge
- Non-liquidatable leverage (under design envelope)

**For allocators prioritizing simplicity:** Consider LSTs
- No dependency on protocol trading volume
- Simpler exposure profile
- Acceptable when willing to accept potential 0.5-2.5% annual return gap

**For USD floor protection:** Consider fToken + external hedge (futures/options on underlying)

---

## 1. Executive Abstract

The maturation of Decentralized Finance (DeFi) has created a split in asset design between:

1. **Stochastic yield-bearing instruments**, represented by Liquid Staking Tokens (LSTs).
2. **Deterministic, structured instruments**, represented by floor-backed tokens (fTokens).

This report develops a first-principles risk framework comparing these two classes, focusing on Value-at-Risk (VaR), solvency mechanics, and the practical behavior of floor-backed protection under stress. The theoretical framework is validated by agent-based Monte Carlo simulation (2,000 agents, 365 days across three market regimes).

We discuss Tier-0 mechanics for fTokens. Under this specification, the floor is not a passive redemption facility but a live trading tier that must be fully backed at all times, independent of lock states. This reframes the floor as an internal full-reserve micro-economy and makes solvency and governance questions precise.

On the LST side, instruments such as stETH and sAVAX provide efficient exposure to underlying staking yield with full participation in market beta. Their core risks are:

- Market beta of the underlying asset.
- Liquidity-driven depeg risk in secondary markets (2–7% historically observed for top LSTs in acute stress).
- Slashing and validator concentration risk.
- Smart-contract risk in wrapper contracts.

On the fToken side, instruments such as fAVAX and fETH structurally censor downside tail risk at the protocol level by enforcing a minimum price $P_f$ tied to reserves $L_f$ and Tier-0 supply $S_0$ through a solvency invariant. The return distribution is **structurally truncated** on the downside: the left tail is cut off at $P_f$ as long as the invariant holds. The floor is endogenous and oracle-free; no external price feed is needed to compute solvency. **Simulation confirms 0% of paths breach the solvency invariant (FPR < 1.0) across all scenarios tested, even in -80% drawdown conditions.**

---

## 2. Introduction: From Yield Tokens To Engineered Floors

Digital Asset Treasuries (DATs) and funds with ETH or AVAX mandates increasingly want three things at once:

1. **Native, asset-denominated yield** rather than idle holdings.
2. **Structural downside mitigation** that goes beyond "HODL and hope".
3. **Re-usable collateral** that can safely support leverage or credit lines without fragile liquidation waterfalls.

Today, the default implementation of this bundle is staked assets via Liquid Staking Tokens (LSTs) such as stETH or sAVAX. LSTs are efficient wrappers around validator yield. They maintain near-par exposure to the underlying asset, pass through staking rewards, and are highly composable in DeFi. For many treasuries, "own the LST" is the baseline expression of an ETH or AVAX mandate.

Floor-backed tokens (fTokens) start from a different objective. Instead of accepting the full left tail of the underlying and simply adding yield on top, they try to **reshape the payoff profile**:

- Introduce a **non-decreasing floor**, computed from onchain reserves net of debt.
- Define **borrowing capacity against that floor**, not against volatile spot.
- Use fee flows and conservative yield to **ratchet the floor upward over time**.

### 2.1 The Stochastic LST Regime

Liquid Staking Tokens such as stETH and sAVAX wrap validator positions and expose holders to:

- The full price path of the underlying token.
- Staking rewards minus penalties and fees.
- Liquidity and smart-contract risks introduced by the wrapper and its secondary markets.

In normal conditions, LSTs behave like "underlying plus yield". In stress, they behave like **levered beta on the underlying** with an additional depeg channel through AMM liquidity and withdrawal queues. From a risk perspective, they are well suited to treasuries that want to maximize upside participation and can tolerate drawdowns on the underlying.

### 2.2 The Engineered fToken Regime

Floor-backed tokens take the opposite tack. They define:

1. A **floor price** $P_f$ enforced by protocol rules on the primary market.
2. **Floor reserves** $L_f$ and Tier-0 supply $S_0$ such that the system can always redeem Tier-0 tokens at $P_f$ as long as a simple invariant holds.
3. **Routing of trading and borrowing fees** into these reserves so that $P_f$ rises in discrete steps when headroom allows.

Two properties follow:

- **Downside relative to the floor is structurally censored** in the reserve numeraire as long as the solvency invariant is respected.
- **Upside is partially reinvested into structural protection**, since fee flows that could have accrued fully to holders are instead used to strengthen reserves and lift the floor.

Where LSTs turn staking yield into higher expected returns with unchanged downside shape, fTokens **turn protocol activity into thicker downside protection** and more predictable collateral behavior.

---

## 3. Architectural Deconstruction of Liquid Staking Tokens (LSTs)

We first formalize the LST baseline as a reference point.

### 3.1 Mechanisms of Value Accrual

Two common LST patterns:

**Rebase (stETH)**
Token balance increases with rewards:
$$\text{Balance}(t) = \text{Balance}(0) (1 + r)^t$$

**Reward-bearing (sAVAX)**
Exchange rate increases while nominal balance stays fixed:
$$\text{Price}_{\text{sAVAX}}(t) = \text{Price}_{\text{AVAX}}(t) \cdot \text{Index}(t)$$

In both cases, the aggregate LST supply must be backed by the value of staked assets minus any slashing losses.

### 3.2 Liquidity Cliff and Depeg Risk

LSTs rely on secondary markets (AMM pools, order books) to provide immediate liquidity. Key properties:

- There is no protocol-enforced floor on the LST/underlying exchange rate.
- In normal conditions, arbitrageurs keep that rate close to the staking-implied value.
- In stress, selling pressure can overwhelm AMM depth and the LST can trade at a discount.

Empirically:
- For major LSTs such as stETH, observed discounts during 2022 stress events (for example the Celsius/3AC unwind) were in the low single digits, typically around 2–7 percent.
- Much larger dislocations (20 percent or more) have occurred in distressed or exploited tokens in the broader DeFi space, but these are not representative of top-tier LST behavior.

Depegs tend to occur **during** market downturns. The depeg component and the underlying return are positively correlated in the tails, which is exactly the regime where VaR matters most.

---

## 4. Architectural Deconstruction of fTokens (Tier-0 Analysis)

We now deconstruct the floor-backed design using the corrected Tier-0 mechanics.

### 4.1 Tier-0 as a Live Trading Floor

In an fToken market:

- Tier-0 is the floor tier, quoted at price $P_f$.
- It is a live market tier on the bonding curve, not a special emergency mode.
- Tier-0 supply $S_0$ includes all fTokens at the floor, whether locked or liquid.

Coverage requirement:

- For every fToken in Tier-0, the protocol must be able to pay $P_f$ units of the reserve asset on redemption without violating solvency. Locking does not relieve this requirement.

This is the key conceptual shift. The floor is an active, fully-backed micro-economy, not a best-effort exit.

### 4.2 The Solvency Invariant

The solvency invariant is:

$$L_f - D \ge P_f S_0$$

Where:

- $L_f$: reserves allocated to backing Tier-0.
- $D$: outstanding debt from internal borrowing against fToken collateral.
- $P_f$: floor price in reserve units per fToken.
- $S_0$: Tier-0 supply.

The floor price is **computed programmatically** from onchain state:

$$P_f = \left\lfloor \frac{L_f - D}{S_0} \right\rfloor_{\text{tick}}$$

where the tick discretization rounds down to the nearest valid floor level.

Interpretation:

- Net reserves $L_f - D$ must cover the liability of redeeming all Tier-0 supply at the stated floor.
- Internal credit is explicitly accounted for; loans reduce the amount of backing available for the floor.
- The floor rises automatically as $(L_f - D)/S_0$ crosses tick thresholds.

The invariant is computed from onchain state, without oracles. No external price feed is required.

---

## 5. Comparative Scenario Analysis (Summary)

We compare sAVAX and fAVAX across stylized regimes, validated by agent-based Monte Carlo simulation (2,000 agents × 365 days per scenario).

### Return Comparison (USD and ETH Terms)

> **Dual numeraire presentation:** This table shows both USD returns (which include underlying price movement) and ETH-denominated floor growth (which isolates the floor mechanism). Both fTokens and LSTs carry identical USD exposure to the underlying.

**Simulated USD-Denominated Returns (365 days):**

| Scenario | fToken USD | LST USD | fToken VaR (95%) | LST VaR (95%) |
|----------|------------|---------|------------------|---------------|
| Super Cycle | +77.0% | +74.4% | -18.7% | -18.7% |
| Crab Market | +8.2% | +7.7% | -27.6% | -27.6% |
| Crypto Winter | -79.0% | -79.5% | -86.4% | -90.4% |

**Simulated ETH-Denominated Floor Growth (365 days):**

| Scenario | Floor Growth | Floor VaR (95%) |
|----------|--------------|-----------------|
| Super Cycle | +4.1% | +2.6% |
| Crab Market | +3.0% | +2.3% |
| Crypto Winter | **+5.0%** | +3.0% |

**Key observation:** Under the base parameter set (70% fees to floor, ~14,000 ETH/day volume, 2.6% LST yield), fTokens outperform LSTs in all simulated scenarios. The counter-cyclical nature of floor growth (highest in bear markets due to panic selling volume) provides additional downside protection.

---

*For the full technical analysis, including detailed solvency mechanics, credit facility design, and parameter sensitivity, please refer to the [Structural Solvency and Risk Topology](./Structural_Solvency_and_Risk_Topology.md) paper.*
