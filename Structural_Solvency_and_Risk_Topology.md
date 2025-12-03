# Structural Solvency and Risk Topology

## A Comparative Value-at-Risk Analysis of Floor-Backed Tokens (fTOKENs) Versus Liquid Staking Tokens (LSTs)

---

## 1. Executive Abstract

The maturation of Decentralized Finance (DeFi) has created a split in asset design between:

1. **Stochastic yield-bearing instruments**, represented by Liquid Staking Tokens (LSTs).
2. **Deterministic, structured instruments**, represented by floor-backed tokens (fTOKENs).

This report develops a first-principles risk framework comparing these two classes, focusing on Value-at-Risk (VaR), solvency mechanics, and the practical behavior of floor-backed protection under stress.

We discuss Tier-0 mechanics for fTOKENs. Under this specification, the floor is not a passive redemption facility but a live trading tier that must be fully backed at all times, independent of lock states. This reframes the floor as an internal full-reserve micro-economy and makes solvency and governance questions precise.

On the LST side, instruments such as stETH and sAVAX provide efficient exposure to underlying staking yield with full participation in market beta. Their core risks are:

- Market beta of the underlying asset.
- Liquidity-driven depeg risk in secondary markets.
- Slashing and validator concentration risk.
- Smart-contract risk in wrapper contracts.

On the fTOKEN side, instruments such as fAVAX and fETH attempt to structurally censor downside tail risk at the protocol level by enforcing a minimum price $P_f$ tied to reserves $L_f$ and Tier-0 supply $S_0$ through a solvency invariant. The return distribution is **structurally truncated** on the downside: the left tail is cut off at $P_f$ as long as the invariant holds. The floor is endogenous and oracle-free; no external price feed is needed to compute solvency.

A naive implementation with constant tier capacities above the floor can make the floor increasingly heavy as the system scales, causing floor growth to slow or stagnate. We show that tier design is the key degree of freedom. By carefully choosing how much new supply is absorbed when tiers merge, protocols can keep floor elevation economically sustainable. The detailed scaling analysis and a harmonic-capacity tier schedule that improves long-run behavior are provided in Appendix B.

Several important caveats remain:

- A floor denominated in AVAX or ETH protects value in units of the underlying, not in USD. For institutional allocators, USD VaR and cross-asset correlation matter.
- Floor-relative VaR is zero by construction in the reserve numeraire, but operational frictions (gas costs, redemption queues) can create micro-losses. If reserves are rehypothecated into yield strategies, those strategies' risks enter the floor's backing.
- Credit issuance against the floor cannot break solvency by itself, but **bad debt** (unrecoverable loans) directly impairs reserves and is the only path to invariant violation absent smart contract failure.

Within these constraints, floor-backed tokens are structurally better suited than LSTs for defensive tranches and high-quality collateral, while LSTs remain superior for pure beta and maximum upside capture. We propose concrete design levers:

- A Floor Protection Ratio (FPR) as the main solvency metric.
- Headroom reserves to ensure tier merges are not stalled by credit utilization.
- Fee-routing and liquidity-reallocation policies that maintain floor elevation velocity over long horizons.

We close with a Monte Carlo simulation framework that can be used by risk teams to quantify VaR and failure probabilities in practice.

---

## 2. Introduction: From Yield Tokens To Engineered Floors

Digital Asset Treasuries (DATs) and funds with ETH or AVAX mandates increasingly want three things at once:

1. **Native, asset-denominated yield** rather than idle holdings.
2. **Structural downside mitigation** that goes beyond "HODL and hope".
3. **Re-usable collateral** that can safely support leverage or credit lines without fragile liquidation waterfalls.

Today, the default implementation of this bundle is staked assets via Liquid Staking Tokens (LSTs) such as stETH or sAVAX. LSTs are efficient wrappers around validator yield. They maintain near-par exposure to the underlying asset, pass through staking rewards, and are highly composable in DeFi. For many treasuries, "own the LST" is the baseline expression of an ETH or AVAX mandate.

