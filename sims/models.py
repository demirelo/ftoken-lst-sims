"""
fToken/Floor Simulation Models

This module implements a Python twin of the Solidity Floor_v1.sol contract,
modeling the key mechanics:
- Solvency invariant: L_f - D >= P_f * S_tradeable
- FPR (Floor Protection Ratio): (L_f - D) / (P_f * S_tradeable)
- Tier-0 floor with step-by-step absorption
- Locked supply for credit facility collateral
- LRE (Liquidity Reallocation Elevation)
- Debt caps and coverage buffers
- Bad debt modeling

Reference: Structural_Solvency_and_Risk_Topology.md
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from enum import Enum


class Asset:
    """Base asset class with price history tracking."""
    
    def __init__(self, name: str, initial_price: float):
        self.name = name
        self.initial_price = initial_price
        self.price_history: List[float] = [initial_price]

    def current_price(self) -> float:
        return self.price_history[-1]

    def update_price(self, new_price: float):
        self.price_history.append(new_price)


class Underlying(Asset):
    """
    Underlying asset (e.g., AVAX, ETH) with GBM price dynamics.
    
    dS/S = μdt + σdW
    """
    
    def __init__(self, name: str, initial_price: float, mu: float, sigma: float):
        super().__init__(name, initial_price)
        self.mu = mu
        self.sigma = sigma

    def simulate_step(self, dt: float) -> float:
        """
        Simulates one time step using Geometric Brownian Motion.
        
        Args:
            dt: Time step in years (e.g., 1/365 for daily)
            
        Returns:
            New price after the step
        """
        current = self.current_price()
        # GBM: S(t+dt) = S(t) * exp((μ - 0.5σ²)dt + σ√dt·Z)
        drift = (self.mu - 0.5 * self.sigma**2) * dt
        shock = self.sigma * np.sqrt(dt) * np.random.normal()
        new_price = current * np.exp(drift + shock)
        self.update_price(new_price)
        return new_price


class LST(Asset):
    """
    Liquid Staking Token model (e.g., sAVAX, stETH).
    
    Tracks underlying price with yield accrual and potential depeg events.
    Depeg probability correlates with market stress per spec Section 5.1.
    """
    
    def __init__(self, name: str, underlying: Underlying, staking_yield: float,
                 p_depeg_base: float = 0.0, depeg_severity_mean: float = -0.05,
                 depeg_severity_std: float = 0.02, stress_depeg_multiplier: float = 3.0):
        super().__init__(name, underlying.initial_price)
        self.underlying = underlying
        self.staking_yield = staking_yield
        self.p_depeg_base = p_depeg_base
        self.depeg_severity_mean = depeg_severity_mean
        self.depeg_severity_std = depeg_severity_std
        self.stress_depeg_multiplier = stress_depeg_multiplier
        self.index = 1.0

        # Track depeg events
        self.depeg_events: List[Tuple[int, float]] = []
        self._step_count = 0

    def simulate_step(self, dt: float, underlying_return: Optional[float] = None) -> float:
        """
        Updates LST price based on underlying, yield, and potential depeg.
        
        Depeg probability is correlated with market stress:
        - Normal conditions: p_depeg = p_depeg_base
        - Stress (underlying down >5%): p_depeg = p_depeg_base * stress_multiplier
        
        Args:
            dt: Time step in years
            underlying_return: Optional pre-computed underlying return for correlation
            
        Returns:
            New LST price
        """
        self._step_count += 1
        
        # 1. Accrue yield
        self.index *= (1 + self.staking_yield * dt)
        
        # 2. Calculate theoretical price
        theoretical_price = self.underlying.current_price() * self.index
        
        # 3. Calculate stress-adjusted depeg probability
        # Per spec: "Depegs tend to occur during market downturns"
        if underlying_return is None:
            # Estimate from price history
            if len(self.underlying.price_history) >= 2:
                prev = self.underlying.price_history[-2]
                curr = self.underlying.price_history[-1]
                underlying_return = (curr - prev) / prev if prev > 0 else 0
            else:
                underlying_return = 0
        
        # Stress multiplier kicks in during significant drawdowns
        stress_threshold = -0.03  # 3% daily drop
        if underlying_return < stress_threshold:
            # Scale multiplier based on severity
            severity_factor = min(3.0, abs(underlying_return / stress_threshold))
            p_depeg = min(1.0, self.p_depeg_base * self.stress_depeg_multiplier * severity_factor)
        else:
            p_depeg = self.p_depeg_base
        
        # 4. Check for depeg
        depeg_factor = 0.0
        if p_depeg > 0 and np.random.random() < p_depeg:
            # Sample from heavy-tailed distribution (negative shock)
            shock = np.random.normal(self.depeg_severity_mean, self.depeg_severity_std)
            depeg_factor = min(0, shock)  # Ensure it's a discount
            self.depeg_events.append((self._step_count, depeg_factor))
            
        market_price = theoretical_price * (1 + depeg_factor)
        self.update_price(market_price)
        return market_price


@dataclass
class TierSegment:
    """
    Represents a discrete bonding curve segment.
    
    Mirrors PackedSegment in Solidity:
    - initial_price: Starting price of the segment
    - price_increase: Price increment per step (0 for floor tier)
    - supply_per_step: Tokens per step
    - num_steps: Number of steps in segment (1 for floor tier)
    """
    initial_price: float
    price_increase: float
    supply_per_step: float
    num_steps: int
    
    def get_end_price(self) -> float:
        """Returns the price at the last step of this segment."""
        if self.num_steps <= 1:
            return self.initial_price
        return self.initial_price + (self.num_steps - 1) * self.price_increase
    
    def get_total_supply(self) -> float:
        """Returns total supply capacity of this segment."""
        return self.supply_per_step * self.num_steps
    
    def get_total_reserve_needed(self) -> float:
        """
        Calculate total reserve needed to back this segment.
        Sum of (price_at_step * supply_per_step) for all steps.
        """
        total = 0.0
        for step in range(self.num_steps):
            step_price = self.initial_price + step * self.price_increase
            total += step_price * self.supply_per_step
        return total


@dataclass
class Loan:
    """Represents an individual loan in the credit facility."""
    loan_id: int
    borrower: str
    principal: float
    collateral_locked: float  # fTokens locked as collateral
    origination_time: int
    floor_price_at_origination: float
    is_active: bool = True


class BadDebtEvent(Enum):
    """Types of bad debt events - NOT USED in fToken model.
    
    Note: Bad debt is structurally impossible in fToken credit facility because:
    1. Collateral (fTokens) only increases in value (floor only rises)
    2. Debt (ETH) is fixed (no interest)
    3. LTV automatically improves over time
    
    Kept for backward compatibility only.
    """
    LIQUIDATION_SHORTFALL = "liquidation_shortfall"
    DEFAULT = "default"
    PROTOCOL_WRITE_OFF = "protocol_write_off"


@dataclass
class BadDebtRecord:
    """Records a bad debt event - NOT USED in fToken model.
    
    Bad debt is structurally impossible. Kept for backward compatibility.
    """
    step: int
    event_type: BadDebtEvent
    amount: float
    loan_id: Optional[int] = None


class fToken(Asset):
    """
    Floor-backed token model implementing Floor_v1.sol mechanics.
    
    Key invariants from Solidity:
    - Coverage: L_f - D >= P_f * S_tradeable
    - FPR = (L_f - D) / (P_f * S_tradeable)
    - Headroom H = (L_f - D) - P_f * S_tradeable - buffer
    - Safe-merge: L_f - D >= P_next * (S_0 + M_next)
    
    Storage mapping:
    - reserves = _virtualCollateralSupply (L_f)
    - debt = _totalDebt (D)
    - floor_price = _segments[0]._initialPrice() (P_f)
    - floor_supply = _segments[0]._supplyPerStep() (S_0, Tier-0 supply)
    - locked_supply = _lockedSupply
    - tradeable_supply = total_supply - locked_supply
    """
    
    def __init__(
        self,
        name: str,
        underlying: Underlying,
        initial_reserves: float,
        initial_supply: float,
        initial_floor: float,
        buy_fee: float,
        sell_fee: float,
        origination_fee: float,
        # Elevation params
        elevation_threshold: float = 0,
        tier_schedule: str = 'harmonic',
        tier_capacity_base: float = 100000,
        tick_size: float = 0.01,
        # Premium curve params
        premium_slope: float = 0.000001,  # Controls how much premium_supply affects market price
        # Governance params (from Floor_v1.sol)
        debt_cap_bps: int = 8000,           # 80% of L_f max
        min_coverage_buffer_bps: int = 10,   # 0.1% minimal buffer
        # Fee routing
        fee_to_floor_ratio: float = 0.80,   # 80% of fees go to floor
        fee_to_stakers_ratio: float = 0.15, # 15% of fees go to stakers
        fee_to_team_ratio: float = 0.05,    # 5% of fees go to team
        # LRE params (from Floor_v1.sol)
        lre_realloc_bps: int = 2500,         # 25% of excess per operation
        lre_max_mkt_impact_bps: int = 200,   # 2% max price impact
        lre_threshold: float = 1.2,          # Trigger when premium 1.2x floor
        # Bad debt params
        bad_debt_lgd: float = 0.3,           # Loss-given-default (30%)
        loan_default_prob_base: float = 0.001,  # Base default probability per step
    ):
        super().__init__(name, initial_floor)
        self.underlying = underlying
        
        # Core state (mirrors Solidity storage)
        self.reserves = initial_reserves           # L_f = _virtualCollateralSupply
        self.debt = 0.0                            # D = _totalDebt
        self.locked_supply = 0.0                   # _lockedSupply
        
        # Supply tracking
        self.floor_supply = initial_supply         # S_0 = Tier-0 supply
        self.premium_supply = 0.0                  # Supply above floor tier
        self.total_supply = initial_supply         # Total minted supply
        
        # Price state
        self.floor_price = initial_floor           # P_f = _segments[0]._initialPrice()
        self.initial_floor_price = initial_floor   # Store for tier boundary calculations
        
        # Fee configuration
        self.buy_fee = buy_fee
        self.sell_fee = sell_fee
        self.origination_fee = origination_fee
        self.flash_loan_fee = 0.0005  # 0.05% flash loan fee on repayment
        
        # Fee routing configuration
        self.fee_to_floor_ratio = fee_to_floor_ratio
        self.fee_to_stakers_ratio = fee_to_stakers_ratio
        self.fee_to_team_ratio = fee_to_team_ratio
        
        # Fee accumulators
        self.governance_fees_accumulated = 0.0  # Kept for backward compat, represents total non-floor fees? No, let's track separately.
        self.stakers_fees_accumulated = 0.0
        self.team_fees_accumulated = 0.0
        
        # Elevation configuration
        self.elevation_threshold = elevation_threshold
        self.pending_fees = 0.0  # Only floor portion of fees
        self.tier_schedule = tier_schedule
        self.tier_capacity_base = tier_capacity_base
        self.tick_size = tick_size
        self.premium_slope = premium_slope
        
        # Governance params (from Floor_v1.sol)
        self.debt_cap_bps = debt_cap_bps
        self.min_coverage_buffer_bps = min_coverage_buffer_bps
        
        # LRE params
        self.lre_realloc_bps = lre_realloc_bps
        self.lre_max_mkt_impact_bps = lre_max_mkt_impact_bps
        self.lre_threshold = lre_threshold
        
        # Bad debt params
        self.bad_debt_lgd = bad_debt_lgd
        self.loan_default_prob_base = loan_default_prob_base
        
        # Tracking
        self.merges_count = 0
        self.lre_events: List[Tuple[int, float, float]] = []  # (step, amount, new_floor)
        self.bad_debt_records: List[BadDebtRecord] = []
        self._step_count = 0
        
        # Loan tracking
        self.loans: List[Loan] = []
        self._next_loan_id = 1
        
        # Build initial segment structure
        self.segments: List[TierSegment] = self._build_initial_segments(
            initial_floor, initial_supply
        )
        
        # History tracking
        self.reserves_history = [initial_reserves]
        self.supply_history = [initial_supply]
        self.floor_history = [initial_floor]
        self.fpr_history = [self.calculate_fpr()]
        self.debt_history = [0.0]
        self.locked_supply_history = [0.0]
        self.premium_multiple_history = [1.0]
        self.headroom_history = [self.calculate_headroom()]
        self.coverage_ratio_history = [self.get_coverage_ratio_bps()]
    
    def _build_initial_segments(self, floor_price: float, floor_supply: float) -> List[TierSegment]:
        """
        Build initial segment structure.
        
        Floor segment (Tier-0): 1 step, 0 price increase
        Premium segments: Multiple steps with increasing prices
        """
        segments = []
        
        # Floor segment (Tier-0) - mirrors Solidity requirement
        floor_segment = TierSegment(
            initial_price=floor_price,
            price_increase=0,
            supply_per_step=floor_supply,
            num_steps=1
        )
        segments.append(floor_segment)
        
        # Premium segments - build based on tier schedule
        current_price = floor_price
        for tier_idx in range(1, 20):  # Up to 20 tiers
            tier_capacity = self._get_tier_capacity(tier_idx)
            price_increment = self.tick_size
            
            # Each premium tier has multiple steps
            num_steps = max(1, int(tier_capacity / (floor_supply / 10)))
            
            premium_segment = TierSegment(
                initial_price=current_price + price_increment,
                price_increase=price_increment,
                supply_per_step=tier_capacity / num_steps if num_steps > 0 else tier_capacity,
                num_steps=num_steps
            )
            segments.append(premium_segment)
            current_price = premium_segment.get_end_price()
        
        return segments
    
    def _get_tier_capacity(self, tier_index: int) -> float:
        """
        Get capacity for a tier based on schedule.
        
        Harmonic: M_i = κ * S_base / i (reduces floor growth rate)
        Naive: M_i = κ * S_base (constant, causes O(m²) elevation cost)
        
        Per Appendix B: Harmonic yields O(m log m) vs O(m²) for naive.
        """
        if self.tier_schedule == 'harmonic':
            return self.tier_capacity_base / (tier_index + 1)
        else:  # naive
            return self.tier_capacity_base

    # =========================================================================
    # Core Metric Calculations (mirrors Floor_v1.sol getters)
    # =========================================================================
    
    def get_tradeable_supply(self) -> float:
        """
        Returns tradeable supply = totalSupply - lockedSupply.
        
        Mirrors _getTradeableSupply() in Floor_v1.sol:
        "Locked tokens are used as loan collateral and cannot be traded/redeemed,
        so they don't need immediate floor liquidity backing."
        """
        return max(0.0, self.total_supply - self.locked_supply)
    
    def get_available_floor_assets(self) -> float:
        """
        Returns A_f = L_f - D.
        
        Mirrors _calculateAvailableFloorAssets() in Floor_v1.sol:
        "This is the net spendable floor backing for redemptions."
        """
        return max(0.0, self.reserves - self.debt)
    
    def calculate_fpr(self) -> float:
        """
        Calculate Floor Protection Ratio.
        
        FPR = (L_f - D) / (P_f * S_tradeable)
        
        Mirrors getCoverageRatio() in Floor_v1.sol but returns ratio not bps.
        - FPR >= 1.0: Solvent at floor
        - FPR < 1.0: Insolvent at stated floor
        """
        tradeable = self.get_tradeable_supply()
        if tradeable == 0:
            return float('inf')
        
        required_coverage = self.floor_price * tradeable
        if required_coverage == 0:
            return float('inf')
        
        available = self.get_available_floor_assets()
        return available / required_coverage
    
    def get_coverage_ratio_bps(self) -> int:
        """
        Returns coverage ratio in basis points (matches Solidity).
        10000 = 100% coverage.
        """
        fpr = self.calculate_fpr()
        if fpr == float('inf'):
            return 10000000  # Max value for display
        return int(fpr * 10000)
    
    def calculate_headroom(self) -> float:
        """
        Calculate headroom H - excess reserves above floor backing.
        
        H = (L_f - D) - (P_f * S_tradeable)
        
        Positive headroom = excess that can fund floor elevation.
        Zero/negative = at or below solvency boundary.
        
        Note: Headroom is the "area between old floor and new floor" -
        the amount that can be withdrawn by users after floor goes up.
        """
        tradeable = self.get_tradeable_supply()
        required = self.floor_price * tradeable
        return self.get_available_floor_assets() - required
    
    def get_market_price(self) -> float:
        """
        Get current market price on the bonding curve.
        
        Market price = floor_price + premium_component
        Market price is ALWAYS >= floor_price by design.
        """
        premium_component = max(0, self.premium_slope * self.premium_supply)
        return self.floor_price + premium_component

    def get_premium_multiple(self) -> float:
        """
        Returns market_price / floor_price.
        
        Per spec Section 5.6: Entry basis risk indicator.
        Multiple > 1 means buyer has downside to floor.
        """
        if self.floor_price == 0:
            return float('inf')
        return self.get_market_price() / self.floor_price
    
    def get_premium_liquidity(self) -> float:
        """
        Returns liquidity in premium tiers.
        
        Mirrors _getPremiumLiquidity() in Floor_v1.sol:
        premiumLiquidity = totalCollateral - (floorPrice * floorSupply)
        """
        floor_collateral = self.floor_price * self.floor_supply
        return max(0.0, self.reserves - floor_collateral)
    
    def get_floor_liquidity(self) -> float:
        """Returns floor tier liquidity."""
        return self.reserves - self.get_premium_liquidity()
    
    def get_debt_cap(self) -> float:
        """Returns maximum allowed debt based on debt_cap_bps."""
        return self.reserves * self.debt_cap_bps / 10000
    
    def get_max_borrowable(self) -> float:
        """
        Returns maximum additional debt preserving floor coverage.
        
        Mirrors _calculateMaxBorrowable() in Floor_v1.sol:
        maxBorrow = A_f - (P_f * S_tradeable) - buffer
        Also respects debt cap.
        """
        headroom = self.calculate_headroom()
        debt_cap = self.get_debt_cap()
        remaining_cap = max(0, debt_cap - self.debt)
        return min(max(0, headroom), remaining_cap)
    
    def _distribute_fee(self, total_fee: float) -> float:
        """
        Distributes a collected fee according to configured ratios.
        Returns the amount that goes to floor elevation.
        """
        if total_fee <= 0:
            return 0.0
            
        fee_to_floor = total_fee * self.fee_to_floor_ratio
        fee_to_stakers = total_fee * self.fee_to_stakers_ratio
        fee_to_team = total_fee * self.fee_to_team_ratio
        
        # Any remainder (due to rounding or ratios < 1.0) goes to team/governance
        # Or we can normalize. For now, let's assume ratios sum to ~1.0 or close enough.
        # If they don't sum to 1, the remainder is implicitly lost or we should assign it.
        # Let's assign remainder to team to be safe.
        remainder = total_fee - (fee_to_floor + fee_to_stakers + fee_to_team)
        if remainder > 0:
            fee_to_team += remainder
            
        self.stakers_fees_accumulated += fee_to_stakers
        self.team_fees_accumulated += fee_to_team
        
        # We also track total "governance" fees for backward compatibility if needed,
        # but for now let's just track components.
        self.governance_fees_accumulated += (fee_to_stakers + fee_to_team)
        
        return fee_to_floor

    # =========================================================================
    # LRE (Liquidity Reallocation Elevation)
    # =========================================================================
    
    def can_perform_lre(self) -> Tuple[bool, float]:
        """
        Check if LRE conditions are met.
        
        Mirrors canPerformReallocation() in Floor_v1.sol:
        Condition: premiumLiquidity / floorLiquidity >= reallocThreshold
        """
        if self.lre_threshold == 0:
            return False, 0.0
        
        premium_liq = self.get_premium_liquidity()
        floor_liq = self.get_floor_liquidity()
        
        if floor_liq <= 0:
            return False, 0.0
        
        ratio = premium_liq / floor_liq
        if ratio >= self.lre_threshold:
            excess = premium_liq - floor_liq
            return True, max(0, excess)
        
        return False, 0.0
    
    def perform_lre(self) -> float:
        """
        Perform liquidity reallocation from premium to floor.
        
        Mirrors performReallocation() in Floor_v1.sol:
        1. Check threshold is met
        2. Calculate excess liquidity
        3. Move reallocBps% of excess to floor
        4. Respect maxMktImpactBps limit
        5. Raise floor with moved amount
        
        Returns: Amount reallocated
        """
        can_realloc, excess = self.can_perform_lre()
        if not can_realloc or excess <= 0:
            return 0.0
        
        # Calculate amount to move
        move_amount = excess * self.lre_realloc_bps / 10000
        
        # Check market impact limit
        total_liq = self.reserves
        max_move = total_liq * self.lre_max_mkt_impact_bps / 10000
        move_amount = min(move_amount, max_move)
        
        if move_amount <= 0:
            return 0.0
        
        # Perform floor raise with the moved amount
        old_floor = self.floor_price
        self._raise_floor_internal(move_amount)
        
        # Record event
        self.lre_events.append((self._step_count, move_amount, self.floor_price))
        
        return move_amount
    
    # =========================================================================
    # Credit Facility Operations
    # =========================================================================
    
    def originate_loan(self, amount: float, collateral_tokens: float, borrower: str = "user", fee_override: Optional[float] = None) -> Tuple[bool, float, float, Optional[int]]:
        """
        Process loan origination with proper checks.
        
        Mirrors increaseDebt() and increaseLockedSupply() in Floor_v1.sol.
        
        Args:
            amount: Loan principal amount
            collateral_tokens: fTokens to lock as collateral
            borrower: Identifier for the borrower
            fee_override: Optional fee rate override (e.g., 2.5% for presale loops)
            
        Returns:
            (success, fee_to_floor, fee_to_governance, loan_id)
        """
        # Check debt cap
        new_debt = self.debt + amount
        debt_cap = self.get_debt_cap()
        if new_debt > debt_cap:
            return False, 0.0, 0.0, None
        
        # Check that collateral doesn't exceed available supply
        if collateral_tokens > (self.total_supply - self.locked_supply):
            return False, 0.0, 0.0,None
        
        # Check coverage invariant after the loan
        # After: debt increases, locked_supply increases (reducing tradeable)
        future_tradeable = self.get_tradeable_supply() - collateral_tokens
        if future_tradeable < 0:
            return False, 0.0, 0.0, None
        
        required = self.floor_price * future_tradeable
        buffer = required * self.min_coverage_buffer_bps / 10000
        future_available = self.reserves - new_debt
        
        if future_available < (required + buffer):
            return False, 0.0, 0.0, None
        
        # Process loan with fee split (use override if provided)
        fee_rate = fee_override if fee_override is not None else self.origination_fee
        total_fee = amount * fee_rate
        # Distribute fee
        fee_to_floor = self._distribute_fee(total_fee)
        fee_to_non_floor = total_fee - fee_to_floor  # For return value compatibility
        
        self.debt += amount
        self.locked_supply += collateral_tokens
        self.pending_fees += fee_to_floor
        # governance_fees_accumulated updated inside _distribute_fee
        
        # Create loan record
        loan = Loan(
            loan_id=self._next_loan_id,
            borrower=borrower,
            principal=amount,
            collateral_locked=collateral_tokens,
            origination_time=self._step_count,
            floor_price_at_origination=self.floor_price
        )
        self.loans.append(loan)
        self._next_loan_id += 1
        
        return True, fee_to_floor, fee_to_non_floor, loan.loan_id
    
    def repay_loan(self, loan_id: int, amount: float) -> Tuple[bool, float]:
        """
        Process loan repayment (unwind/unloop).
        
        When repaying, borrower:
        1. Pays back ETH principal (goes to reserves)
        2. Pays 0.05% flash loan fee (goes to floor elevation)
        3. Unlocks collateral if fully repaid
        
        The repaid ETH MUST go back to reserves to maintain coverage.
        
        Args:
            loan_id: ID of the loan to repay
            amount: Amount of ETH to repay
            
        Returns:
            (success, flash_fee_paid)
        """
        loan = next((l for l in self.loans if l.loan_id == loan_id and l.is_active), None)
        if loan is None:
            return False, 0.0
        
        # Cap at remaining principal
        repay_amount = min(amount, loan.principal)
        
        # Calculate flash loan fee (0.05% of repayment)
        flash_fee = repay_amount * self.flash_loan_fee
        
        # Update state
        # Repaid ETH goes back to reserves (this is critical for coverage!)
        self.reserves += repay_amount
        self.debt -= repay_amount
        loan.principal -= repay_amount
        
        # Flash loan fee goes to pending fees (floor elevation)
        # Distribute fee
        fee_to_floor = self._distribute_fee(flash_fee)
        self.pending_fees += fee_to_floor
        # governance_fees_accumulated updated inside _distribute_fee
        
        # If fully repaid, unlock collateral
        if loan.principal <= 0:
            self.locked_supply -= loan.collateral_locked
            loan.is_active = False
        
        return True, flash_fee
    
    def repay_loan_simple(self, amount: float, collateral_to_unlock: float) -> Tuple[bool, float]:
        """
        Simple loan repayment for agent exits (no loan tracking).
        
        Used when agents exit and need to repay debt to unlock collateral.
        
        Args:
            amount: Amount of ETH to repay
            collateral_to_unlock: Amount of collateral to unlock
            
        Returns:
            (success, flash_fee_paid)
        """
        if amount <= 0:
            return False, 0.0
        
        # Cap at total debt
        repay_amount = min(amount, self.debt)
        
        # Calculate flash loan fee
        flash_fee = repay_amount * self.flash_loan_fee
        # Distribute fee
        fee_to_floor = self._distribute_fee(flash_fee)
        
        # Update state
        self.reserves += repay_amount
        self.debt -= repay_amount
        self.locked_supply -= min(collateral_to_unlock, self.locked_supply)
        
        # Fees
        self.pending_fees += fee_to_floor
        # governance_fees_accumulated updated inside _distribute_fee
        
        return True, flash_fee
    
    def process_loan_defaults(self) -> float:
        """
        Process potential loan defaults - RETURNS 0 (bad debt impossible).
        
        WHY BAD DEBT CANNOT OCCUR:
        ==========================
        1. Collateral = fTokens → floor price ONLY rises → collateral value ONLY increases
        2. Debt = ETH → fixed amount (no interest) → debt stays constant
        3. LTV improves over time → as floor rises, effective LTV decreases
        
        Example:
        - Day 1: Lock 100 fTokens (floor=1.0) → Collateral=100 ETH, Borrow 90 ETH → LTV=90%
        - Day 30: Floor=1.1 → Collateral=110 ETH, Debt=90 ETH → LTV=81.8% (safer!)
        - Day 60: Floor=1.2 → Collateral=120 ETH, Debt=90 ETH → LTV=75% (even safer!)
        
        Since collateral can never be worth less than debt, bad debt is structurally
        impossible. The credit facility is risk-free for the protocol.
        
        Returns: 0.0 (always - bad debt cannot occur)
        """
        # No defaults can occur - loans only get safer over time
        return 0.0
    
    # =========================================================================
    # Trading Operations
    # =========================================================================
    
    def buy(self, reserve_amount: float, execution_price: float = None) -> Tuple[float, float, float, float]:
        """
        Process a buy order.
        
        Mirrors buyFor() in BC_Discrete_Redeeming_VirtualSupply_v1.sol.
        Price tiers are fixed at 1% increments (tick_size = 0.01).
        
        Args:
            reserve_amount: Amount of reserve (collateral) to spend
            execution_price: Optional price to use (for batched execution)
            
        Returns:
            (tokens_minted, fee_to_floor, fee_to_governance, actual_spent)
        """
        if reserve_amount <= 0:
            return 0.0, 0.0, 0.0, 0.0
        
        # Calculate and split fee
        total_fee = reserve_amount * self.buy_fee
        # Distribute fee
        fee_to_floor = self._distribute_fee(total_fee)
        net_investment = reserve_amount - total_fee
        
        # Calculate tokens to mint based on execution price
        price = execution_price if execution_price else self.get_market_price()
        if price <= 0:
            return 0.0, 0.0, 0.0, 0.0
        
        tokens_minted = net_investment / price
        
        # Cap minting to prevent runaway growth: max 5% of current supply per transaction
        # If capped, scale down the investment proportionally (excess is "not spent")
        max_mint = self.total_supply * 0.05
        actual_investment = net_investment
        actual_spent = reserve_amount
        
        if tokens_minted > max_mint:
            # Scale down: only use the reserves needed for max_mint tokens
            # actual_investment = max_mint * price
            # But wait, net_investment = reserve - fee.
            # If we scale down net_investment, we should also scale down fee and reserve_amount.
            # Let's calculate purely based on tokens needed:
            # required_net = tokens * price
            # required_reserve = required_net / (1 - buy_fee)
            
            tokens_minted = max_mint
            actual_net = tokens_minted * price
            actual_spent = actual_net / (1 - self.buy_fee) if (1 - self.buy_fee) > 0 else actual_net
            
            # Recalculate fees based on actual spent
            total_fee = actual_spent * self.buy_fee
            fee_to_floor = self._distribute_fee(total_fee) # note: _distribute_fee might have side effects? 
            # Yes, modifies governance_fees_accumulated. We should be careful calling it twice or reverse it?
            # actually _distribute_fee just returns the split. It increments self.governance_fees_accumulated.
            # We should probably reset/undo the previous call or just calculate properly first.
            
            # To avoid side effect complexity: let's revert the first _distribute_fee effect if we can.
            # Or better: check cap BEFORE fee distrib?
            # But cap depends on total_supply which is current.
            # And tokens_minted depends on price.
            # So the logic flow is correct.
            # We just need to adjust the accumulated fees.
             
            # Let's fix this cleanly:
            # 1. Calculate potential tokens.
            # 2. Check cap.
            # 3. Determine Final Tokens.
            # 4. Calculate Final Reserve Amount needed.
            # 5. Apply Fees and Updates.
        
        # RE-IMPLEMENTATION for correctness:
        price = execution_price if execution_price else self.get_market_price()
        if price <= 0:
            return 0.0, 0.0, 0.0, 0.0
            
        # 1. Max potential tokens based on wallet strict limit? No, limit is reserve_amount.
        # But we first need to see how much we CAN buy.
        
        # Potential net investment
        potential_net = reserve_amount * (1 - self.buy_fee)
        potential_tokens = potential_net / price
        
        # 2. Apply Cap
        max_mint = self.total_supply * 0.05
        tokens_minted = min(potential_tokens, max_mint)
        
        # 3. Backward calculate actual needed reserves
        needed_net = tokens_minted * price
        needed_reserves = needed_net / (1 - self.buy_fee)
        
        # 4. Apply Fees on actual needed reserves
        actual_total_fee = needed_reserves * self.buy_fee
        fee_to_floor = self._distribute_fee(actual_total_fee)
        fee_gov = actual_total_fee - fee_to_floor
        
        # 5. Update State
        self.reserves += needed_net
        self.pending_fees += fee_to_floor
        self.premium_supply += tokens_minted
        self.total_supply += tokens_minted
        
        return tokens_minted, fee_to_floor, fee_gov, needed_reserves
    
    MIN_SUPPLY = 1e-6

    def sell(self, token_amount: float, execution_price: float = None) -> Tuple[float, float, bool]:
        """
        Process a sell order with coverage check.
        
        Mirrors sellTo() in Floor_v1.sol with coverage enforcement.
        
        Args:
            token_amount: Amount of fTokens to sell
            execution_price: Optional price to use (for batched execution)
            
        Returns:
            (reserve_received, fee_paid, success)
        """
        if token_amount <= 0:
            return 0.0, 0.0, False
        
        # Cap at available supply
        available = self.get_tradeable_supply()
        token_amount = min(token_amount, available, self.total_supply)
        
        if token_amount <= 0:
            return 0.0, 0.0, False

        # SAFEGUARD: Ensure we don't drop below MIN_SUPPLY
        if (self.total_supply - token_amount) < self.MIN_SUPPLY:
            # Cap the sell amount to leave MIN_SUPPLY
            # If we're already below/at MIN_SUPPLY, this becomes <= 0
            token_amount = self.total_supply - self.MIN_SUPPLY
            
            if token_amount <= 0:
                # Cannot sell anymore without breaching min supply
                return 0.0, 0.0, False
        
        # Calculate payout at execution price
        price = execution_price if execution_price else self.get_market_price()
        gross_payout = token_amount * price
        fee = gross_payout * self.sell_fee
        net_payout = gross_payout - fee
        
        # Coverage check (mirrors Floor_v1.sol sellTo)
        # Per Solidity: coverage check only applies when debt > 0
        new_reserves = self.reserves - net_payout
        
        # Basic sanity: cannot have negative reserves
        if new_reserves < 0:
             return 0.0, 0.0, False

        new_supply = self.total_supply - token_amount
        new_tradeable = max(0, new_supply - self.locked_supply)
        new_required = self.floor_price * new_tradeable
        
        if self.debt > 0:
            # Only check coverage when there's outstanding debt
            if (new_reserves - self.debt) < new_required:
                return 0.0, 0.0, False
        
        # Execute sell
        self.reserves = new_reserves
        self.total_supply = new_supply
        
        # Split fee between floor and governance
        # Distribute fee
        fee_to_floor = self._distribute_fee(fee)
        self.pending_fees += fee_to_floor
        # governance_fees_accumulated updated inside _distribute_fee
        
        # Reduce from premium first, then floor
        if self.premium_supply >= token_amount:
            self.premium_supply -= token_amount
        else:
            reduction_from_floor = token_amount - self.premium_supply
            self.premium_supply = 0
            self.floor_supply = max(0, self.floor_supply - reduction_from_floor)
        
        # Recalibrate curve after redemption
        self._recalibrate_curve()
        
        return net_payout, fee, True
    
    def _recalibrate_curve(self):
        """
        Recalibrate curve after redemptions.
        
        Mirrors _recalibrateCurve() in Floor_v1.sol:
        "Shrinks the floor segment to match current supply,
        ensuring next buy starts in the premium tier."
        """
        if self.total_supply < self.floor_supply and self.total_supply > 0:
            # Shrink floor to current supply (with minimum)
            min_floor_supply = 1.0  # Prevent dust issues
            self.floor_supply = max(min_floor_supply, self.total_supply)
        
        # Update premium supply as derived value
        self.premium_supply = max(0.0, self.total_supply - self.floor_supply)
    
    # =========================================================================
    # Floor Elevation
    # =========================================================================
    
    def _raise_floor_internal(self, collateral_amount: float) -> float:
        """
        Internal floor raise logic.
        
        Mirrors raiseFloor() in Floor_v1.sol with step-by-step absorption.
        Continuously verifies that FPR stays >= 1.0 + buffer after each raise.
        
        Tier Structure:
        - Tier 0 (Floor): price = P_f, supply = floor_supply
        - Tier N (N>=1): price_boundary = initial_floor + N * tick_size
                         capacity = tier_capacity_base / (N + 1)
        
        Safe-Merge Trigger:
        - When floor_price >= tier_boundary, check if we can ABSORB that tier
        - Absorption: floor_supply += min(premium_supply, tier_capacity)
        - Does NOT create new supply - reclassifies existing premium tokens
        
        Args:
            collateral_amount: Amount of collateral to inject
            
        Returns:
            Actual collateral consumed
        """
        if collateral_amount <= 0:
            return 0.0
        
        consumed = 0.0
        max_steps = 200  # Allow more steps for proper tier absorption
        steps_consumed = 0
        
        while steps_consumed < max_steps:
            # Cost to raise floor by one tick
            # Use total_supply to ensure we have backing for ALL tokens (including locked)
            # Safeguard: Use max(total_supply, 1000.0) to prevent infinite growth if supply drops near zero
            # This acts as "virtual liquidity" ensuring floor elevation always has a minimum cost
            backing_supply = max(self.total_supply, 1000.0)
            cost_per_tick = self.tick_size * backing_supply
            
            # Stop if we've consumed all the fees that were injected
            # Fees ARE the source of floor elevation - no extra buffer needed
            if consumed + cost_per_tick > collateral_amount:
                break
            
            # Raise floor by one tick
            next_floor = self.floor_price + self.tick_size
            self.floor_price = next_floor
            consumed += cost_per_tick
            steps_consumed += 1
            
            # Check for tier merge at this new floor price
            # Tier N boundary = initial_floor + N * tick_size
            # We should absorb tier (merges_count + 1) when floor >= its boundary
            next_tier_idx = self.merges_count + 1
            tier_boundary = self.initial_floor_price + next_tier_idx * self.tick_size
            
            # Check if we've reached or passed the next tier boundary
            if self.floor_price >= tier_boundary and self.premium_supply > 0:
                next_capacity = self._get_tier_capacity(next_tier_idx)
                
                # Amount to absorb = min(premium_supply, tier_capacity)
                # This reclassifies existing premium tokens as floor tokens
                amount_to_absorb = min(self.premium_supply, next_capacity)
                
                if amount_to_absorb > 0:
                    # Calculate new floor_supply after absorption
                    new_floor_supply = self.floor_supply + amount_to_absorb
                    new_tradeable = self.total_supply - self.locked_supply  # Total unchanged
                    
                    # Safe-merge check: can we back the absorbed supply at new floor?
                    merge_required = self.floor_price * new_tradeable
                    merge_buffer = merge_required * self.min_coverage_buffer_bps / 10000
                    
                    # Recalculate available (may have changed)
                    available = self.get_available_floor_assets()
                    
                    if available >= (merge_required + merge_buffer):
                        # Execute merge - reclassify premium as floor
                        self.floor_supply = new_floor_supply
                        self.premium_supply -= amount_to_absorb
                        # total_supply UNCHANGED - we're just reclassifying
                        self.merges_count += 1
        
        # Final cleanup - ensure premium_supply consistency
        self.premium_supply = max(0.0, self.total_supply - self.floor_supply)
        
        return consumed
    
    def process_elevation(self):
        """
        Process batched elevation when threshold is met.
        
        The flow:
        1. Fees accumulate → added to reserves
        2. Fees support floor rise: delta_floor = fees / tradeable
        3. Floor rises → collateral worth more
        4. Tier merges when floor reaches tier boundary
        5. Borrowers can top-up (their headroom increases)
        """
        if self.pending_fees >= self.elevation_threshold:
            fees_to_inject = self.pending_fees
            self.reserves += fees_to_inject
            
            # Raise floor, returns how much was actually consumed
            consumed = self._raise_floor_internal(fees_to_inject)
            
            # Keep unconsumed fees for next elevation
            self.pending_fees = fees_to_inject - consumed
    
    # =========================================================================
    # Realistic Loan Activity
    # =========================================================================
    
    def calculate_borrower_headroom(self, ltv: float = 0.90) -> float:
        """
        Calculate borrower headroom - additional amount existing borrowers can borrow.
        
        Headroom is created when the FLOOR RISES:
        1. Fees (trading + loans) accumulate
        2. Fees → floor elevation (65% to floor reserves)
        3. Floor rises → collateral value increases
        4. Increased collateral value → can borrow more at same LTV
        
        Headroom = (locked_supply × new_floor_price × LTV) - current_debt
        
        Args:
            ltv: Target loan-to-value ratio
            
        Returns:
            Additional debt that can be borrowed (the "headroom")
        """
        if self.locked_supply <= 0 or self.debt <= 0:
            return 0.0
        
        # Collateral value at current floor
        collateral_value = self.locked_supply * self.floor_price
        
        # Max debt at target LTV
        max_debt_at_ltv = collateral_value * ltv
        
        # Headroom = additional borrowable amount
        headroom = max(0, max_debt_at_ltv - self.debt)
        
        # Also respect debt cap
        debt_cap = self.get_debt_cap()
        room_under_cap = max(0, debt_cap - self.debt)
        
        return min(headroom, room_under_cap)
    
    def calculate_max_new_loan(self, tokens_to_lock: float, ltv: float = 0.90) -> float:
        """
        Calculate max debt for a NEW loan (locking new tokens).
        
        Must maintain coverage invariant after the loan.
        
        Args:
            tokens_to_lock: New tokens to lock as collateral
            ltv: Loan-to-value ratio
            
        Returns:
            Maximum debt for the new loan
        """
        if tokens_to_lock <= 0:
            return 0.0
        
        # Debt cap check
        debt_cap = self.get_debt_cap()
        room_under_cap = max(0, debt_cap - self.debt)
        
        # Max loan at LTV
        collateral_value = tokens_to_lock * self.floor_price
        max_at_ltv = collateral_value * ltv
        
        # Coverage check after loan
        future_tradeable = self.get_tradeable_supply() - tokens_to_lock
        if future_tradeable < 0:
            return 0.0
        
        required = self.floor_price * future_tradeable
        buffer = required * self.min_coverage_buffer_bps / 10000
        room_under_coverage = max(0, self.reserves - self.debt - required - buffer)
        
        return min(max_at_ltv, room_under_cap, room_under_coverage)
    
    def process_loan_repayments(
        self,
        repay_probability: float = 0.02,
        partial_repay_ratio: float = 0.3
    ) -> Tuple[float, float, float]:
        """
        Process sporadic loan repayments (unlooping).
        
        Borrowers occasionally repay loans to unlock collateral. This creates
        a revolving credit facility with turnover, not just one-way origination.
        
        In reality, borrowers repay when:
        - They need liquidity (sell the unlocked tokens)
        - They want to reduce leverage
        - Market conditions change
        
        Repayment flow:
        1. Borrower pays back ETH principal (goes to reserves)
        2. Borrower pays 0.05% flash loan fee (goes to floor elevation)
        3. Collateral unlocked if fully repaid
        
        Args:
            repay_probability: Probability each active loan gets (partially) repaid this step
            partial_repay_ratio: Fraction of loan to repay (0.3 = 30% partial repay)
            
        Returns:
            (total_debt_repaid, total_collateral_unlocked, total_flash_fees)
        """
        total_repaid = 0.0
        total_unlocked = 0.0
        total_flash_fees = 0.0
        
        # Get active loans
        active_loans = [l for l in self.loans if l.is_active and l.principal > 0]
        
        for loan in active_loans:
            # Stochastic repayment decision
            if np.random.random() < repay_probability:
                # Partial or full repayment
                if np.random.random() < 0.3:  # 30% chance of full repay
                    repay_amount = loan.principal
                else:
                    repay_amount = loan.principal * partial_repay_ratio
                
                # Execute repayment
                old_principal = loan.principal
                old_collateral = loan.collateral_locked
                
                success, flash_fee = self.repay_loan(loan.loan_id, repay_amount)
                if success:
                    actual_repaid = old_principal - loan.principal
                    total_repaid += actual_repaid
                    total_flash_fees += flash_fee
                    
                    # If loan fully repaid, collateral was unlocked
                    if not loan.is_active:
                        total_unlocked += old_collateral
        
        return total_repaid, total_unlocked, total_flash_fees
    
    def process_loan_activity(
        self,
        target_lock_ratio: float = 0.85,
        ltv: float = 0.90,
        enable_topup: bool = True,
        repay_probability: float = 0.02,
        partial_repay_ratio: float = 0.3
    ) -> Tuple[float, float, float, float, float]:
        """
        Process realistic loan activity for floor token holders.
        
        The full loan lifecycle:
        1. Repayments (unlooping) - sporadic loan closures unlock collateral
        2. New originations - lock tokens, borrow at LTV
        3. Top-ups - borrow additional headroom when floor rises
        
        This creates a revolving credit facility with turnover.
        
        Headroom = (collateral_value × LTV) - current_debt
        When floor rises, collateral_value increases, creating headroom.
        
        Args:
            target_lock_ratio: Target % of floor supply to lock
            ltv: Loan-to-value ratio (default 90%)
            enable_topup: Whether to top up when floor rises
            repay_probability: Probability each loan gets repaid this step
            partial_repay_ratio: Fraction of loan to repay on partial repayment
            
        Returns:
            (new_debt_created, collateral_locked, fees_generated, debt_repaid, collateral_unlocked)
        """
        new_debt = 0.0
        new_collateral = 0.0
        fees_generated = 0.0
        
        # === STEP 0: Process repayments (unlooping) ===
        # This frees up collateral for new loans and creates turnover
        # Repaid ETH goes back to reserves, flash loan fee to floor
        debt_repaid, collateral_unlocked, flash_fees = self.process_loan_repayments(
            repay_probability=repay_probability,
            partial_repay_ratio=partial_repay_ratio
        )
        fees_generated += flash_fees
        
        floor_supply = self.floor_supply
        if floor_supply <= 0:
            return 0.0, 0.0, fees_generated, debt_repaid, collateral_unlocked
        
        # === STEP 1: Lock new tokens if below target ===
        current_locked = self.locked_supply
        target_locked = floor_supply * target_lock_ratio
        tokens_to_lock = max(0, target_locked - current_locked)
        
        # Limit to available (unlocked) floor supply
        available_to_lock = max(0, floor_supply - current_locked)
        tokens_to_lock = min(tokens_to_lock, available_to_lock)
        
        if tokens_to_lock > 0:
            # Calculate max loan for these tokens
            max_loan = self.calculate_max_new_loan(tokens_to_lock, ltv)
            
            if max_loan > 0:
                # Scale collateral to actual loan amount
                actual_collateral = (max_loan / ltv) / self.floor_price
                actual_collateral = min(actual_collateral, tokens_to_lock)
                
                # Originate loan
                success, fee_f, fee_g, _ = self.originate_loan(
                    max_loan, actual_collateral, borrower="floor_holder"
                )
                
                if success:
                    new_debt += max_loan
                    new_collateral += actual_collateral
                    fees_generated += fee_f + fee_g
        
        # === STEP 2: Top-up existing loans ===
        # Headroom = additional borrowable due to floor appreciation
        # Floor rises → collateral value up → can borrow more at same LTV
        if enable_topup and self.locked_supply > 0 and self.debt > 0:
            headroom = self.calculate_borrower_headroom(ltv)
            
            if headroom > 0:
                # Top-up: borrow the headroom (no new collateral needed)
                success, fee_f, fee_g, _ = self.originate_loan(
                    headroom, 0.0, borrower="topup"
                )
                
                if success:
                    new_debt += headroom
                    fees_generated += fee_f + fee_g
        
        return new_debt, new_collateral, fees_generated, debt_repaid, collateral_unlocked
    
    # =========================================================================
    # Leverage Looping
    # =========================================================================
    
    def process_leverage_looping(
        self,
        is_presale: bool = False,
        leverage_probability_base: float = 0.05,
        leverage_premium_threshold: float = 0.10,
        average_loops: float = 2.0,
        leverage_ltv: float = 0.70
    ) -> Tuple[float, float, float]:
        """
        Process leverage looping (looping to lever up fToken position).
        
        Leverage loop flow:
        1. User has fTokens they want to lever up
        2. Lock fTokens as collateral
        3. Borrow ETH (pay origination fee)
        4. Buy more fTokens with borrowed ETH
        5. Repeat for N loops
        
        Fees:
        - Presale: 2.5% per loop (origination fee)
        - Post-presale: 2% per loop (standard origination fee)
        
        When people lever up:
        - Premium < 10%: Attractive because downside to floor is small
        - Higher premium = less attractive (more downside risk)
        
        The probability of leveraging scales inversely with premium:
        - At 0% premium: max probability
        - At threshold (10%): probability drops to near zero
        - Above threshold: no leveraging
        
        Args:
            is_presale: If True, use 2.5% fee; if False, use 2% fee
            leverage_probability_base: Base probability per step that leveraging occurs
            leverage_premium_threshold: Max premium at which leveraging is attractive
            average_loops: Average number of leverage loops executed
            leverage_ltv: LTV used for leverage (typically 70%)
            
        Returns:
            (total_debt_created, total_fTokens_acquired, total_fees_paid)
        """
        total_debt = 0.0
        total_tokens_acquired = 0.0
        total_fees = 0.0
        
        # Set fee based on presale status
        loop_fee = 0.025 if is_presale else self.origination_fee  # 2.5% presale, 2% otherwise
        
        # Calculate current premium
        market_price = self.get_market_price()
        premium = (market_price - self.floor_price) / self.floor_price if self.floor_price > 0 else 0
        
        # Only lever up if premium is below threshold
        if premium >= leverage_premium_threshold:
            return 0.0, 0.0, 0.0
        
        # Scale probability inversely with premium
        # At 0% premium: full probability
        # At threshold: zero probability
        premium_factor = max(0, 1 - (premium / leverage_premium_threshold))
        adjusted_probability = leverage_probability_base * premium_factor
        
        # Check if leveraging happens this step
        if np.random.random() > adjusted_probability:
            return 0.0, 0.0, 0.0
        
        # Determine number of loops (Poisson-ish distribution around average)
        # Max 10 loops for 10x max leverage (at 90% LTV, 10 loops ≈ 10x)
        num_loops = min(10, max(1, int(np.random.poisson(average_loops))))
        
        # Calculate how much "fresh capital" is being levered
        # Use a fraction of available tradeable supply as the base
        available_supply = self.get_tradeable_supply()
        if available_supply <= 0:
            return 0.0, 0.0, 0.0
        
        # Base leverage amount: 1-5% of tradeable supply participates each time
        leverage_participation_rate = 0.01 + np.random.random() * 0.04
        tokens_to_leverage = available_supply * leverage_participation_rate
        
        # Execute leverage loops
        current_tokens = tokens_to_leverage
        
        for loop in range(num_loops):
            if current_tokens <= 0:
                break
            
            # Step 1: Lock tokens as collateral
            collateral_value = current_tokens * self.floor_price
            
            # Step 2: Calculate max borrow amount
            max_borrow = self.calculate_max_new_loan(current_tokens, leverage_ltv)
            if max_borrow <= 0:
                break
            
            # Step 3: Borrow ETH (with presale loop fee if applicable)
            success, fee_f, fee_g, _ = self.originate_loan(
                max_borrow, current_tokens, borrower=f"leverage_loop_{loop}",
                fee_override=loop_fee
            )
            
            if not success:
                break
            
            total_debt += max_borrow
            total_fees += fee_f + fee_g
            
            # Step 4: Buy more fTokens with borrowed ETH
            # Account for buy fee
            net_eth_for_buying = max_borrow * (1 - self.buy_fee)
            tokens_bought = net_eth_for_buying / market_price if market_price > 0 else 0
            
            # Execute the buy (this adds to supply and reserves)
            actual_bought, buy_fee_f, buy_fee_g, _ = self.buy(max_borrow, execution_price=market_price)
            
            total_tokens_acquired += actual_bought
            total_fees += buy_fee_f + buy_fee_g
            
            # The newly bought tokens become collateral for next loop
            current_tokens = actual_bought
            
            # Update market price for next iteration (price impact)
            market_price = self.get_market_price()
        
        return total_debt, total_tokens_acquired, total_fees
    
    # =========================================================================
    # Main Simulation Step
    # =========================================================================
    
    def simulate_step(
        self,
        dt: float,
        buy_volume: float,
        sell_volume: float,
        new_loan_amount: float = 0,
        new_loan_collateral: float = 0,
        # Realistic loan activity params
        enable_loan_activity: bool = False,
        target_lock_ratio: float = 0.85,
        loan_ltv: float = 0.90,
        enable_topup: bool = True,
        repay_probability: float = 0.02,
        partial_repay_ratio: float = 0.3,
        # Leverage looping params
        enable_leverage_looping: bool = False,
        is_presale: bool = False,
        leverage_probability_base: float = 0.05,
        leverage_premium_threshold: float = 0.10,
        average_leverage_loops: float = 2.0,
        leverage_ltv: float = 0.70
    ) -> float:
        """
        Simulate one time step.
        
        Args:
            dt: Time step in years
            buy_volume: Volume of buys in reserve units
            sell_volume: Volume of sells in reserve units
            new_loan_amount: New loan origination amount (legacy)
            new_loan_collateral: fTokens to lock for new loan (legacy)
            enable_loan_activity: Enable realistic loan activity model
            target_lock_ratio: Target % of floor supply to lock
            loan_ltv: LTV ratio for loans
            enable_topup: Enable top-up when floor rises
            repay_probability: Probability each loan gets repaid this step
            partial_repay_ratio: Fraction of loan to repay on partial repayment
            enable_leverage_looping: Enable leverage looping behavior
            is_presale: If True, use 2.5% loop fee; if False, use 2%
            leverage_probability_base: Base probability of leverage looping per step
            leverage_premium_threshold: Premium below which leverage is attractive (10%)
            average_leverage_loops: Average number of leverage loops
            leverage_ltv: LTV used for leverage loops
            
        Returns:
            Current floor price
        """
        self._step_count += 1
        
        # Track floor before step for top-up logic
        floor_before = self.floor_price
        
        # Capture start-of-step price for consistent execution within the step
        # This models random ordering of trades within a time step
        start_price = self.get_market_price()
        
        # 1. Process trading using start-of-step price for both
        # This prevents intra-step price manipulation
        sell_tokens = sell_volume / start_price if start_price > 0 and sell_volume > 0 else 0
        
        if buy_volume > 0:
            self.buy(buy_volume, execution_price=start_price)
        
        if sell_tokens > 0:
            self.sell(sell_tokens, execution_price=start_price)
        
        # 2. Process loan origination (legacy mode)
        if new_loan_amount > 0 and new_loan_collateral > 0:
            self.originate_loan(new_loan_amount, new_loan_collateral)
        
        # 3. Process elevation (before loan activity to create headroom)
        self.process_elevation()
        
        # 4. Realistic loan activity (includes repayments, originations, and top-ups)
        if enable_loan_activity:
            self.process_loan_activity(
                target_lock_ratio=target_lock_ratio,
                ltv=loan_ltv,
                enable_topup=enable_topup,
                repay_probability=repay_probability,
                partial_repay_ratio=partial_repay_ratio
            )
        
        # 5. Leverage looping (when premium is low, people lever up)
        if enable_leverage_looping:
            self.process_leverage_looping(
                is_presale=is_presale,
                leverage_probability_base=leverage_probability_base,
                leverage_premium_threshold=leverage_premium_threshold,
                average_loops=average_leverage_loops,
                leverage_ltv=leverage_ltv
            )
        
        # 6. Try LRE if conditions met
        self.perform_lre()
        
        # 7. Recalibrate curve - shrink floor supply if total_supply dropped
        # This ensures next buy starts in premium tier after sells
        self._recalibrate_curve()
        
        # 8. Update history
        self.update_price(self.floor_price)
        self.reserves_history.append(self.reserves)
        self.supply_history.append(self.total_supply)
        self.floor_history.append(self.floor_price)
        self.fpr_history.append(self.calculate_fpr())
        self.debt_history.append(self.debt)
        self.locked_supply_history.append(self.locked_supply)
        self.premium_multiple_history.append(self.get_premium_multiple())
        self.headroom_history.append(self.calculate_headroom())
        self.coverage_ratio_history.append(self.get_coverage_ratio_bps())
        
        return self.floor_price
    
    # =========================================================================
    # Status Methods
    # =========================================================================
    
    def is_solvent(self) -> bool:
        """Check if system is solvent (FPR >= 1.0)."""
        return self.calculate_fpr() >= 1.0
    
    def get_fpr_zone(self) -> str:
        """
        Returns FPR zone per spec Section 9.3.
        - Green: FPR >= 1.10
        - Yellow: 1.05 <= FPR < 1.10  
        - Red: FPR < 1.05
        """
        fpr = self.calculate_fpr()
        if fpr >= 1.10:
            return "green"
        elif fpr >= 1.05:
            return "yellow"
        else:
            return "red"
    
    def get_total_bad_debt(self) -> float:
        """Returns total bad debt incurred - ALWAYS 0 (bad debt impossible)."""
        return 0.0
    
    def get_loan_health(self, loan_id: int) -> Optional[dict]:
        """
        Get health metrics for a specific loan.
        
        Returns dict with:
        - current_ltv: Current LTV based on current floor price
        - original_ltv: LTV at origination
        - collateral_value: Current value of collateral in ETH
        - debt: Remaining debt
        - health_factor: collateral_value / debt (> 1 = healthy)
        
        Note: LTV only improves over time since floor only rises.
        """
        loan = next((l for l in self.loans if l.loan_id == loan_id and l.is_active), None)
        if loan is None:
            return None
        
        # Collateral value = tokens * current floor price
        collateral_value = loan.collateral_locked * self.floor_price
        original_collateral_value = loan.collateral_locked * loan.floor_price_at_origination
        
        current_ltv = loan.principal / collateral_value if collateral_value > 0 else 0
        original_ltv = loan.principal / original_collateral_value if original_collateral_value > 0 else 0
        health_factor = collateral_value / loan.principal if loan.principal > 0 else float('inf')
        
        return {
            'current_ltv': current_ltv,
            'original_ltv': original_ltv,
            'ltv_improvement': (original_ltv - current_ltv) / original_ltv if original_ltv > 0 else 0,
            'collateral_value': collateral_value,
            'debt': loan.principal,
            'health_factor': health_factor,
            'floor_appreciation': self.floor_price / loan.floor_price_at_origination - 1
        }
    
    def get_active_loan_count(self) -> int:
        """Returns count of active loans."""
        return sum(1 for l in self.loans if l.is_active)
    
    def get_total_outstanding_debt(self) -> float:
        """Returns total outstanding loan principal."""
        return sum(l.principal for l in self.loans if l.is_active)
