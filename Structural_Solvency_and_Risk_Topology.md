# The Rising Floor

## A Comparative Risk Analysis of Floor-Backed Tokens vs Liquid Staking Tokens

---

## Allocator Summary

*This summary is intended for institutional allocators, treasury managers, and risk committees. The full technical analysis follows.*

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

**Under the parameter regime studied here, fTokens outperform LSTs in all three market scenarios.** This result is contingent on: (1) trading volume generating 3-5% annual floor growth, (2) LST yield at 2.6% APY, and (3) 70% of fees routed to floor. Different parameter choices can change the outcome—see Section 8.10 for sensitivity analysis.

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

The "no liquidation, no bad debt" result holds only under strict design constraints (see **Design Envelope in Section 9.2**).

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

A naive implementation with constant tier capacities above the floor can make the floor increasingly heavy as the system scales, causing floor growth to slow or stagnate. We show that tier design is the key degree of freedom. By carefully choosing how much new supply is absorbed when tiers merge, protocols can keep floor elevation economically sustainable. The detailed scaling analysis and a harmonic-capacity tier schedule that improves long-run behavior are provided in Appendix B.

**Practical implication of tier design:** In plain terms, you don't want Tier-0 to be "all minted tokens forever." That makes each price tick more expensive as the protocol grows—eventually prohibitively so. Instead, you either cap Tier-0 at a percentage of total supply, or use a harmonic schedule where each merge adds a progressively smaller chunk of new supply to the floor. This keeps ticks affordable even at protocol scale. The trade-off is between floor growth rate (faster if Tier-0 is smaller) and floor breadth (more tokens benefit from the guarantee if Tier-0 is larger).

Several important caveats remain:

- A floor denominated in AVAX or ETH protects value in units of the underlying, not in USD. For institutional allocators, USD VaR and cross-asset correlation matter.
- Floor-relative VaR is zero by construction in the reserve numeraire, but operational frictions (gas costs, redemption queues) can create micro-losses. If reserves are rehypothecated into yield strategies, those strategies' risks enter the floor's backing.
- Credit issuance against the floor cannot break solvency by itself. With native floor-denominated credit, **bad debt is structurally impossible** when loans are collateralized by fTokens: the collateral's floor value can only increase while debt is fixed, causing LTV to automatically improve over time.

Within these constraints, floor-backed tokens offer superior risk-adjusted returns compared to LSTs under the parameter regime studied. The key insight from agent-based simulation (2,000 agents, 365-day horizon) is the **counter-cyclical floor**: floor growth reaches +5.0% in Crypto Winter versus +4.1% in Super Cycle. Panic selling generates more fees, which means the floor grows fastest precisely when downside protection matters most.

In USD terms over one year (simulated):
- Super Cycle: fToken +77.0% vs LST +74.4% (fToken leads by 2.6%)
- Crab Market: fToken +8.2% vs LST +7.7% (fToken leads by 0.5%)
- Crypto Winter: fToken -79.0% vs LST -79.5% (fToken leads by 0.5%, plus avoids simulated depeg events)

These results are contingent on trading volume sufficient to generate 3-5% annual floor growth and LST yield of 2.6%. If volume falls below ~12,000 ETH/day or fee routing is reduced, fTokens can underperform LSTs. This is a governance lever, not a free lunch.

We propose concrete design levers:

- A Floor Protection Ratio (FPR) as the main solvency metric.
- Headroom reserves to ensure tier merges are not stalled by credit utilization.
- Fee-routing and liquidity-reallocation policies that maintain floor elevation velocity over long horizons.

The Monte Carlo simulation framework and governance mechanisms presented here are intended as practical tools for protocol designers, risk teams, and allocators who want to adopt floor-backed tokens with clear, quantifiable guarantees.

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

In the ETH context, this gives you two structurally distinct building blocks:

- LSTs like stETH for **maximal beta and staking yield**.
- fETH for **ETH-denominated downside censorship, liquidation-free credit, and programmable exposure** (staked fETH as a yield asset; locked fETH as credit collateral).

A similar dichotomy exists on Avalanche between sAVAX and fAVAX.

This paper is about the **risk topology** that emerges when you put these two classes of instruments side by side. Rather than arguing that one dominates the other, we treat LSTs and fTokens as **complementary tools** and focus on three questions:

1. How do their **Value-at-Risk (VaR)** profiles differ in the underlying asset numeraire and in USD?
2. What are the **solvency mechanics** of a floor that is implemented as a live trading tier instead of a best-effort redemption promise?
3. Which governance and design levers matter most if treasuries intend to use fTokens as a defensive or senior tranche in their stack?

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

### 2.3 Tier Design as a Structural Lever

Because the floor is implemented as a **live trading tier** rather than a separate redemption window, its size matters. Every time higher tiers merge into Tier-0, more supply becomes entitled to redemption at the new floor. If tier capacities are naive (for example, fixed size across the whole curve), Tier-0 can become so large that further floor raises require prohibitive amounts of new reserves. The floor then tends to "freeze" at some level and loses much of its intended function.

Tier design is therefore not cosmetic. It is the main structural lever that determines whether:

- The floor remains a **living, elevating mechanism** over multi-year horizons.
- Or it becomes a **one-off bootstrap device** that is economically too heavy to move once the system is large.

We show later that with an appropriate tier schedule (for example, harmonically decaying capacities), the **total work to elevate the floor by $m$ tiers scales like $O(m \log m)$ instead of $O(m^2)$**. This keeps long-run elevation feasible even as treasuries and DATs scale into billions.

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

Duration of depegs depends on unstaking times, risk appetite of arbitrageurs, and broader market conditions.

### 3.3 Comparative Risk Table: LSTs

| Risk Component | Description | Probability | Severity (Order of Magnitude) |
|----------------|-------------|-------------|-------------------------------|
| Market beta | Full exposure to underlying price swings | Certain | High (up to 100 percent drawdown) |
| Slashing | Validator misbehavior or failure | Low (with diversified validators) | Low to moderate (single-digit percent potential loss) |
| Depeg | AMM imbalance or panic selling | Regime dependent; typically rare | Moderate (2–7 percent common for major LSTs in stress; more in distressed names) |
| Smart contract | Bugs in wrapper or staking logic | Low for mature protocols | Catastrophic if realized |

Existing LST risk frameworks (for example from Gauntlet or Chaos Labs) emphasize:

- External liquidity and slippage.
- Depeg risk under forced unwinds and leverage.
- Withdrawal queue dynamics.

Our focus is on the structurally different behavior of floor-backed designs.

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

### 4.3 Headroom (H): The Scarce Resource

Define headroom:

$$H = (L_f - D) - P_f S_0$$

Headroom quantifies the slack between net reserves and floor obligations.

- $H > 0$: surplus backing; room to raise the floor or extend credit.
- $H = 0$: boundary of solvency; no safe room to move.
- $H < 0$: insolvent at the stated floor.

Headroom dynamics:

- Increases when protocol fee revenue is routed into $L_f$.
- Decreases when the floor is raised (because $P_f S_0$ grows).
- Decreases when new loans increase $D$.

### 4.4 Safe Merge Between Tiers

Above Tier-0, the bonding curve is discretized into tiers:

- Tier-0: price $P_f$, supply $S_0$.
- Tier-1: price $P_1 = P_f + \Delta P$, minted supply $M_1$.
- Higher tiers: recursively defined.

As headroom grows and $P_f$ approaches $P_1$, a safe merge is allowed only if:

$$L_f - D \ge P_1 (S_0 + M_1)$$

If the condition holds:

- Tier-1 minted supply $M_1$ is absorbed into Tier-0.
- New Tier-0 supply is $S_0' = S_0 + M_1$.
- New floor is $P_f' = P_1$.

If it fails, the system waits for more fees or liquidity reallocation and thus more headroom. This stepwise behavior produces a staircase floor path.

---

## 5. Quantitative Risk Modeling and Numeraire Choice

We now compare LSTs and fTokens through a VaR lens and address the choice of numeraire directly.

### 5.1 LST Risk Model: Augmented Beta (With Caveats)

For an LST, define:

$$R_{\text{LST}} = R_U + y + \Delta e$$

where:

- $R_U$: return of the underlying over horizon $T$.
- $y$: staking yield over $T$.
- $\Delta e$: change in depeg (premium or discount) relative to the staking-implied value.

For a first-order VaR approximation:

- Model $R_U$ as approximately normal $N(\mu_U, \sigma_U^2)$ on moderate horizons.
- Treat $\Delta e$ as a heavy-tailed shock with variance $\sigma_e^2$ and correlation $\rho$ with $R_U$.

Then:

$$\text{VaR}_{\text{LST}}^{\alpha} \approx V_0 \left( z_{\alpha} \sqrt{\sigma_U^2 + \sigma_e^2 + 2 \rho \sigma_U \sigma_e} - \mu_{\text{total}} \right)$$

where $V_0$ is initial value, $z_{\alpha}$ is the standard-normal quantile, and $\mu_{\text{total}}$ is combined drift from appreciation and yield.

In stress regimes, $\rho$ is typically positive and sizeable. Depegs tend to coincide with drawdowns on the underlying. This increases effective tail risk relative to a naive assumption of independent shocks.

This Gaussian treatment still understates extreme tail risk because $\Delta e$ is not truly Gaussian, but it is useful for framing.

### 5.2 fToken Structural VaR (Floor-Denominated)

In an fToken market, the floor is not a policy parameter but a **programmatic computation** from onchain state:

$$P_f = \left\lfloor \frac{L_f - D}{S_0} \right\rfloor_{\text{tick}}$$

As long as:

- The solvency invariant $L_f - D \geq P_f S_0$ holds, and
- Redemptions are possible within operational constraints,

the market price in reserve units should satisfy:

$$P_{\text{fToken}}(t) \geq P_f(t)$$

If we take reserve units as numeraire, the downside in that numeraire is censored at the floor:

$$\text{VaR}_{\text{fToken}}^{\text{downside, floor-numeraire}} = 0$$

This is not an approximation or a soft guarantee—it is a mathematical consequence of the invariant. Relative to $P_f$, losses in reserve units are eliminated by construction.

**Simulation validation:** Agent-based Monte Carlo testing confirms the solvency invariant holds with robust headroom across all scenarios (see Section 8.7 for detailed metrics). Floor-relative downside VaR is zero by construction.

**What can impair floor-relative VaR?**

The floor is immune to spot price movements, but a small set of risks can still affect value in reserve units:

1. **Smart contract risk.** Bugs in the protocol logic could break the invariant or block redemptions.

2. **Reserve rehypothecation.** If $L_f$ is deployed into yield strategies (e.g., staking the reserve asset), those strategies carry their own risks—slashing, smart contract failure, illiquidity. A loss in the rehypothecated portion directly reduces $L_f$ and can impair solvency. For protocols that keep $L_f$ in the base asset without rehypothecation, this risk is absent.

3. **External collateral bad debt.** If the protocol accepts collateral other than fTokens (e.g., LSTs, stablecoins) for credit, those positions can generate bad debt through traditional pathways. Native fToken-collateralized loans cannot generate bad debt (see Section 9.2).

4. **Redemption frictions.** Gas costs, queue limits, or unwrapping delays (see Section 5.4) can create micro-losses for small holders or introduce timing gaps.

Crucially, **spot price movements do not appear in this list**. The invariant depends on $L_f$, $D$, and $S_0$—none of which are functions of spot. This is the structural difference from LSTs, where depeg risk is driven by market conditions.

### 5.3 Numeraire Choice: AVAX-Denominated Floor vs USD-Denominated Risk

Institutions generally care about risk in a fiat numeraire.

If the floor is denominated in AVAX:

- An fAVAX holder is protected in AVAX units, not in USD.
- If AVAX drops 75 percent in USD, both sAVAX and fAVAX will lose roughly 75 percent of their USD value, even if fAVAX returns more AVAX per initial unit.

Let:

- $P_{\text{AVAX}\rightarrow \text{USD}}(t)$ be AVAX/USD price.
- $P_f(t)$ be the floor in AVAX per fAVAX.

Then:

$$V_{\text{fToken, USD}}(t) = P_f(t) \cdot P_{\text{AVAX}\rightarrow \text{USD}}(t)$$

Even if $P_f(t)$ rises over time, USD value remains sensitive to AVAX/USD.

For USD-centric risk control, three options exist:

1. Accept AVAX beta and treat fAVAX as an AVAX-denominated defensive asset that improves risk-adjusted returns in AVAX units.
2. Hedge AVAX/USD externally (for example via futures or options) and hold fAVAX as the protected AVAX leg.
3. Design USD-floor fTokens by combining AVAX reserves with explicit hedging (perps, options). This yields a more complex structured note and sits somewhat outside a simple LST versus fToken comparison.

In all cases, the value of the floor for institutional allocators must be evaluated net of hedging costs and cross-asset correlations.

### 5.4 Redemption Frictions and Reserve Composition

The mathematical floor guarantee assumes frictionless redemption. Real systems introduce operational considerations:

**Secondary market pricing below $P_f$.**

If gas and fees are significant, small holders may not arbitrage even if the AMM price is slightly below $P_f$. For them, effective value includes a micro-loss from not fully capturing the floor. This is an economic friction, not a solvency issue—the protocol can still redeem at $P_f$.

**Redemption limits and queues.**

For grief prevention, a protocol may throttle redemptions (for example per-block limits). In stress, a queue can form and AMM prices may trade below $P_f$ until the queue clears. The floor is still honored for those who wait; the friction is temporal.

**Reserve composition and rehypothecation.**

If $L_f$ is held purely in the base asset (e.g., native AVAX), redemption is immediate and the floor is fully liquid. However, if $L_f$ includes yield-bearing positions:

- **Staked assets** (e.g., sAVAX) introduce unbonding periods (7–14 days) and slashing risk. A slashing event directly reduces $L_f$ and can impair solvency.
- **Tokenized off-chain assets** (e.g., T-bills) may have settlement delays or counterparty risk.
- **LP positions or other DeFi strategies** carry their own smart contract and liquidity risks.

The degree of reserve rehypothecation is a governance choice that trades yield against liquidity and risk. A conservative reserve policy (minimal rehypothecation) keeps floor-relative VaR near zero; an aggressive policy (significant staking or strategy deployment) introduces the risks of those strategies into the floor's backing.

**Implications for VaR modeling.**

A full VaR model for fTokens should:

- Specify reserve composition and rehypothecation fraction.
- Model slashing or strategy-loss probabilities if reserves are deployed.
- Bound maximum queue lengths and expected wait times.
- Model gas and transaction costs for redemption arbitrage.

For protocols with unhypothecated reserves, floor-relative VaR in the reserve numeraire is effectively zero (subject only to smart contract risk). For protocols with rehypothecated reserves, the VaR inherits the risk profile of the deployed strategies—but this is a known, governable parameter, not an inherent property of the floor design.

### 5.5 Portfolio View and Correlations

Most institutional portfolios hold multiple assets. For a portfolio with weights $w_i$ in assets $A_i$:

$$R_{\text{portfolio}} = \sum_i w_i R_i$$

so portfolio VaR depends on:

- Individual asset variances $\sigma_i^2$.
- Covariances $\text{Cov}(R_i, R_j)$.

Qualitative expectations:

- fTokens remain highly correlated with their underlying over long horizons, especially if the floor is denominated in the same asset.
- Floor protection mainly improves lower-tail behavior (reduced severity of drawdowns) rather than creating uncorrelated returns.
- Correlation between an LST and the fToken of the same underlying is likely close to 1 in normal regimes and may diverge somewhat in stress when floor dynamics and depegs differ.

Portfolio-level VaR therefore benefits from:

- Lower marginal tail risk of fTokens.
- Better behavior under internal leverage (non-liquidatable positions; see Section 7).
- Not from major decorrelation compared to the underlying.

Appendix A outlines a Monte Carlo framework that can quantify these effects.

### 5.6 Entry Basis and Premium Risk

So far the analysis has been floor-relative. For an actual investor, **entry price relative to the floor** is a distinct risk dimension.

In practice, healthy fToken markets trade at a **premium** to the floor. For example, if $P_f = 1.00$ and the market price is $1.10$, a new buyer at 1.10 faces immediate downside to 1.00. Their near-term floor-relative VaR is 9 percent in the reserve numeraire, even though the floor itself is non-decreasing.

Two implications follow:

- Floor-relative VaR in the reserve numeraire may be close to zero, but **investor VaR around their entry basis is not**. A treasurer who must mark to a 3-month horizon cares about the spread between entry price and $P_f$, not only about the existence of the floor.
- fTokens are **best suited to long-term collateral and defensive sleeves**, where the expectation is that the floor will eventually catch up with, and then exceed, the entry premium. They are less suitable as short-term trading vehicles for investors who might need to exit while the premium is still volatile.

In portfolio context, fTokens are best understood as "same beta, better lower tail" building blocks rather than as diversifiers. A risk-conscious allocator should therefore:

- Track the premium $M = P_{\text{spot}}/P_f$.
- Consider policies such as only entering when $M$ is within a target band, or dollar-cost averaging to smooth basis risk.
- Model **premium volatility** explicitly alongside floor-relative risk.

In other words, the floor truncates the left tail, but **does not guarantee that an investor who bought at a high premium will not see mark-to-market losses** before the floor catches up.

---

## 6. Tier Design and Long-Term Behavior

The long-term behavior of a floor-backed system depends on how Tier-0 grows as the protocol succeeds.

- If every merge from higher tiers adds a large block of new supply to Tier-0, the floor becomes harder and harder to move. Over time, the cost of raising $P_f$ can outpace feasible fee inflows, and floor growth stagnates.
- If higher tiers are designed with smaller incremental capacity, Tier-0 grows more slowly and the cost of future elevation remains manageable.

From a risk and design perspective:

- Tier scheduling is not just a UX choice. It directly affects whether the floor remains a living mechanism or becomes a one-off bootstrap device.
- A reasonable approach is to be generous in early tiers (to get supply and liquidity) and steadily more conservative in higher tiers (to avoid a future "immovable floor" problem).

The formal scaling analysis and a specific harmonic-capacity schedule that achieves favorable long-run behavior are given in Appendix B. In the main body we only need the takeaway:

> Tier design is the main structural lever that determines whether a floor-backed token can keep raising its floor over multiple years without hitting an economic wall.

### 6.1 Liquidity Reallocation and Realized Gains

Fee flow is not the only source of floor elevation. In full implementations, the protocol can also employ **Liquidity Reallocation (LRE)**.

When markets trade well above the floor, part of the liquidity or PnL generated in higher tiers can be reallocated downwards into floor reserves. Conceptually this converts realized gains at high prices into **permanent backing** at the floor. LRE is typically guarded by conditions (for example only active when the premium exceeds a threshold and volatility is moderate) to avoid destabilizing the market.

For risk analysis this matters because:

- In **high-volatility uptrends**, LRE can meaningfully accelerate floor growth beyond what fees alone would support.
- In **quiet markets**, floor growth is dominated by fees and any passive yield on reserves.
- LRE increases the coupling between realized trading performance in the premium tiers and structural risk reduction in the floor.

A VaR model for fTokens in a live deployment should therefore treat both **revenue injection** and **liquidity reallocation** as floor drivers, with governance parameters controlling how aggressive LRE can be.

---

## 7. Native Credit as a Strategic Asset

The discussion of headroom and debt so far has focused on system-level risk mechanics. But native credit in fToken systems is not merely a risk to manage—it is a distinct value proposition with no direct analogue in the LST stack. This section makes the strategic case explicit.

### 7.1 The Liquidation Problem in External DeFi Lending

When an LST holder wants leverage, they typically deposit their LST into an external lending protocol (Aave, Compound, Benqi, etc.) and borrow against it. The protocol values the collateral at spot and enforces a Loan-to-Value (LTV) ratio, typically 70–80% for major LSTs.

If the underlying asset falls, the collateral's USD value drops, and the position approaches liquidation. During acute drawdowns:

- Liquidations cascade as forced selling pushes prices lower.
- LST depegs compound the problem—collateral loses value both from underlying beta and from the depeg itself.
- Borrowers who cannot top up collateral are liquidated at the worst possible time.
- Protocol-level bad debt can accumulate if liquidations fail to cover loans.

This creates a **procyclical liquidation waterfall**: precisely when holders most need their positions to survive, external lending mechanics force them to sell or be sold.

### 7.2 Floor Credit: The Native Innovation

In an fToken system, native credit is denominated against the **floor**, not against volatile spot. This is the core structural innovation.

For a position holding $n$ fTokens:

$$\text{Native Borrowing Capacity} = \text{LTV}_f \cdot n \cdot P_f$$

The collateral reference is the floor price $P_f$, which is **computed programmatically** from onchain state:

$$P_f = \left\lfloor \frac{L_f - D}{S_0} \right\rfloor_{\text{tick}}$$

The floor is not "set" by governance or policy—it is a mathematical consequence of reserves, debt, and supply. This changes the risk topology fundamentally:

**No spot-driven liquidation.** A drop in the underlying's USD price—or a compression of the premium above the floor—does not affect the solvency invariant. The invariant $L_f - D \geq P_f S_0$ depends only on reserves, debt, and Tier-0 supply, none of which move with spot.

**Floor only moves up.** Because the floor is derived from $(L_f - D)/S_0$, and because $L_f$ grows from fee inflows while $S_0$ grows only through merges (which require coverage checks), the floor is structurally non-decreasing.

**Self-healing loans.** Unlike traditional DeFi lending, fToken-collateralized loans automatically become safer over time:

| Day | Floor | Collateral Value | Debt | LTV |
|-----|-------|------------------|------|-----|
| 1 | 1.00 ETH | 100 ETH | 90 ETH | 90% |
| 30 | 1.10 ETH | 110 ETH | 90 ETH | 81.8% |
| 60 | 1.20 ETH | 120 ETH | 90 ETH | 75% |

The loan is self-healing because collateral (fTokens) can only increase in floor value, while debt (reserve asset) is fixed. LTV automatically improves as the floor rises.

**Bad debt is structurally impossible for native fToken loans under the model assumptions.** For a loan to become underwater, collateral value must fall below debt. But floor value cannot fall (absent smart contract failure or reserve rehypothecation losses), so fToken-collateralized positions cannot become undercollateralized. This is confirmed by simulation: across all scenarios over 365 days, 0% of paths experienced FPR < 1.0.

**Credit against floor cannot break solvency.** New loans reduce headroom $H = (L_f - D) - P_f S_0$, but as long as the protocol only issues credit when $H \geq \Delta D$, the solvency invariant is preserved by construction. Credit issuance is bounded by available headroom—it cannot consume more than exists.

**Implications for protocol design:**

- No liquidation infrastructure needed for native fToken credit
- No procyclical selling pressure during market stress
- Credit facility origination fees (e.g., 2%) are effectively risk-free revenue under the invariant
- LTV can be set aggressively high (e.g., 90%) because the loan only becomes safer

**Residual risks:** Smart contract bugs could break the invariant. If the protocol accepts collateral types other than fTokens (e.g., LSTs, stablecoins), those positions can generate bad debt through traditional pathways.

### 7.3 The Premium Is Not Collateral (In Native Credit)

A critical point: native fToken credit does **not** allow borrowing against the premium $\delta = P_{\text{spot}} - P_f$. The premium represents market value above the floor, but it is volatile and not part of the native collateral base.

If a holder wants to lever against the full spot value of their fToken (including the premium), they must take their fToken to an **external money market** and borrow against spot price. In that case:

- The external protocol values collateral at $P_{\text{spot}}$, not $P_f$.
- If spot falls toward the floor, the position approaches liquidation.
- The holder reintroduces all the liquidation risks that native credit was designed to avoid.

This is a deliberate design boundary. Native credit provides **unconditional stability** in floor units precisely because it ignores the volatile premium. Holders who want more aggressive leverage can access it externally, but they accept a different risk profile.

### 7.4 Native Looping: Amplified Exposure with Structural Protection

One of the most powerful applications of native credit is **looping**: borrowing against fToken collateral at the floor, using the proceeds to acquire more fTokens, and repeating. This amplifies exposure to fToken performance while maintaining floor-denominated safety.

The profitability of a looped position over a holding period depends on three factors:

**1. Premium Delta ($\Delta \delta$)**

If the premium expands (spot rises faster than the floor), the looped position gains on the additional fTokens acquired. If the premium compresses, gains are reduced or reversed. Premium volatility is the main short-term driver of loop returns.

**2. Floor Elevation ($\Delta P_f$)**

Over the holding period, the floor itself may rise through tier merges and fee accumulation. Floor elevation permanently captures value into the protected layer. Even if the premium compresses, a higher floor means the looped position's downside is now bounded at a better level than at entry.

This is the key long-term driver: a looper who enters when $P_f = 1.00$ and exits when $P_f = 1.15$ has locked in 15% structural gain on their floor-layer exposure, regardless of where spot trades at exit (as long as it remains above the new floor).

**3. Borrowing Fees**

Looping is not free. Borrowing costs accumulate over the holding period. The net return from looping is approximately:

$$R_{\text{loop}} \approx k \cdot (\Delta \delta + \Delta P_f) - \int_0^T r_{\text{borrow}}(t) \, dt$$

where $k$ is the effective leverage multiplier (constrained by floor LTV) and the integral captures cumulative borrowing costs.

For looping to be profitable:

- $\Delta P_f$ provides a structural tailwind that external lending cannot replicate (LSTs have no rising floor).
- $\Delta \delta$ can be positive or negative depending on market conditions.
- Borrow rates must be low enough relative to expected floor elevation and premium appreciation.

**Comparison to LST Looping**

Looping with LSTs in external protocols (e.g., deposit stETH → borrow ETH → buy more stETH) is also possible but carries fundamentally different risks:

- Collateral is valued at spot, so a market drawdown can liquidate the entire loop.
- There is no floor elevation tailwind—the strategy depends entirely on the LST premium (staking yield minus borrow rate) remaining positive.
- Liquidation cascades can force exits at the worst possible time.

fToken looping, by contrast, allows leveraged exposure while maintaining a structural floor. A looper cannot be liquidated by spot movements alone—only by floor insolvency, which is a system-level event governed by FPR.

### 7.5 Strategic Use Cases

The floor-only credit structure enables several applications that are difficult or dangerous with spot-based external lending:

**Treasury leverage without liquidation exposure.** A DAO treasury or fund holding fToken can borrow against floor value to fund operations, make investments, or meet redemptions—without the risk that a market downturn forces a fire sale of core holdings. The treasury retains its fToken position through any volatility that doesn't breach the floor.

**Yield amplification with predictable margin.** Borrowers can deploy borrowed funds into yield strategies (staking, LP positions, etc.) knowing their collateral won't be liquidated mid-strategy due to spot movements.

**Institutional mandates.** Many institutional allocators are prohibited from taking liquidation-exposed leverage. Floor credit, with its structural protection against forced selling, may satisfy mandates that would reject LST-collateralized borrowing in external protocols.

**Long-term accumulation via looping.** Participants who are structurally bullish on floor elevation can use looping to amplify their exposure to $\Delta P_f$ over multi-month or multi-year horizons, treating premium volatility as noise and borrowing costs as the price of leveraged participation.

### 7.6 Headroom: Post-Elevation Surplus

Headroom $H = (L_f - D) - P_f S_0$ is not a budget that "competes" between floor raises and credit. The sequence is:

1. **Fees accrue** to protocol revenue.
2. **Fees are deployed** to $L_f$.
3. **Floor rises** as $(L_f - D)/S_0$ crosses tick thresholds.
4. **Headroom emerges** as the surplus above floor obligations after the raise.
5. **Credit capacity per token increases** because $P_f$ is now higher.

Headroom is therefore the *result* of floor elevation, not an alternative use of the same funds. When new loans are issued, they consume headroom (increasing $D$), but this cannot break solvency as long as loans are only issued when $H \geq \Delta D$.

The governance trade-off is subtler than "floor vs credit":

- **Aggressive credit issuance** keeps $H$ near zero, which means the system has less buffer for the next merge (absorbing Tier-1 supply requires $L_f - D \geq P_1(S_0 + M_1)$). If credit utilization is high, merges may stall until fees rebuild headroom.
- **Conservative credit issuance** leaves more headroom, enabling faster merges and more aggressive floor elevation.

The real trade-off is between **credit utilization now** and **floor elevation velocity**. Both are valuable; governance determines the balance through utilization caps, borrow rates, and fee routing.

### 7.7 Summary: A Structurally Different Credit Topology

Native fToken credit is floor credit only—and that constraint is precisely what makes it valuable. By refusing to collateralize the volatile premium, native credit provides unconditional stability that external lending cannot match.