Floor-backed tokens (fTOKENs) start from a different objective. Instead of accepting the full left tail of the underlying and simply adding yield on top, they try to **reshape the payoff profile**:

- Introduce a **non-decreasing floor**, computed from onchain reserves net of debt.
- Define **borrowing capacity against that floor**, not against volatile spot.
- Use fee flows and conservative yield to **ratchet the floor upward over time**.

In the ETH context, this gives you two structurally distinct building blocks:

- LSTs like stETH for **maximal beta and staking yield**.
- fETH for **ETH-denominated downside censorship, liquidation-free credit, and programmable exposure** (staked fETH as a yield asset; locked fETH as credit collateral).

A similar dichotomy exists on Avalanche between sAVAX and fAVAX.

This paper is about the **risk topology** that emerges when you put these two classes of instruments side by side. Rather than arguing that one dominates the other, we treat LSTs and fTOKENs as **complementary tools** and focus on three questions:

1. How do their **Value-at-Risk (VaR)** profiles differ in the underlying asset numeraire and in USD?
2. What are the **solvency mechanics** of a floor that is implemented as a live trading tier instead of a best-effort redemption promise?
3. Which governance and design levers matter most if treasuries intend to use fTOKENs as a defensive or senior tranche in their stack?

### 2.1 The Stochastic LST Regime

Liquid Staking Tokens such as stETH and sAVAX wrap validator positions and expose holders to:

- The full price path of the underlying token.
- Staking rewards minus penalties and fees.
- Liquidity and smart-contract risks introduced by the wrapper and its secondary markets.

In normal conditions, LSTs behave like "underlying plus yield". In stress, they behave like **levered beta on the underlying** with an additional depeg channel through AMM liquidity and withdrawal queues. From a risk perspective, they are well suited to treasuries that want to maximize upside participation and can tolerate drawdowns on the underlying.

### 2.2 The Engineered fTOKEN Regime

Floor-backed tokens take the opposite tack. They define:

1. A **floor price** $P_f$ enforced by protocol rules on the primary market.
2. **Floor reserves** $L_f$ and Tier-0 supply $S_0$ such that the system can always redeem Tier-0 tokens at $P_f$ as long as a simple invariant holds.
3. **Routing of trading and borrowing fees** into these reserves so that $P_f$ rises in discrete steps when headroom allows.

Two properties follow:

- **Downside relative to the floor is structurally censored** in the reserve numeraire as long as the solvency invariant is respected.
- **Upside is partially reinvested into structural protection**, since fee flows that could have accrued fully to holders are instead used to strengthen reserves and lift the floor.

Where LSTs turn staking yield into higher expected returns with unchanged downside shape, fTOKENs **turn protocol activity into thicker downside protection** and more predictable collateral behavior.

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

## 4. Architectural Deconstruction of fTOKENs (Tier-0 Analysis)

We now deconstruct the floor-backed design using the corrected Tier-0 mechanics.

### 4.1 Tier-0 as a Live Trading Floor

In an fTOKEN market:

- Tier-0 is the floor tier, quoted at price $P_f$.
- It is a live market tier on the bonding curve, not a special emergency mode.
- Tier-0 supply $S_0$ includes all fTOKENs at the floor, whether locked or liquid.

Coverage requirement:

- For every fTOKEN in Tier-0, the protocol must be able to pay $P_f$ units of the reserve asset on redemption without violating solvency. Locking does not relieve this requirement.

This is the key conceptual shift. The floor is an active, fully-backed micro-economy, not a best-effort exit.

### 4.2 The Solvency Invariant

The solvency invariant is:

$$L_f - D \ge P_f S_0$$

Where:

- $L_f$: reserves allocated to backing Tier-0.
- $D$: outstanding debt from internal borrowing against fTOKEN collateral.
- $P_f$: floor price in reserve units per fTOKEN.
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

We now compare LSTs and fTOKENs through a VaR lens and address the choice of numeraire directly.

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

### 5.2 fTOKEN Structural VaR (Floor-Denominated)

In an fTOKEN market, the floor is not a policy parameter but a **programmatic computation** from onchain state:

$$P_f = \left\lfloor \frac{L_f - D}{S_0} \right\rfloor_{\text{tick}}$$

As long as:

- The solvency invariant $L_f - D \geq P_f S_0$ holds, and
- Redemptions are possible within operational constraints,

the market price in reserve units should satisfy:

$$P_{\text{fTOKEN}}(t) \geq P_f(t)$$

If we take reserve units as numeraire, the downside in that numeraire is censored at the floor:

$$\text{VaR}_{\text{fTOKEN}}^{\text{downside, floor-numeraire}} \to 0$$

This is not an approximation or a soft guarantee—it is a mathematical consequence of the invariant. Relative to $P_f$, losses in reserve units are eliminated by construction.

**What can impair floor-relative VaR?**

The floor is immune to spot price movements, but a small set of risks can still affect value in reserve units:

1. **Smart contract risk.** Bugs in the protocol logic could break the invariant or block redemptions.

2. **Reserve rehypothecation.** If $L_f$ is deployed into yield strategies (e.g., staking the reserve asset), those strategies carry their own risks—slashing, smart contract failure, illiquidity. A loss in the rehypothecated portion directly reduces $L_f$ and can impair solvency. For protocols that keep $L_f$ in the base asset without rehypothecation, this risk is absent.

3. **Bad debt.** If internal loans become unrecoverable, the write-off reduces $(L_f - D)$ and can push the system below the solvency threshold.

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

$$V_{\text{fTOKEN, USD}}(t) = P_f(t) \cdot P_{\text{AVAX}\rightarrow \text{USD}}(t)$$

Even if $P_f(t)$ rises over time, USD value remains sensitive to AVAX/USD.

For USD-centric risk control, three options exist:

1. Accept AVAX beta and treat fAVAX as an AVAX-denominated defensive asset that improves risk-adjusted returns in AVAX units.
2. Hedge AVAX/USD externally (for example via futures or options) and hold fAVAX as the protected AVAX leg.
3. Design USD-floor fTOKENs by combining AVAX reserves with explicit hedging (perps, options). This yields a more complex structured note and sits somewhat outside a simple LST versus fTOKEN comparison.

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

A full VaR model for fTOKENs should:

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

- fTOKENs remain highly correlated with their underlying over long horizons, especially if the floor is denominated in the same asset.
- Floor protection mainly improves lower-tail behavior (reduced severity of drawdowns) rather than creating uncorrelated returns.
- Correlation between an LST and the fTOKEN of the same underlying is likely close to 1 in normal regimes and may diverge somewhat in stress when floor dynamics and depegs differ.

Portfolio-level VaR therefore benefits from:

- Lower marginal tail risk of fTOKENs.
- Better behavior under internal leverage (non-liquidatable positions; see Section 7).
- Not from major decorrelation compared to the underlying.

Appendix A outlines a Monte Carlo framework that can quantify these effects.

### 5.6 Entry Basis and Premium Risk

So far the analysis has been floor-relative. For an actual investor, **entry price relative to the floor** is a distinct risk dimension.

In practice, healthy fTOKEN markets trade at a **premium** to the floor. For example, if $P_f = 1.00$ and the market price is $1.10$, a new buyer at 1.10 faces immediate downside to 1.00. Their near-term floor-relative VaR is 9 percent in the reserve numeraire, even though the floor itself is non-decreasing.

Two implications follow:

- Floor-relative VaR in the reserve numeraire may be close to zero, but **investor VaR around their entry basis is not**. A treasurer who must mark to a 3-month horizon cares about the spread between entry price and $P_f$, not only about the existence of the floor.
- fTOKENs are **best suited to long-term collateral and defensive sleeves**, where the expectation is that the floor will eventually catch up with, and then exceed, the entry premium. They are less suitable as short-term trading vehicles for investors who might need to exit while the premium is still volatile.

A risk-conscious allocator should therefore:

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

A VaR model for fTOKENs in a live deployment should therefore treat both **revenue injection** and **liquidity reallocation** as floor drivers, with governance parameters controlling how aggressive LRE can be.