| Dimension | LST + External Lending | fToken + Native Credit |
|-----------|------------------------|------------------------|
| Collateral reference | Spot price (volatile) | Floor price (non-decreasing) |
| Floor computation | N/A | $P_f = \lfloor(L_f - D)/S_0\rfloor_{\text{tick}}$ |
| Liquidation trigger | Spot drawdown | Never (floor can't decrease) |
| Bad debt risk | Yes (failed liquidations) | No (self-healing loans)* |
| Cascade risk | High (correlated liquidations) | None (no liquidations) |
| Leverage tailwind | None | Floor elevation ($\Delta P_f$) |
| Premium as collateral | Yes (full spot exposure) | No (premium excluded) |
| LTV trajectory | Worsens in downturns | Improves over time |
| Credit risk to protocol | Significant | Zero (simulation: 0 bad debt) |

**Simulation validation:** Across all simulation paths over 365 days:
- Bad debt: 0 ETH
- FPR breach events: 0
- Minimum FPR: 1.113 (robust solvency throughout)

The no-liquidation design means locked tokens stay locked indefinitely if borrowers don't repay. The protocol simply waits—no cascade risk, no procyclical selling.

For treasuries and allocators who value predictable leverage and cannot tolerate forced selling, native credit may be as important as the floor itself. For active participants, the floor elevation tailwind ($\Delta P_f$) makes looping strategies viable over horizons where external LST loops would be too risky to sustain.

---

## 8. Comparative Scenario Analysis

We now compare sAVAX and fAVAX across stylized regimes, validated by agent-based Monte Carlo simulation (2,000 agents × 365 days per scenario).

### 8.1 Simulation Parameters

**Agent-Based Model Configuration:**

| Parameter | Value | Description |
|-----------|-------|-------------|
| Agent Count | 2,000 | Heterogeneous market participants |
| Horizon | 365 days | Full year simulation |
| Paths per scenario | 500 | Monte Carlo paths |
| Fee to Floor (α_f) | 70% | Portion of fees → floor reserves |
| LTV | 70% | Standard borrowing against floor |
| Buy/Sell Fee | 0.5% | Per-transaction fee |
| Loan Origination Fee | 2% | One-time fee, no ongoing interest |
| LST Yield | 2.6% APY | Staking yield benchmark |

**Agent Types:**

| Type | Share | Behavior |
|------|-------|----------|
| YieldSeekers | 45% | Core holders seeking stable yield, rebalance periodically |
| DATAgents | 20% | Value investors who buy when price < fair value |
| LeverageSeekers | 15% | Aggressive traders who loop leverage when premium is low |
| Arbitrageurs | 10% | Short-term traders exploiting price inefficiencies |
| FloorHolders | 10% | Long-term holders using floor for capital efficiency |

**Churn Dynamics:**
- Profit taking: Agents exit after +25% returns
- Stop losses: Agents exit after -15% drawdown
- New entrants: Fresh capital replaces exiting agents, maintaining population

### 8.2 Scenario Definitions

| Scenario | Description | Drift (μ) | Volatility (σ) |
|----------|-------------|-----------|----------------|
| Super Cycle | Strong bull market | +70% | 70% |
| Crab Market | Sideways, moderate vol | +5% | 40% |
| Crypto Winter | Severe bear market | -80% | 80% |

**Daily Volume (average per path):**

| Scenario | Daily Volume | Annual Turnover |
|----------|--------------|-----------------|
| Super Cycle | 13,624 ETH | High |
| Crab Market | 14,689 ETH | Moderate |
| Crypto Winter | 21,079 ETH | **Highest** (panic selling) |

### 8.3 Return Comparison (USD and ETH Terms)

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

**Key observation:** Under the base parameter set (70% fees to floor, ~14,000 ETH/day volume, 2.6% LST yield), fTokens outperform LSTs in all simulated scenarios. The counter-cyclical nature of floor growth (highest in bear markets due to panic selling volume) provides additional downside protection. This result is parameter-dependent; see Section 8.10 for sensitivity analysis.

### 8.4 Super Cycle: Strong Bull Market

Assume:

- Strong bull market with +70% annual drift.
- High volatility (70%).
- Moderate daily volume as holders tend to hold.

**Simulation Results (365 days):**

| Metric | fToken | LST |
|--------|--------|-----|
| USD Return | **+77.0%** | +74.4% |
| Floor Growth (ETH) | +4.1% | N/A |
| VaR (95%) | -18.7% | -18.7% |
| Supply Growth | +27.3% | N/A |
| Depeg Events | 0 | 1.2 avg |

**fToken outperforms on USD returns (+2.6%)** because:

- Floor growth (+4.1%) exceeds LST yield (2.6%)
- Both capture underlying rally, but fToken adds more yield
- Zero depeg events vs 1.2 for LST

**fToken also provides:**

- Structural downside protection (floor cannot decrease)
- Superior position for subsequent market downturn
- No depeg risk

### 8.5 Crab Market: Sideways with Moderate Volatility

Assume:

- Sideways market with +5% annual drift.
- Moderate volatility (40%).
- Steady trading activity.

**Simulation Results (365 days):**

| Metric | fToken | LST |
|--------|--------|-----|
| USD Return | **+8.2%** | +7.7% |
| Floor Growth (ETH) | +3.0% | N/A |
| VaR (95%) | -27.6% | -27.6% |
| Supply Growth | +26.9% | N/A |
| Depeg Events | 0 | 0.4 avg |

**fToken outperforms on USD returns (+0.5%)** because:

- Floor growth (+3.0%) exceeds LST yield (2.6%)
- Moderate trading generates steady fee revenue
- Margin is smaller but fToken still wins

**fToken also provides:**

- Structural downside protection
- Zero depeg events
- Building protection for potential downturns

### 8.6 Crypto Winter: Severe Bear Market (The Bear Market Paradox)

Assume:

- Severe bear market with -80% annual drift.
- High volatility (80%).
- **Panic selling drives highest volume.**

**Simulation Results (365 days):**

| Metric | fToken | LST |
|--------|--------|-----|
| USD Return | **-79.0%** | -79.5% |
| Floor Growth (ETH) | **+5.0%** | N/A |
| VaR (95%) | **-86.4%** | -90.4% |
| Daily Volume | 21,079 ETH | N/A |
| Depeg Events | 0 | **7.6 avg** |
| Depeg Impact | 0% | **-38%** |

**The Bear Market Paradox:** Floor growth is HIGHEST in Crypto Winter (+5.0%) because:

- Panic selling drives highest daily volume (21,079 ETH vs 13,624 in bull)
- More volume = more fees = faster floor elevation
- Floor rises even as underlying crashes 80%

**fToken significantly outperforms:**

- USD Return: -79.0% vs -79.5% (fToken wins by 0.5%)
- VaR (95%): -86.4% vs -90.4% (fToken has 4% better tail risk)
- Zero depeg events vs 7.6 for LST (cumulative -38% drag)
- Floor appreciation provides natural hedge

**This is the regime where fToken design matters most:** The counter-cyclical floor growth provides downside protection precisely when it's needed, while LST suffers severe depeg events.

### 8.7 Solvency Validation

Across all 1,500 simulation paths:

| Scenario | Min FPR (5th %ile) | Mean Min FPR | Final FPR (Mean) | Paths < 1.0 |
|----------|-------------------|--------------|------------------|-------------|
| Super Cycle | 1.113 | 1.113 | 1.125 | 0.0% |
| Crab Market | 1.113 | 1.113 | 1.122 | 0.0% |
| Crypto Winter | 1.113 | 1.113 | 1.128 | 0.0% |

**FPR Zones:**
- 🟢 Green: FPR ≥ 1.10 (healthy)
- 🟡 Yellow: 1.05 ≤ FPR < 1.10 (caution)
- 🔴 Red: FPR < 1.05 (circuit breakers)

**0% insolvency across all paths.** The system maintains a healthy buffer above 1.10 even in extreme -80% drawdown scenarios. The conservative design (70% LTV, 70% fees to floor) ensures robust solvency.

### 8.8 LST Depeg Analysis: Stress-Correlated Risk

| Scenario | Mean Depeg Events | Depeg Probability | Annual Impact |
|----------|-------------------|-------------------|---------------|
| Super Cycle | 1.2 | Low | -2.4% |
| Crab Market | 0.4 | Very Low | -1.2% |
| Crypto Winter | **7.6** | **High** | **-38%** |

**Depeg risk is stress-correlated:** Probability increases ~10x during market crashes. Over a full year of Crypto Winter, the average path experiences 7.6 depeg events with cumulative -38% impact on returns.

This is the key asymmetry: **LST depeg risk is highest precisely when downside protection matters most.** fTokens provide structural immunity—floor value is guaranteed regardless of market stress.

### 8.9 Summary: Simulation Results Under Base Parameters

**Core finding:** Under the base parameter set, fTokens outperform LSTs on both total USD returns and risk-adjusted metrics across all simulated market regimes.

**Simulated USD Returns (365 days):**

| Scenario | fToken | LST | fToken Edge | Floor Growth |
|----------|--------|-----|-------------|--------------|
| Super Cycle | +77.0% | +74.4% | +2.6% | +4.1% |
| Crab Market | +8.2% | +7.7% | +0.5% | +3.0% |
| Crypto Winter | -79.0% | -79.5% | +0.5% | +5.0% |

**Why fTokens outperform in this model:** Floor growth (3.0-5.0%) exceeds LST yield (2.6%) under the volume assumptions used.

**Simulated Risk-Adjusted Metrics:**

| Metric | fToken | LST | Winner |
|--------|--------|-----|--------|
| Sharpe Ratio | Higher | Lower | fToken |
| VaR (95%) | Better | Worse | fToken |
| Max Drawdown | Bounded by floor | Unbounded | fToken |
| Tail Risk | Bounded | Unbounded (depeg) | fToken |
| Simulated Depeg Exposure | 0 | 7.6 events/year (bear) | fToken |

*Note: The depeg statistics are model outputs, not historical measurements. Historically, top-tier LSTs have seen 2-7% discounts in acute stress.*

**The Counter-Cyclical Floor:**

Floor growth is highest in bear markets:
- Super Cycle: +4.1% floor growth (13,624 ETH/day volume)
- Crab Market: +3.0% floor growth (14,689 ETH/day volume)
- Crypto Winter: **+5.0% floor growth** (21,079 ETH/day volume)

Panic selling drives more volume → more fees → faster floor elevation. The floor rises even as the underlying crashes 80%. This provides a natural hedge that is most effective precisely when you need it.

### 8.10 Parameter Sensitivity: When fTokens Underperform

The simulation results above are contingent on specific parameter choices. fTokens can underperform LSTs if:

**1. Volume is insufficient**

| Daily Volume | Floor Growth (est.) | vs LST 2.6% Yield | Outcome |
|--------------|---------------------|-------------------|---------|
| 8,000 ETH | ~1.7% | Below | LST wins |
| 12,000 ETH | ~2.6% | Breakeven | Tie |
| 15,000 ETH | ~3.2% | Above | fToken wins |
| 20,000 ETH | ~4.5% | Well above | fToken wins |

**Breakeven volume:** ~12,000 ETH/day at current fee parameters.

**2. Fee routing is reduced**

| Fee to Floor (α_f) | Floor Growth (at 15k vol) | vs LST 2.6% | Outcome |
|--------------------|---------------------------|-------------|---------|
| 50% | ~2.3% | Below | LST wins |
| 60% | ~2.7% | Slightly above | Close |
| 70% | ~3.2% | Above | fToken wins |
| 80% | ~3.6% | Well above | fToken wins |

**3. LST yields rise**

If LST staking yields increase (e.g., to 4-5% APY due to MEV or restaking), fTokens need proportionally higher volume to compete on raw returns. However, fTokens retain their risk-adjusted advantages (no depeg, no liquidation) regardless of yield differential.

**4. Protocol is early-stage**

New protocols with low trading activity may not generate sufficient fees. The fToken value proposition strengthens as the protocol matures and volume grows.

**Governance implication:** Fee routing (α_f) and volume incentives are governance levers. If floor growth falls below LST yields, governance can adjust parameters—but this is a trade-off against other protocol objectives (e.g., LP rewards, treasury accumulation).

---

## 9. Endogenous Credit Risk: Headroom, Debt, and Fragility

Loans against fToken collateral are not external; they enter the solvency invariant through $D$. This concentrates credit risk.

### 9.1 Headroom Mechanics

Recall:

$$H = (L_f - D) - P_f S_0$$

Headroom is the surplus of net reserves above floor obligations. It emerges after floor elevation and is consumed by:

- **New loans** (which increase $D$).
- **Tier merges** (which increase $S_0$ and thus the coverage requirement $P_f S_0$).

The solvency invariant $L_f - D \geq P_f S_0$ is equivalent to $H \geq 0$. As long as the protocol only:

- Issues loans when $H \geq \Delta D$, and
- Executes merges only when safe-merge conditions hold,

the invariant is preserved by construction. **Credit issuance cannot break solvency**—it can only consume available headroom.

The practical constraint is on **velocity**: high credit utilization (low $H$) means less buffer for merges. If Tier-1 is ready to merge but $H < P_1 \cdot M_1$, the merge stalls until fees rebuild headroom. Governance can influence this through:

- Utilization caps that reserve a fraction of $H$ for merges.
- Borrow rates that increase as $H$ shrinks.
- Fee routing parameters that accelerate headroom rebuilding.

### 9.2 No Liquidation, No Bad Debt: The Credit Facility Design

A key innovation of the fToken credit facility: **there is no liquidation mechanism**. This fundamentally changes the risk profile compared to traditional DeFi lending.

**How traditional DeFi lending creates bad debt:**

In external lending protocols (Aave, Compound, etc.), loans against volatile collateral can become underwater:

1. Collateral is valued at spot price
2. Spot price drops faster than liquidation can execute
3. Debt exceeds collateral value → bad debt → protocol loss

**How fToken native credit works:**

1. Borrower **locks** fTokens → borrows reserve asset (ETH/AVAX) at 70% LTV (of floor value)
2. fTokens stay locked until borrower repays debt
3. **No interest accrues** → debt is fixed in reserve asset terms
4. If borrower walks away → fTokens remain locked indefinitely, debt stays on books

**From the protocol's perspective:**
- Locked fTokens are still there (cannot be redeemed)
- Outstanding debt is still owed
- **No bad debt** because collateral isn't liquidated or written off
- Protocol simply waits for repayment—potentially forever

**Why this works (the coverage invariant):**

$$\text{Required reserves} = P_f \times \text{tradeable\_supply}$$

Where `tradeable = total_supply - locked_supply`. Locked tokens **don't count** toward the coverage requirement:
- Locking removes tokens from tradeable supply
- This reduces required reserves proportionally
- Even if borrower never repays, solvency is maintained

**Example: Borrower Default Scenario**
```
Day 1:  Borrower locks 100 fTokens (floor = 1.0 reserve unit), borrows 70 reserve units
        Protocol: locked += 100, tradeable -= 100, debt += 70 reserve units
        Coverage requirement decreased by 100 reserve units
        Net effect on FPR: neutral or positive

Day 30: Borrower loses the 70 reserve units elsewhere, can't repay
        Protocol state: locked=100, debt=70 reserve units (unchanged!)
        
Forever: fTokens stay locked, debt stays on books
         FPR unaffected because locked tokens don't need floor backing
         Protocol has permanent "hostage" collateral
```

**Why LTV only improves over time:**

1. Collateral (fTokens) is valued at floor price $P_f$
2. Floor price is non-decreasing by construction
3. Debt (reserve asset) is fixed (no interest accrual)
4. Therefore: LTV can only decrease as floor rises

$$\text{LTV}(t) = \frac{D}{n \cdot P_f(t)} \leq \frac{D}{n \cdot P_f(0)} = \text{LTV}(0)$$

**Simulation confirmation:** Across all paths over 365 days, simulation confirms **0 bad debt** and **0% insolvency** (see Section 8.7 for full solvency validation).

**Implications for protocol design:**

- No liquidation infrastructure needed
- No cascade risk during market stress
- No procyclical selling pressure
- Loan origination fees (2%) are effectively risk-free revenue
- Conservative LTV (70%) ensures robust solvency buffer

---

**Design Envelope: When "No Liquidation, No Bad Debt" Holds**

> The structural safety properties above hold under these constraints:
>
> | Constraint | Requirement | Relaxation Risk |
> |------------|-------------|-----------------|
> | **Collateral type** | fTokens only | Other collateral (LSTs, stables) can lose value and create bad debt |
> | **Loan denomination** | Reserve asset only (ETH/AVAX) | Non-reserve debt introduces currency risk |
> | **Reserve rehypothecation** | Zero, or negligible-risk strategies only | Yield strategy losses directly impair $L_f$ |
> | **Senior liabilities** | None | External debt creates priority claims on reserves |
>
> Any relaxation of these assumptions reintroduces familiar credit risks and requires separate limits, monitoring, and potentially liquidation infrastructure.
>
> **Production trade-offs:** Real deployments may want to accept other collateral types or deploy reserves into yield strategies. These are valid choices, but they move the protocol back toward traditional risk management. In practice, if governance chooses to accept other collateral types or deploy reserves into risky yield, some liquidation or risk-off mechanisms may be required for those components, even though native fToken loans remain non-liquidatable. The "no bad debt" property is a consequence of the design constraints, not a universal guarantee.

---

### 9.3 Floor Protection Ratio (FPR) as Health Metric

We can turn the solvency invariant into a direct monitoring metric.

Define the Floor Protection Ratio:

$$\text{FPR} = \frac{L_f - D}{P_f S_0}$$

Interpretation:

- $\text{FPR} = 1$: exactly fully backed at the floor, zero buffer.
- $\text{FPR} > 1$: overcollateralized; $\text{FPR} - 1$ is the fractional buffer.
- $\text{FPR} < 1$: insolvent at the stated floor.

Under correct protocol operation (loans issued only when $H \geq \Delta D$, merges only when safe-merge holds), **FPR cannot fall below 1** except through bad debt. This makes FPR a direct measure of cumulative credit losses: if FPR drops toward 1, bad debt has occurred.

Using headroom $H = (L_f - D) - P_f S_0$:

$$\text{FPR} = 1 + \frac{H}{P_f S_0}$$

We can also relate this to:

- Leverage ratio $\lambda = D / L_f$.
- Obligation ratio $\phi = P_f S_0 / L_f$.

The invariant $L_f - D \ge P_f S_0$ is equivalent to:

$$1 - \lambda \ge \phi$$

And:

$$\text{FPR} = \frac{L_f - D}{P_f S_0} = \frac{1 - \lambda}{\phi}$$

So:

- $\text{FPR} \ge 1$ is exactly "solvent at the floor".

Practical target bands:

- Green zone: $\text{FPR} \ge 1.10$.
- Yellow zone: $1.05 \le \text{FPR} < 1.10$.
- Red zone: $\text{FPR} < 1.05$.

These thresholds are illustrative. In practice, they should be calibrated via stress tests, for example:

> Choose a critical threshold $\text{FPR}_{\text{crit}}$ so that in a given stress scenario, the probability that $\text{FPR}$ falls below $\text{FPR}_{\text{crit}}$ over a chosen horizon is less than a target value (for example 1 percent). The Monte Carlo framework in Appendix A can be used to find such thresholds under different volatility regimes.

**Circuit-breaker usage.** Beyond monitoring, FPR can also drive **automatic controls**. A simple rule is:

- If $\text{FPR} < 1.05$ (red zone), **pause new loan origination and LRE**, and optionally increase borrow rates.
- Only resume credit expansion when $\text{FPR}$ returns to a safer band.

This turns FPR into both a health KPI and a direct control variable.

**FPR Policy Grid.** The following table shows how protocol parameters can be dynamically adjusted based on FPR bands:

| FPR Band | Zone | Borrow Fee | Fee to Floor (α_f) | Max LTV | Credit Status |
|----------|------|------------|--------------------| --------|---------------|
| ≥ 1.15 | 🟢 Green+ | 2.0% | 70% | 70% | Full capacity |
| 1.10 – 1.15 | 🟢 Green | 2.0% | 70% | 70% | Normal |
| 1.05 – 1.10 | 🟡 Yellow | 3.0% | 80% | 60% | Reduced capacity |
| 1.00 – 1.05 | 🔴 Red | 5.0% | 90% | 50% | New loans paused |
| < 1.00 | ⚫ Critical | N/A | 100% | 0% | Emergency mode |

**Interpretation:**
- As FPR drops, borrow fees increase (discouraging new debt) and fee-to-floor allocation increases (accelerating floor growth)
- Max LTV decreases to reduce new debt issuance
- Below 1.05, new loans are paused entirely
- Below 1.00 is a breach of the solvency invariant and should never occur under normal operation

The key point is that FPR is a simple, onchain-computable ratio that connects solvency, leverage, and Tier-0 size into a single health metric.

---

## 10. Governance and Mechanism Design

The structural trade-offs outlined above must be encoded into mechanisms, not just policy documents. We sketch three concrete levers.

### 10.1 Algorithmic Borrow Rates Based on Solvency

Borrow APR can be a function of solvency rather than a fixed constant.

One option:

- Use FPR or headroom as input:
  - Let $h = H / (L_f + \varepsilon)$ or use $\text{FPR}$ directly.
  - Borrow rate $r_{\text{borrow}}$ is low when solvency is strong and increases as solvency weakens.

Example shape:

$$r_{\text{borrow}}(\text{FPR}) = r_{\text{min}} + \alpha \cdot \max(0, \text{FPR}_{\text{target}} - \text{FPR})$$

where $\text{FPR}_{\text{target}} > 1$ and $\alpha$ controls slope.

Behavior:

- When FPR is high, credit is cheap and attractive.
- As FPR falls toward critical thresholds, borrowing becomes more expensive, naturally throttling demand.

More aggressive shapes, such as quadratic or exponential penalties as FPR approaches 1, can provide stronger self-correction but may reduce credit availability during moderate stress. The choice of shape is a governance decision.

### 10.2 Headroom Reserves for Merges

Since high credit utilization can stall merges, governance may reserve a portion of headroom specifically for tier absorption:

- **Merge reserve** $H_m$: headroom held back from credit issuance to ensure merges can proceed.
- **Available for credit** $H_c = H - H_m$: headroom that can be consumed by new loans.

Operational rules:

- Loan issuance is capped at $H_c$, not total $H$.
- Merge reserve $H_m$ is sized to cover expected near-term merges: $H_m \geq P_1 \cdot M_1$ for the next pending tier.

This ensures that floor elevation velocity is not sacrificed for credit utilization. The split can be dynamic—for example, $H_m$ could be a function of how close Tier-1 is to merging.

### 10.3 Fee Routing as Monetary Policy

Fee routing parameters act like monetary policy for the floor:

- $\alpha_f$: fraction of fees allocated to $L_f$.
- $\alpha_c$: fraction allocated to other stakeholders (for example governance token, DevCo).
- $\alpha_b$: optional fraction for governance-token buybacks or burns.

Constraints:

$$\alpha_f + \alpha_c + \alpha_b = 1$$

**Simulation used $\alpha_f = 70\%$**, which proved effective across all three market regimes:

| Scenario | Floor Growth |
|----------|--------------|
| Crypto Winter | +5.0% |
| Crab Market | +3.0% |
| Super Cycle | +4.1% |

**Dynamic fee routing recommendation** based on FPR:

| FPR Zone | $\alpha_f$ | Rationale |
|----------|------------|-----------|
| > 1.15 | 50% | Strong solvency; share more with governance |
| 1.05 – 1.15 | 65% | Healthy; maintain current policy |
| < 1.05 | 80% | Weak solvency; prioritize floor reserves |

Changes to $\alpha_f$ should be announced and tied to FPR bands and long-term goals, not to short-term market sentiment.

### 10.4 Oracle-Free Floor as a Governance Asset

The floor is computed from:

- Onchain reserves $L_f$.
- Onchain debt $D$.
- Onchain Tier-0 supply $S_0$.

No external price feed is required to enforce solvency in floor units. For risk managers, this:

- Eliminates a large category of oracle manipulation risk.
- Simplifies reasoning about worst-case behavior in reserve units.

The only oracle exposure arises from the instruments included in $L_f$ if they depend on off-chain or oracle-based valuation. A conservative choice is to keep $L_f$ in base assets and very simple yield sources.

---

## 11. Conclusion

This report has developed a structural risk framework for comparing floor-backed tokens and Liquid Staking Tokens, validated by agent-based Monte Carlo simulation (2,000 heterogeneous agents, 365 days across three market regimes). Four central findings emerge.

First, floor-backed tokens provide **mathematical downside protection** in the reserve numeraire. The floor $P_f = \lfloor(L_f - D)/S_0\rfloor_{\text{tick}}$ is computed programmatically from onchain state, not set by policy. The solvency invariant $L_f - D \geq P_f S_0$ is preserved by construction as long as the protocol enforces safe-merge conditions and manages credit appropriately. Simulation confirms 0% of paths breach FPR < 1.0, with minimum FPR of 1.113 even in -80% drawdown conditions. Floor-relative VaR in the reserve numeraire is zero by design.

Second, the Floor Protection Ratio,

$$\text{FPR} = \frac{L_f - D}{P_f S_0} = 1 + \frac{H}{P_f S_0} = \frac{1 - \lambda}{\phi}$$

emerges as the natural unified solvency metric. It is onchain-computable, directly tied to the invariant, and suitable for real-time monitoring and dynamic policy (see FPR Policy Grid in Section 9.3).

Third, **under the parameter regime studied, fTokens outperform LSTs in all simulated market regimes**:

| Regime | fToken USD | LST USD | fToken Edge | Floor Growth |
|--------|------------|---------|-------------|--------------|
| Super Cycle | +77.0% | +74.4% | +2.6% | +4.1% |
| Crab Market | +8.2% | +7.7% | +0.5% | +3.0% |
| Crypto Winter | -79.0% | -79.5% | +0.5% | +5.0% |

The **counter-cyclical floor** is the key qualitative insight: floor growth is highest in bear markets (+5.0% in Crypto Winter) because panic selling generates more trading volume and fees. The floor rises even as the underlying crashes 80%, providing a natural hedge precisely when it matters most.

Fourth, **the credit facility has no liquidation and no bad debt** under the design envelope constraints (fToken collateral only, reserve-denominated loans, no reserve rehypothecation, no senior liabilities). Relaxing these constraints reintroduces traditional credit risks.

**Model limitations and caveats.** The simulation results are contingent on:
- Trading volume sufficient to generate 3-5% annual floor growth (~14,000 ETH/day in the model)
- LST yield of 2.6% APY (if yields rise to 4-5%, fTokens need higher volume to compete)
- Fee-to-floor allocation of 70% (reducing this weakens floor growth)
- Agent behavioral assumptions that may not match real markets

If volume falls below ~12,000 ETH/day or fee routing is reduced, fTokens can underperform LSTs on raw returns. The depeg statistics (7.6 events/year in Crypto Winter) are model outputs, not historical measurements; real LST behavior may differ. See Section 8.10 for parameter sensitivity analysis and Appendix A.2 for full simulation limitations.

**Allocator guidance.** Under the base parameters:

- fTokens offer superior risk-adjusted returns with counter-cyclical floor growth
- LSTs offer simplicity with no dependency on protocol volume
- The edge is in floor-relative risk and elimination of depeg/liquidation modes—not in USD beta, which is identical for both instruments

For institutional allocators:

- Consider fTokens for risk-adjusted optimization and defensive tranches
- Consider LSTs when simplicity is paramount
- Recognize that fee routing and volume are governance levers, not guarantees
- In USD terms, both instruments carry identical underlying beta—if your mandate is "no underlying beta," neither solves that

For active participants:

- Looping strategies benefit from $\Delta P_f$ tailwind (floor elevation)
- Enter during low-premium periods to minimize basis risk
- Monitor FPR for system health

The agent-based simulation framework and governance mechanisms presented here provide practical tools for protocol designers, risk teams, and allocators who want to adopt floor-backed tokens with clear, quantifiable—but parameter-dependent—guarantees.

---

## 12. Technical Appendix: Invariants and Operations

### 12.1 Redemptions Preserve Solvency

Given:

$$L_f - D \ge P_f S_0$$

consider redemption of 1 fToken at $P_f$.

After redemption:

- $S_0' = S_0 - 1$.
- $L_f' = L_f - P_f$.
- $D' = D$.

Check:

$$L_f' - D' = (L_f - P_f) - D$$
$$P_f S_0' = P_f (S_0 - 1) = P_f S_0 - P_f$$

Subtract:

$$(L_f' - D') - P_f S_0' = (L_f - P_f - D) - (P_f S_0 - P_f) = L_f - D - P_f S_0 = H$$

Headroom is unchanged. If the invariant holds before redemption, it holds after.

### 12.2 Loans Preserve Solvency Under Headroom Check

Given $H \ge 0$, a proposed loan of size $\Delta D$ changes:

- $D' = D + \Delta D$.
- $L_f' = L_f$.
- $S_0' = S_0$.

New headroom:

$$H' = (L_f - (D + \Delta D)) - P_f S_0 = H - \Delta D$$

If the protocol enforces $H' \ge 0$, then $L_f' - D' \ge P_f S_0$ still holds, and solvency is preserved. Credit risk enters only through future changes in $L_f$ and possible write-downs of $D$.

### 12.3 Notes on VaR Assumptions

The VaR comparisons in this paper:

- Use variance-based approximations to compare designs.
- Treat non-Gaussian features (heavy-tailed depegs) at a coarse level.

For institutional-grade analysis, a more complete treatment should:

- Fit return distributions to historical data.
- Include jump and regime-switching dynamics.
- Model depegs, redemption frictions, and unwrapping delays explicitly.
- Run Monte Carlo simulations across correlated assets.

Appendix A provides a concrete simulation framework for such analysis.

---

## Appendix A: Monte Carlo Simulation Framework and Results

This appendix outlines the Monte Carlo framework used to validate the theoretical findings in this report. Simulations were conducted using an agent-based model with 2,000 heterogeneous participants over 365 days across three market regimes, confirming the structural properties of floor-backed tokens.

### A.1 Simulation Summary

| Parameter | Value |
|-----------|-------|
| Agent Count | 2,000 |
| Horizon | 365 days |
| Paths per scenario | 500 |
| Scenarios | 3 (Crypto Winter, Crab Market, Super Cycle) |
| Fee to Floor (α_f) | 70% |
| LTV | 70% |
| LST Benchmark | 2.6% APY |

**Agent Types:**

| Type | Share | Behavior |
|------|-------|----------|
| YieldSeekers | 45% | Core holders seeking stable yield |
| DATAgents | 20% | Value investors buying below fair value |
| LeverageSeekers | 15% | Aggressive traders looping leverage |
| Arbitrageurs | 10% | Short-term traders exploiting inefficiencies |
| FloorHolders | 10% | Long-term holders using floor for capital efficiency |

**Key Results:**

| Finding | Result |
|---------|--------|
| Paths with FPR < 1.0 | 0 (0.0%) |
| Minimum FPR (all scenarios) | 1.113 |
| Counter-cyclical floor growth | Crypto Winter: +5.0% (highest) |
| LST depeg events (Crypto Winter) | 7.6 avg (-38% impact) |
| fToken outperformance | ALL scenarios (total return + risk-adjusted) |

### A.2 Simulation Limitations

The following limitations should be considered when interpreting results:

| Limitation | Description | Impact on Results |
|------------|-------------|-------------------|
| **GBM price process** | Underlying modeled as geometric Brownian motion; no jumps or regime switches | May understate tail risk in extreme scenarios |
| **Agent heuristics** | Agent behaviors are stylized; real market participants may act differently | Volume and fee patterns may vary |
| **Depeg distribution** | Simple per-step probability with fixed shock distribution | Historical depegs may cluster differently |
| **No smart contract failures** | Protocol logic assumed to work correctly | Actual deployments carry implementation risk |
| **Fixed parameters** | Fee rates, LTV, and α_f held constant across regimes | Real governance may adjust parameters dynamically |
| **No gas/friction costs** | Redemption and arbitrage assumed frictionless | Small holders may experience micro-losses |
| **No protocol exploits** | No oracle manipulation, MEV attacks, or governance exploits modeled | Real deployments face adversarial conditions |

**What is not in the model that could hurt this system in reality:**

1. Smart contract bugs that break the solvency invariant
2. Reserve rehypothecation losses (if $L_f$ is deployed into yield strategies that fail)
3. Governance failures or malicious parameter changes
4. Extreme illiquidity preventing redemption arbitrage
5. Coordinated attacks or market manipulation

These limitations do not invalidate the structural findings—the invariant mathematics hold—but they bound the confidence interval around simulation predictions.

### A.3 Objectives

For a given market (for example sAVAX versus fAVAX), estimate:

1. Reserve-denominated VaR for LST and fToken over horizon $T$ at confidence level $\alpha$.
2. Distribution of FPR over time and probability that FPR falls below a critical threshold.
3. Distribution of relative return $R_{\text{LST}} - R_{\text{fToken}}$.
4. Validation that bad debt is structurally impossible for fToken-collateralized loans.

### A.3 Time Grid and Paths

- Horizon $T$ = 365 days (1 year).
- Time step $\Delta t$ = 1 day.
- Number of steps $N = 365$.
- Number of paths $N_{\text{paths}}$ = 500 per scenario.
- Agent count = 2,000 heterogeneous participants.

### A.3 Underlying Price Process

Base model: geometric Brownian motion in USD:

$$\frac{dS_t}{S_t} = \mu dt + \sigma dW_t$$

Discretization:

$$\ln S_{t+\Delta t} = \ln S_t + \left(\mu - \frac{\sigma^2}{2}\right)\Delta t + \sigma \sqrt{\Delta t} Z$$

where $Z \sim N(0, 1)$.

For time steps up to daily $\Delta t \le 1$ day, discretization bias from this scheme is negligible for risk comparisons at the level of detail in this framework. Finer time steps can be used if needed.

Extensions such as jumps or regime switches can be added later.

### A.4 LST Process

State variables:

- Underlying price $S_t$.
- LST index $\text{Index}_t$ (for reward-bearing LSTs).

Reward accrual:

$$\text{Index}_{t+\Delta t} = \text{Index}_t (1 + r \Delta t)$$

where $r$ is annualized staking reward converted to per-step.

Theoretical LST price:

$$P_{\text{LST, theo}}(t) = S_t \cdot \text{Index}_t$$

Depeg model:

- With probability $p_{\text{depeg}}$ per step, sample a depeg shock $D_t$ from a heavy-tailed distribution (for example negative skew, support in $(-d_{\max}, 0)$).
- Apply:
  - If depeg event: $P_{\text{LST}}(t) = P_{\text{LST, theo}}(t) (1 + D_t)$.
  - Otherwise: $P_{\text{LST}}(t) = P_{\text{LST, theo}}(t)$.

Calibration guidance:

- Historical analyses of major LSTs such as stETH suggest depegs in the 2–7 percent range during acute stress, with larger dislocations typically associated with more distressed or illiquid tokens.
- For sAVAX and similar LSTs, there have been fewer major stress events, so conservative assumptions may be appropriate.

A reasonable starting point for a daily model might be: $p_{\text{depeg}} \approx 0.001$ per day and a shock distribution centered around −5 percent with a tail extending to −20 percent. These can then be tuned to match observed behavior.

### A.5 fToken Process (No Credit, First Pass)

State variables per path:

- Floor $P_f(t)$ in AVAX.
- Reserves $L_f(t)$ in AVAX.
- Tier-0 supply $S_0(t)$.
- Headroom $H(t)$.
- Debt $D(t)$, initially set to zero.

Simplifying assumptions in v1:

- All protocol fees are routed to $L_f$ with fixed rate $\alpha_f$.
- For conservative, worst-case VaR analysis, we can approximate the fToken price in AVAX as the floor:

$$P_{\text{fToken}}(t) \approx P_f(t)$$

This produces a lower bound on fToken value and an upper bound on relative VaR versus LSTs.

For more realistic simulations, the premium over the floor can be modeled as a function of:

- Headroom or FPR (higher values imply higher confidence and premium).
- Recent trading volume.
- Distance to the next tier (closer to a merge may justify a higher premium).

These refinements can be added once the base framework is in place.

Fee model:

- Simulate a trading-volume process $V_t$ (for example lognormal, possibly correlated with $|R_U|$).
- Fee rate $f_{\text{trade}}$ on notional volume.
- Per-step reserve inflow:

$$\Delta L_f^{\text{fees}}(t) = \alpha_f f_{\text{trade}} V_t$$

Update:

$$L_f(t+\Delta t) = L_f(t) + \Delta L_f^{\text{fees}}(t)$$

Floor-raise logic (simplified):

1. Compute headroom $H(t) = L_f(t) - D(t) - P_f(t) S_0(t)$.
2. If $H(t) \ge \Delta P \cdot S_0(t)$, then raise floor by one tick:
   - $P_f(t+\Delta t) = P_f(t) + \Delta P$.
   - $H(t+\Delta t) = H(t) - \Delta P S_0(t)$.
3. If new $P_f$ crosses the next tier price in a chosen tier schedule, attempt a merge by adding the corresponding minted capacity $M_i$ to $S_0$ if solvency at the higher price holds.

This discrete-time implementation approximates a tiered floor elevation process. If a harmonic-capacity schedule is desired, $M_i$ can be set as in Appendix B.

### A.6 Portfolio Values and Returns

For each path:

- LST USD value with 1 unit initial notional:

$$V_{\text{LST}}(t) = P_{\text{LST}}(t)$$

- fToken USD value (assuming AVAX floor and no premium in the base case):

$$V_{\text{fToken}}(t) = P_f(t) \cdot S_t$$

Compute returns at horizon $T$:

$$R_{\text{LST}} = \frac{V_{\text{LST}}(T)}{V_{\text{LST}}(0)} - 1,\quad R_{\text{fToken}} = \frac{V_{\text{fToken}}(T)}{V_{\text{fToken}}(0)} - 1$$

Relative return:

$$R_{\text{rel}} = R_{\text{LST}} - R_{\text{fToken}}$$

### A.7 Metrics from the Simulation

From the ensemble of paths:

1. **USD VaR**: For each asset, build empirical distribution of returns and extract quantiles.

2. **Floor behavior**: Track $\text{FPR}(t) = (L_f(t) - D(t)) / (P_f(t) S_0(t))$ along each path. Measure distribution of $\min_t \text{FPR}(t)$. Estimate $\mathbb{P}[\min_t \text{FPR}(t) < \text{FPR}_{\text{crit}}]$ for critical thresholds such as 1.05 or 1.00.

3. **Relative VaR**: Study distribution of $R_{\text{rel}}$, quantifying opportunity cost of choosing fToken over LST.

4. **Failure probability**: Track occurrences where $L_f - D < P_f S_0$ at any time ($\text{FPR} < 1$). These are floor-break events under given parameters.

### A.8 Extension: Internal Credit and Bad Debt

Once the base fToken model is tested, credit can be added:

- Simple loan-demand model driven by volatility and premium of fToken above floor.
- LTV parameter specifying how much can be borrowed per fToken.
- Default model where a fraction of loans becomes unrecoverable when collateral drops below a threshold, with loss-given-default parameter.

On default:

- Reduce $L_f$ and $D$ by loss-given-default times loan size.
- Recompute headroom and FPR.

By running this extended simulation at different combinations of:

- Leverage ratio targets.
- LTVs.
- LGD assumptions.

Risk managers can map out which configurations keep FPR in the green zone across most paths and how often the floor breaks in extreme scenarios.

### A.9 Pseudocode Summary

For implementation teams, the core loop can be summarized as:

```
for path in 1..N_paths:
    initialize S_0, L_f, P_f, D, Index, S_price
    for step in 1..N_steps:
        # 1. Underlying price update (GBM)
        sample Z ~ Normal(0,1)
        log_S_price <- log_S_price
                        + (mu - 0.5 * sigma^2) * dt
                        + sigma * sqrt(dt) * Z
        S_price <- exp(log_S_price)

        # 2. LST index and price
        Index <- Index * (1 + r * dt)
        P_LST_theo <- S_price * Index

        # 3. Depeg event
        sample U ~ Uniform(0,1)
        if U < p_depeg:
            sample D_shock from depeg_distribution
            P_LST <- P_LST_theo * (1 + D_shock)
        else:
            P_LST <- P_LST_theo

        # 4. Fees to floor
        simulate V_t (trading volume)
        L_f <- L_f + alpha_f * f_trade * V_t

        # 5. Headroom and floor raise
        H <- L_f - D - P_f * S_0
        if H >= DeltaP * S_0:
            P_f <- P_f + DeltaP
            H   <- H - DeltaP * S_0
            # Optional: check for tier merge and adjust S_0 via M_i

        # 6. Compute FPR and store
        FPR <- (L_f - D) / (P_f * S_0)
        store FPR, P_LST, P_f, S_price

    # 7. Compute end-of-horizon returns for LST and fToken
    compute R_LST, R_fToken, R_rel for this path
aggregate distributions of R_LST, R_fToken, R_rel, min(FPR), and failure events
```

This pseudocode is intentionally high level. A production implementation should include explicit handling of tier merges, optional fToken premiums, loan origination and default logic, and more detailed fee and volume models.

### A.10 Simulation Results Summary

The following results are from the agent-based simulation (2,000 agents × 365 days × 3 scenarios). **All values in this section are model outputs, not historical measurements.**

**Simulated USD-Denominated Returns (365 days)**

| Scenario | Instrument | Mean Return | VaR (95%) |
|----------|------------|-------------|-----------|
| Super Cycle | fToken USD | +77.0% | -18.7% |
| | LST USD | +74.4% | -18.7% |
| | fToken Floor (ETH) | +4.1% | +2.6% |
| Crab Market | fToken USD | +8.2% | -27.6% |
| | LST USD | +7.7% | -27.6% |
| | fToken Floor (ETH) | +3.0% | +2.3% |
| Crypto Winter | fToken USD | -79.0% | -86.4% |
| | LST USD | -79.5% | -90.4% |
| | fToken Floor (ETH) | +5.0% | +3.0% |

Under the base parameter set (70% fees to floor, ~14,000 ETH/day volume, 2.6% LST yield), fTokens outperform in all simulated scenarios. This result is parameter-dependent.

**Simulated Floor Elevation (365 days)**

| Scenario | Mean Floor Growth | Daily Volume | Supply Growth |
|----------|-------------------|--------------|---------------|
| Super Cycle | +4.1% | 13,624 ETH | +27.3% |
| Crab Market | +3.0% | 14,689 ETH | +26.9% |
| Crypto Winter | +5.0% | 21,079 ETH | +22.5% |

**Counter-cyclical floor:** Floor growth is highest in Crypto Winter (+5.0%) because panic selling drives highest volume (21,079 ETH/day vs 13,624 in bull market).

**Solvency Metrics (Simulated)**

| Scenario | Min FPR (5th %ile) | Final FPR (Mean) | Paths with FPR < 1.0 |
|----------|-------------------|------------------|----------------------|
| Super Cycle | 1.113 | 1.125 | 0.0% |
| Crab Market | 1.113 | 1.122 | 0.0% |
| Crypto Winter | 1.113 | 1.128 | 0.0% |

**FPR Zones:**
- 🟢 Green: FPR ≥ 1.10 (all scenarios maintained this level)
- 🟡 Yellow: 1.05 ≤ FPR < 1.10
- 🔴 Red: FPR < 1.05 (circuit breakers)

**Simulated LST Depeg Events (365 days)**

| Scenario | Mean Events | Annual Impact |
|----------|-------------|---------------|
| Super Cycle | 1.2 | -2.4% |
| Crab Market | 0.4 | -1.2% |
| Crypto Winter | 7.6 | -38% |

*Note: These depeg statistics are model outputs based on a stress-test probability distribution. Historically, top-tier LSTs like stETH have seen 2-7% discounts in acute stress; the -38% cumulative impact in Crypto Winter is a deliberately conservative stress assumption.*

**Simulated Performance Comparison**

| Metric | fToken | LST | Winner |
|--------|--------|-----|--------|
| Total Return (under base params) | Higher | Lower | fToken |
| Sharpe Ratio | Higher | Lower | fToken |
| Max Drawdown | Limited by floor | Unbounded | fToken |
| VaR (95%) | Better | Worse | fToken |
| Tail Risk | Bounded | Unbounded (depeg) | fToken |

**1-Year Comparison Table (Simulated)**

| Metric | Super Cycle | Crab Market | Crypto Winter |
|--------|-------------|-------------|---------------|
| Duration | 365 days | 365 days | 365 days |
| Drift (μ) | +70% | +5% | -80% |
| Volatility (σ) | 70% | 40% | 80% |
| Floor Growth | +4.1% | +3.0% | +5.0% |
| Supply Growth | +27.3% | +26.9% | +22.5% |
| Daily Volume | 13,624 ETH | 14,689 ETH | 21,079 ETH |
| Min FPR (5th) | 1.113 | 1.113 | 1.113 |
| Insolvency | 0.0% | 0.0% | 0.0% |
| fToken USD | +77.0% | +8.2% | -79.0% |
| LST USD | +74.4% | +7.7% | -79.5% |
| Depeg Events | 1.2 | 0.4 | 7.6 |

**The Yield vs. Volume Trade-off:**

LSTs provide a fixed 2.6% yield, while fToken floor growth varies with trading volume:
- Breakeven volume: ~12,000 ETH/day
- Actual volume in simulation: 13,624-21,079 ETH/day
- Result: fToken floor growth (3.0-5.0%) consistently beats LST yield (2.6%)

---

## Appendix B: Asymptotic Tier Scaling and Harmonic Capacity

This appendix contains the more technical analysis of how different tier schedules affect long-run elevation cost.

To avoid confusion with headroom $H$ in the main text, we denote **harmonic numbers** by $\mathcal{H}_n$.

### B.1 Basic Elevation Cost

To raise the floor by a small increment $\Delta P$ at a given Tier-0 supply $S_0$, the required reserve injection is:

$$\Delta L_f = \Delta P \cdot S_0$$

With repeated ticks and merges, cumulative cost is governed by how $S_0$ evolves.

### B.2 Naive Constant-Capacity Tiers Yield $\Theta(m^2)$

Assume:

- Each upper tier has constant minted capacity $C$.
- Each merge fully adds $C$ to Tier-0.

After $i$ merges:

$$S_0(i) = S_{\text{initial}} + i C$$

Marginal cost to complete the $i$-th merge:

$$\text{Cost}_{\text{tier}}(i) \propto \Delta P \cdot S_0(i-1) \propto i$$

Cumulative cost over $m$ merges:

$$\text{TotalCost}(m) \propto \sum_{i=1}^{m} i = \frac{m(m+1)}{2} = \Theta(m^2)$$

Quadratic drag is the direct consequence of linear growth in Tier-0 supply.

### B.3 Harmonic-Capacity Schedule: $O(m \log m)$

Design tiers so that minted capacity absorbed per merge decays harmonically:

$$M_i = \kappa S_{\text{base}} \cdot \frac{1}{i}, \quad i = 1, 2, \dots, m$$

where:

- $M_i$ is minted supply absorbed at the $i$-th merge.
- $S_{\text{base}}$ is baseline Tier-0 size.
- $\kappa$ is a design parameter.

After $i-1$ merges:

$$S_0(i-1) = S_{\text{base}} \bigl(1 + \kappa \mathcal{H}_{i-1}\bigr)$$

with harmonic numbers:

$$\mathcal{H}_n = \sum_{j=1}^{n} \frac{1}{j} \approx \log n + \gamma$$

**Elevation work per merge**

Marginal tick cost at step $i$:

$$\text{TickCost}(i) = \Delta P \cdot S_0(i-1) = \Delta P S_{\text{base}} \bigl(1 + \kappa \mathcal{H}_{i-1}\bigr)$$

Sum:

$$\sum_{i=1}^{m} \text{TickCost}(i) = \Delta P S_{\text{base}} \left( m + \kappa \sum_{i=1}^{m} \mathcal{H}_{i-1} \right)$$

Using $\sum_{i=1}^{m} \mathcal{H}_{i-1} = m \mathcal{H}_m - m = \Theta(m \log m)$:

$$\sum_{i=1}^{m} \text{TickCost}(i) = \Theta\bigl(\Delta P S_{\text{base}} m \log m\bigr)$$

**Coverage cost per merge**

Safe merge at price $P_1$ requires:

$$L_f - D \ge P_1 (S_0 + M_i)$$

Coverage cost for $M_i$:

$$\text{CoverageCost}(i) \approx P_1 M_i \approx P_1 \kappa S_{\text{base}} \frac{1}{i}$$

Sum:

$$\sum_{i=1}^{m} \text{CoverageCost}(i) \approx P_1 \kappa S_{\text{base}} \sum_{i=1}^{m} \frac{1}{i} = \Theta\bigl(P_1 \kappa S_{\text{base}} \log m\bigr)$$

**Total work**

$$\text{TotalWork}(m) = \Theta\bigl(\Delta P S_{\text{base}} m \log m\bigr)$$

The dominant term is $m \log m$, a strict improvement over the $m^2$ regime.

### B.4 Interpretation

The contrast is:

- Constant-capacity tiers: Tier-0 grows linearly, elevation cost scales as $\Theta(m^2)$.
- Harmonic-capacity tiers: Tier-0 grows like $S_{\text{base}}(1 + \kappa \log m)$, elevation cost scales as $O(m \log m)$.

For a protocol targeting, say, 50 merges over its lifetime, a rough comparison of the dominant terms shows:

$$\frac{m \log m}{m^2 / 2} \bigg|_{m=50} \approx 0.15$$

So, in asymptotic terms, a harmonic schedule can require on the order of 15 percent of the elevation capital that a constant-capacity schedule would need to reach a similar number of merges. The exact ratio depends on parameter choices, but the qualitative advantage is clear.

This does not guarantee "free" floor growth, but it moves the system from a structurally prohibitive regime (quadratic drag) to a more manageable one. Combined with careful headroom and FPR governance, harmonic-capacity tiers give floor-backed designs a credible long-run path.

---

## Appendix C: Notation Glossary

| Symbol | Definition |
|--------|------------|
| $L_f$ | Floor reserves allocated to Tier-0 (in the reserve asset, for example AVAX). |
| $D$ | Outstanding debt from internal loans against fToken collateral. |
| $S_0$ | Tier-0 fToken supply. |
| $P_f$ | Floor price in reserve units per fToken; computed as $P_f = \lfloor(L_f - D)/S_0\rfloor_{\text{tick}}$. |
| $H$ | Headroom: $H = (L_f - D) - P_f S_0$. |
| $\text{FPR}$ | Floor Protection Ratio: $\text{FPR} = (L_f - D)/(P_f S_0)$. |
| $\lambda$ | Leverage ratio: $\lambda = D / L_f$. |
| $\phi$ | Obligation ratio: $\phi = P_f S_0 / L_f$. |
| $\delta$ | Premium: $\delta = P_{\text{spot}} - P_f$, the spread between spot price and floor. |
| $\Delta \delta$ | Premium delta: change in premium over a holding period. |
| $\Delta P_f$ | Floor elevation: change in floor price over a holding period. |
| $\text{LTV}_f$ | Loan-to-value ratio applied to floor credit in native lending. |
| $R_{\text{loop}}$ | Return from a looped fToken position. |
| $k$ | Effective leverage multiplier in a looped position. |
| $S_t$ | Underlying asset price at time $t$ (for example AVAX/USD). |
| $\text{Index}_t$ | LST index capturing accumulated staking rewards. |
| $P_{\text{LST}}$ | Market price of the LST. |
| $P_{\text{LST, theo}}$ | Theoretical LST price without depeg: $S_t \cdot \text{Index}_t$. |
| $\Delta e$ | Depeg shock for LST (premium or discount relative to staking-implied value). |
| $r$ | Annualized staking reward rate for the underlying. |
| $r_{\text{borrow}}$ | Borrow rate for internal fToken credit. |
| $\mu$ | Drift parameter of the underlying price process (in GBM). |
| $\sigma$ | Volatility parameter of the underlying price process (in GBM). |
| $\Delta t$ | Time step in the discretized Monte Carlo simulation. |
| $V_t$ | Trading volume used to generate protocol fee revenue at time $t$. |
| $f_{\text{trade}}$ | Fee rate on trading volume. |
| $\alpha_f$ | Fraction of protocol fees routed to floor reserves. |
| $\alpha_c$ | Fraction of protocol fees routed to other stakeholders (for example governance token, DevCo). |
| $\alpha_b$ | Fraction of protocol fees used for buybacks or burns of governance tokens. |
| $\Delta P$ | Tick size for floor price increments. |
| $C_i$ | Capacity or collateral associated with tier or user $i$, depending on context. |
| $M_i$ | Minted supply absorbed into Tier-0 when tier $i$ is merged; harmonic schedule uses $M_i = \kappa S_{\text{base}}/i$. |
| $\kappa$ | Dimensionless parameter controlling aggressiveness of Tier-0 growth in the harmonic schedule. |
| $S_{\text{base}}$ | Baseline Tier-0 size used as reference in harmonic-capacity design. |
| $\mathcal{H}_n$ | $n$-th harmonic number: $\mathcal{H}_n = \sum_{j=1}^{n} 1/j$. |
| $R_{\text{LST}}$ | Return of the LST over the simulation horizon. |
| $R_{\text{fToken}}$ | Return of the fToken over the simulation horizon. |
| $R_{\text{rel}}$ | Relative return: $R_{\text{rel}} = R_{\text{LST}} - R_{\text{fToken}}$. |
| $p_{\text{depeg}}$ | Per-step probability of an LST depeg event in the Monte Carlo model. |
| $d_{\max}$ | Maximum magnitude of a depeg shock in the depeg distribution. |
| $\text{LGD}$ | Loss-given-default parameter for internal credit in extended simulations. |

---