---

## 7. Native Credit as a Strategic Asset

The discussion of headroom and debt so far has focused on system-level risk mechanics. But native credit in fTOKEN systems is not merely a risk to manage—it is a distinct value proposition with no direct analogue in the LST stack. This section makes the strategic case explicit.

### 7.1 The Liquidation Problem in External DeFi Lending

When an LST holder wants leverage, they typically deposit their LST into an external lending protocol (Aave, Compound, Benqi, etc.) and borrow against it. The protocol values the collateral at spot and enforces a Loan-to-Value (LTV) ratio, typically 70–80% for major LSTs.

If the underlying asset falls, the collateral's USD value drops, and the position approaches liquidation. During acute drawdowns:

- Liquidations cascade as forced selling pushes prices lower.
- LST depegs compound the problem—collateral loses value both from underlying beta and from the depeg itself.
- Borrowers who cannot top up collateral are liquidated at the worst possible time.
- Protocol-level bad debt can accumulate if liquidations fail to cover loans.

This creates a **procyclical liquidation waterfall**: precisely when holders most need their positions to survive, external lending mechanics force them to sell or be sold.

### 7.2 Floor Credit: The Native Innovation

In an fTOKEN system, native credit is denominated against the **floor**, not against volatile spot. This is the core structural innovation.

For a position holding $n$ fTOKENs:

$$\text{Native Borrowing Capacity} = \text{LTV}_f \cdot n \cdot P_f$$

The collateral reference is the floor price $P_f$, which is **computed programmatically** from onchain state:

$$P_f = \left\lfloor \frac{L_f - D}{S_0} \right\rfloor_{\text{tick}}$$

The floor is not "set" by governance or policy—it is a mathematical consequence of reserves, debt, and supply. This changes the risk topology fundamentally:

**No spot-driven liquidation.** A drop in the underlying's USD price—or a compression of the premium above the floor—does not affect the solvency invariant. The invariant $L_f - D \geq P_f S_0$ depends only on reserves, debt, and Tier-0 supply, none of which move with spot.

**Floor only moves up.** Because the floor is derived from $(L_f - D)/S_0$, and because $L_f$ grows from fee inflows while $S_0$ grows only through merges (which require coverage checks), the floor is structurally non-decreasing absent bad debt.

**Credit against floor cannot break solvency.** When fees are deployed to $L_f$ and the floor rises, each token's borrowing capacity increases proportionally. New loans reduce headroom $H = (L_f - D) - P_f S_0$, but as long as the protocol only issues credit when $H \geq \Delta D$, the solvency invariant is preserved by construction. Credit issuance is bounded by available headroom—it cannot consume more than exists.

**Insolvency requires bad debt.** The only path to $L_f - D < P_f S_0$ is unrecoverable debt: a borrower defaults and the loss must be written off against reserves. This is why LTV discipline, collateral quality, and credit caps matter—not because credit *competes* with floor raises, but because bad debt directly impairs the invariant.

### 7.3 The Premium Is Not Collateral (In Native Credit)

A critical point: native fTOKEN credit does **not** allow borrowing against the premium $\delta = P_{\text{spot}} - P_f$. The premium represents market value above the floor, but it is volatile and not part of the native collateral base.

If a holder wants to lever against the full spot value of their fTOKEN (including the premium), they must take their fTOKEN to an **external money market** and borrow against spot price. In that case:

- The external protocol values collateral at $P_{\text{spot}}$, not $P_f$.
- If spot falls toward the floor, the position approaches liquidation.
- The holder reintroduces all the liquidation risks that native credit was designed to avoid.

This is a deliberate design boundary. Native credit provides **unconditional stability** in floor units precisely because it ignores the volatile premium. Holders who want more aggressive leverage can access it externally, but they accept a different risk profile.

### 7.4 Native Looping: Amplified Exposure with Structural Protection

One of the most powerful applications of native credit is **looping**: borrowing against fTOKEN collateral at the floor, using the proceeds to acquire more fTOKENs, and repeating. This amplifies exposure to fTOKEN performance while maintaining floor-denominated safety.

The profitability of a looped position over a holding period depends on three factors:

**1. Premium Delta ($\Delta \delta$)**

If the premium expands (spot rises faster than the floor), the looped position gains on the additional fTOKENs acquired. If the premium compresses, gains are reduced or reversed. Premium volatility is the main short-term driver of loop returns.

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

fTOKEN looping, by contrast, allows leveraged exposure while maintaining a structural floor. A looper cannot be liquidated by spot movements alone—only by floor insolvency, which is a system-level event governed by FPR.

### 7.5 Strategic Use Cases

The floor-only credit structure enables several applications that are difficult or dangerous with spot-based external lending:

**Treasury leverage without liquidation exposure.** A DAO treasury or fund holding fTOKEN can borrow against floor value to fund operations, make investments, or meet redemptions—without the risk that a market downturn forces a fire sale of core holdings. The treasury retains its fTOKEN position through any volatility that doesn't breach the floor.

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

Native fTOKEN credit is floor credit only—and that constraint is precisely what makes it valuable. By refusing to collateralize the volatile premium, native credit provides unconditional stability that external lending cannot match.

| Dimension | LST + External Lending | fTOKEN + Native Credit |
|-----------|------------------------|------------------------|
| Collateral reference | Spot price (volatile) | Floor price (non-decreasing) |
| Floor computation | N/A | $P_f = \lfloor(L_f - D)/S_0\rfloor_{\text{tick}}$ |
| Liquidation trigger | Spot drawdown | Never (only bad debt causes insolvency) |
| Cascade risk | High (correlated liquidations) | None (no spot-driven liquidations) |
| Leverage tailwind | None | Floor elevation ($\Delta P_f$) |
| Premium as collateral | Yes (full spot exposure) | No (premium excluded) |
| Insolvency path | Spot crash + failed liquidations | Bad debt only |
| VaR in reserve units | Spot volatility + depeg | Zero (modulo SC risk, rehypothecation) |

For treasuries and allocators who value predictable leverage and cannot tolerate forced selling, native credit may be as important as the floor itself. For active participants, the floor elevation tailwind ($\Delta P_f$) makes looping strategies viable over horizons where external LST loops would be too risky to sustain.

---

## 8. Comparative Scenario Analysis

We now compare sAVAX and fAVAX across stylized regimes and illustrate behavior with a simple worked example.

### 8.1 Crypto Winter: AVAX Drops 75 Percent

Assume:

- AVAX price falls from 100 USD to 25 USD.
- Staking yield is small relative to this move.

**sAVAX**

- Tracks AVAX nearly one to one in USD, plus a small yield.
- Approximate final value: 250,000 USD per 1,000,000 USD of initial exposure.

**fAVAX with AVAX-denominated floor**

- Suppose the floor starts at $P_f = 1.0$ AVAX and rises to $P_f = 1.2$ AVAX before the crash.
- At 25 USD/AVAX, the floor is 30 USD per fAVAX.
- Compared to holding AVAX directly, the user ends with more AVAX but at a lower price.

Both positions suffer large USD losses. fAVAX improves outcomes in AVAX units and eliminates liquidation risk in internal credit, but it does not stabilize USD value.

### 8.2 Crab Market: Sideways, Low Volume

Assume:

- AVAX trades around 100 USD in a narrow band.
- Trading volume is modest.

**sAVAX**

- Earns staking yield in the 5–7 percent APY range.
- VaR is moderate, dominated by price noise.

**fAVAX**

- Relies on trading and borrowing fees plus any LRE to raise $P_f$.
- With low fees and limited premium, floor growth may be slow or flat.
- If headroom is heavily allocated to credit, elevation may be deprioritized.

In this regime, LSTs generally win on total return. fAVAX still functions as strong collateral and a low-volatility AVAX exposure in floor units, but its implicit "tax" on upside to fund floor elevation is less rewarded.

### 8.3 Super Cycle: High Volatility, Uptrend

Assume:

- AVAX rallies from 100 USD to 400 USD.
- Volatility and volume are high.

**sAVAX**

- Participates fully in the 4x move plus yield.
- Hard to beat on raw ROI.

**fAVAX**

- Participates in AVAX upside.
- Routes a portion of trading and borrowing PnL into $L_f$.
- Potentially uses LRE to pull some profits from high tiers down to the floor.
- Over time, $P_f$ ratchets upward, thickening Tier-0 and providing protection against later drawdowns.

On raw ROI, sAVAX likely outperforms, since it does not divert upside. On risk-adjusted metrics, fAVAX can look better:

- Lower drawdowns in reserve units.
- Non-liquidatable leverage against the floor.
- More predictable collateral behavior.

### 8.4 Worked Example: Intuition for Tier Growth

Consider a simple illustrative example:

- Baseline Tier-0 size $S_{\text{base}} = 1{,}000{,}000$ fAVAX.
- Tick size $\Delta P = 0.01$ AVAX.
- No debt.
- We imagine 10 successive merges.

Under a naive scheme where each merge adds a fixed 100,000 new fAVAX to Tier-0, Tier-0 ends at 2,000,000 fAVAX. Every additional tick at that point costs roughly twice as many AVAX reserves as at the start.

Under a more conservative scheme where higher tiers add progressively less new supply (for example harmonic capacities), Tier-0 might still grow significantly but in a way that keeps the cost of future elevation from exploding.

The detailed formulae and an explicit harmonic schedule are provided in Appendix B. The main point for risk and product teams is that:

> How much new supply is allowed into Tier-0 at each merge is a core economic parameter.

---

## 9. Endogenous Credit Risk: Headroom, Debt, and Fragility

Loans against fTOKEN collateral are not external; they enter the solvency invariant through $D$. This concentrates credit risk.

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

### 9.2 Bad Debt: The Only Path to Insolvency

Credit issuance, by itself, cannot break the solvency invariant—it merely consumes available headroom. The **only** mechanism by which internal credit can cause insolvency is **bad debt**: loans that become unrecoverable.

If a borrower defaults and the collateral cannot be liquidated for full value, a portion of $D$ must be written off. In floor-backed designs, this write-off hits reserves directly:

$$L_f \to L_f - \Delta D_{\text{bad}}, \quad D \to D - \Delta D_{\text{bad}}$$

Net effect on headroom:

$$H \to H - \Delta D_{\text{bad}}$$

If the cumulative bad debt is large enough:

$$L_f - D < P_f S_0$$

the system is mathematically insolvent at the stated floor. The protocol then faces undesirable choices:

- Reduce the floor (breaking the non-decreasing guarantee).
- Impose haircuts or other emergency measures.
- Recapitalize $L_f$ from external sources.

Because bad debt is the singular path to insolvency (absent smart contract failure), credit risk must be tightly controlled:

- **Conservative LTVs** that leave buffer even if collateral value drops.
- **Credit caps** that bound total $D$ relative to $L_f$.
- **Liquidation of external collateral** (if any) before losses hit the floor.
- **Insurance or reserve buffers** to absorb small losses without impairing the floor.

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

Regime guidance:

- High-growth, early regime: set $\alpha_f$ high to build reserves and push FPR well above 1.
- Mature regime: lower $\alpha_f$, increase $\alpha_c$ and possibly $\alpha_b$ to share more revenue.

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

This report has developed a structural risk framework for comparing floor-backed tokens and Liquid Staking Tokens, with four central conclusions.

First, floor-backed tokens provide **mathematical downside protection** in the reserve numeraire. The floor $P_f = \lfloor(L_f - D)/S_0\rfloor_{\text{tick}}$ is computed programmatically from onchain state, not set by policy. The solvency invariant $L_f - D \geq P_f S_0$ is preserved by construction as long as the protocol enforces safe-merge conditions and issues credit only against available headroom. Floor-relative VaR in the reserve numeraire is zero by design, with residual risks limited to smart contract failure, reserve rehypothecation losses (if any), and bad debt.

Second, the Floor Protection Ratio,

$$\text{FPR} = \frac{L_f - D}{P_f S_0} = 1 + \frac{H}{P_f S_0} = \frac{1 - \lambda}{\phi}$$

emerges as the natural unified solvency metric. It is onchain-computable, directly tied to the invariant, and suitable for real-time monitoring and policy. Combined with Monte Carlo calibration, FPR bands and circuit-breaker rules provide a concrete way to define green, yellow, and red regimes for the system.

Third, native credit is denominated against the floor only—and this design makes it structurally safe. Credit issuance consumes headroom but cannot break the solvency invariant; only bad debt can cause insolvency. This enables non-liquidatable leverage for treasuries and allocators, and looping strategies where the floor elevation tailwind ($\Delta P_f$) provides a structural advantage unavailable to LST-based loops. The governance trade-off is between credit utilization and floor elevation velocity, not between credit and solvency.

Fourth, tier design determines long-term viability. With naive constant-capacity tiers, Tier-0 becomes heavy and floor elevation cost scales as $\Theta(m^2)$. With harmonic-capacity schedules, elevation cost scales as $O(m \log m)$, keeping floor progression economically feasible over many merges. Combined with fee routing and headroom governance, tier design determines whether the floor remains a living mechanism or ossifies at a fixed level.

In this light, LSTs and fTOKENs occupy distinct roles in a portfolio:

- LSTs are best suited for pure beta and yield, where the objective is to track or outperform the underlying.
- fTOKENs are best suited for defensive tranches, high-quality collateral, and structures that require non-liquidatable leverage and predictable lower bounds.

The Monte Carlo framework and governance mechanisms presented here are intended as practical tools for protocol designers, risk teams, and allocators who want to adopt floor-backed tokens with clear, quantifiable guarantees.

---

## 12. Technical Appendix: Invariants and Operations

### 12.1 Redemptions Preserve Solvency

Given:

$$L_f - D \ge P_f S_0$$

consider redemption of 1 fTOKEN at $P_f$.

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

## Appendix A: Monte Carlo Simulation Framework

This appendix outlines a Monte Carlo framework that risk teams (internal or external, such as Gauntlet or Chaos Labs) can use to quantify VaR and floor failure probabilities.

### A.1 Objectives

For a given market (for example sAVAX versus fAVAX), estimate:

1. USD VaR for LST and fTOKEN over horizon $T$ at confidence level $\alpha$.
2. Distribution of FPR over time and probability that FPR falls below a critical threshold.
3. Distribution of relative return $R_{\text{LST}} - R_{\text{fTOKEN}}$.
4. Sensitivity of floor solvency to bad-debt shocks and different leverage regimes.

### A.2 Time Grid and Paths

- Horizon $T$ (for example 30 or 90 days).
- Time step $\Delta t$ (for example 1 hour or 1 day).
- Number of steps $N = T / \Delta t$.
- Number of paths $N_{\text{paths}}$ (for example 10,000).

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

### A.5 fTOKEN Process (No Credit, First Pass)

State variables per path:

- Floor $P_f(t)$ in AVAX.
- Reserves $L_f(t)$ in AVAX.
- Tier-0 supply $S_0(t)$.
- Headroom $H(t)$.
- Debt $D(t)$, initially set to zero.

Simplifying assumptions in v1:

- All protocol fees are routed to $L_f$ with fixed rate $\alpha_f$.
- For conservative, worst-case VaR analysis, we can approximate the fTOKEN price in AVAX as the floor:

$$P_{\text{fTOKEN}}(t) \approx P_f(t)$$

This produces a lower bound on fTOKEN value and an upper bound on relative VaR versus LSTs.

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

- fTOKEN USD value (assuming AVAX floor and no premium in the base case):

$$V_{\text{fTOKEN}}(t) = P_f(t) \cdot S_t$$

Compute returns at horizon $T$:

$$R_{\text{LST}} = \frac{V_{\text{LST}}(T)}{V_{\text{LST}}(0)} - 1,\quad R_{\text{fTOKEN}} = \frac{V_{\text{fTOKEN}}(T)}{V_{\text{fTOKEN}}(0)} - 1$$

Relative return:

$$R_{\text{rel}} = R_{\text{LST}} - R_{\text{fTOKEN}}$$

### A.7 Metrics from the Simulation

From the ensemble of paths:

1. **USD VaR**: For each asset, build empirical distribution of returns and extract quantiles.

2. **Floor behavior**: Track $\text{FPR}(t) = (L_f(t) - D(t)) / (P_f(t) S_0(t))$ along each path. Measure distribution of $\min_t \text{FPR}(t)$. Estimate $\mathbb{P}[\min_t \text{FPR}(t) < \text{FPR}_{\text{crit}}]$ for critical thresholds such as 1.05 or 1.00.

3. **Relative VaR**: Study distribution of $R_{\text{rel}}$, quantifying opportunity cost of choosing fTOKEN over LST.

4. **Failure probability**: Track occurrences where $L_f - D < P_f S_0$ at any time ($\text{FPR} < 1$). These are floor-break events under given parameters.

### A.8 Extension: Internal Credit and Bad Debt

Once the base fTOKEN model is tested, credit can be added:

- Simple loan-demand model driven by volatility and premium of fTOKEN above floor.
- LTV parameter specifying how much can be borrowed per fTOKEN.
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

    # 7. Compute end-of-horizon returns for LST and fTOKEN
    compute R_LST, R_fTOKEN, R_rel for this path
aggregate distributions of R_LST, R_fTOKEN, R_rel, min(FPR), and failure events
```

This pseudocode is intentionally high level. A production implementation should include explicit handling of tier merges, optional fTOKEN premiums, loan origination and default logic, and more detailed fee and volume models.

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
| $D$ | Outstanding debt from internal loans against fTOKEN collateral. |
| $S_0$ | Tier-0 fTOKEN supply. |
| $P_f$ | Floor price in reserve units per fTOKEN; computed as $P_f = \lfloor(L_f - D)/S_0\rfloor_{\text{tick}}$. |
| $H$ | Headroom: $H = (L_f - D) - P_f S_0$. |
| $\text{FPR}$ | Floor Protection Ratio: $\text{FPR} = (L_f - D)/(P_f S_0)$. |
| $\lambda$ | Leverage ratio: $\lambda = D / L_f$. |
| $\phi$ | Obligation ratio: $\phi = P_f S_0 / L_f$. |
| $\delta$ | Premium: $\delta = P_{\text{spot}} - P_f$, the spread between spot price and floor. |
| $\Delta \delta$ | Premium delta: change in premium over a holding period. |
| $\Delta P_f$ | Floor elevation: change in floor price over a holding period. |
| $\text{LTV}_f$ | Loan-to-value ratio applied to floor credit in native lending. |
| $R_{\text{loop}}$ | Return from a looped fTOKEN position. |
| $k$ | Effective leverage multiplier in a looped position. |
| $S_t$ | Underlying asset price at time $t$ (for example AVAX/USD). |
| $\text{Index}_t$ | LST index capturing accumulated staking rewards. |
| $P_{\text{LST}}$ | Market price of the LST. |
| $P_{\text{LST, theo}}$ | Theoretical LST price without depeg: $S_t \cdot \text{Index}_t$. |
| $\Delta e$ | Depeg shock for LST (premium or discount relative to staking-implied value). |
| $r$ | Annualized staking reward rate for the underlying. |
| $r_{\text{borrow}}$ | Borrow rate for internal fTOKEN credit. |
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
| $R_{\text{fTOKEN}}$ | Return of the fTOKEN over the simulation horizon. |
| $R_{\text{rel}}$ | Relative return: $R_{\text{rel}} = R_{\text{LST}} - R_{\text{fTOKEN}}$. |
| $p_{\text{depeg}}$ | Per-step probability of an LST depeg event in the Monte Carlo model. |
| $d_{\max}$ | Maximum magnitude of a depeg shock in the depeg distribution. |
| $\text{LGD}$ | Loss-given-default parameter for internal credit in extended simulations. |

---
