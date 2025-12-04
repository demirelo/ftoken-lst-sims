"""
Agent-Based Modeling for fToken Simulation

This module defines distinct participant archetypes with different
behaviors, time horizons, and risk preferences.

Agent Types:
- LeverageSeeker: Aggressive leverage user, deleverages in stress
- YieldSeeker: Conservative holder, minimal trading
- DATAgent: Long-horizon buyer, estimates 5Y floor growth
- Arbitrageur: Buys when market < expected floor
- FloorHolder: Uses credit facility for capital efficiency
"""

import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum


class ActionType(Enum):
    """Types of actions an agent can take."""
    BUY = "buy"
    SELL = "sell"
    BORROW = "borrow"
    REPAY = "repay"
    LEVERAGE_LOOP = "leverage_loop"
    TOPUP = "topup"
    HOLD = "hold"


@dataclass
class Action:
    """Represents an action an agent wants to take."""
    action_type: ActionType
    amount: float = 0.0           # ETH or tokens depending on action
    loops: int = 0                # For leverage loops
    reason: str = ""              # Why the agent took this action


@dataclass
class MarketState:
    """Current market state visible to agents."""
    # Prices
    underlying_price: float
    underlying_return: float      # Daily return
    underlying_drawdown: float    # Drawdown from recent high
    
    # fToken state
    floor_price: float
    market_price: float
    premium: float                # (market - floor) / floor
    fpr: float                    # Floor protection ratio
    
    # Credit facility
    total_debt: float
    total_locked: float
    debt_utilization: float       # debt / debt_cap
    
    # Volume
    recent_buy_volume: float
    recent_sell_volume: float
    
    # Time
    step: int
    days_elapsed: float


@dataclass
class AgentPosition:
    """Tracks an agent's position and P&L."""
    tokens_held: float = 0.0
    tokens_locked: float = 0.0
    eth_balance: float = 0.0
    debt: float = 0.0
    entry_floor: float = 0.0      # Floor when first entered
    entry_price: float = 0.0      # Average entry price
    total_invested: float = 0.0   # Total ETH invested
    total_fees_paid: float = 0.0
    leverage_loops: int = 0
    # Tracking for profit-taking
    peak_value: float = 0.0       # High-water mark for profit calculation
    holding_days: int = 0         # Days held for aging
    total_sold: float = 0.0       # Total tokens sold (for volume tracking)
    
    @property
    def total_tokens(self) -> float:
        return self.tokens_held + self.tokens_locked
    
    @property
    def current_ltv(self) -> float:
        if self.tokens_locked == 0:
            return 0.0
        # LTV = debt / collateral_value
        # Collateral value at floor price
        collateral_value = self.tokens_locked * self.entry_floor  # Conservative
        return self.debt / collateral_value if collateral_value > 0 else 0.0
    
    def unrealized_pnl(self, current_floor: float) -> float:
        """Calculate unrealized P&L as percentage."""
        if self.entry_floor == 0 or self.total_tokens == 0:
            return 0.0
        return (current_floor - self.entry_floor) / self.entry_floor


class Agent(ABC):
    """
    Base agent class with position, capital, and decision-making.
    
    Each agent type implements decide_action() with its own logic.
    """
    
    def __init__(
        self,
        agent_id: int,
        agent_type: str,
        initial_eth: float = 10.0,
        params: Optional[Dict[str, Any]] = None
    ):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.position = AgentPosition(eth_balance=initial_eth)
        self.params = params or {}
        self.action_history: List[Tuple[int, Action]] = []
        
    @abstractmethod
    def decide_action(self, state: MarketState) -> Action:
        """
        Decide what action to take given current market state.
        
        Returns:
            Action to execute (or HOLD if no action)
        """
        pass
    
    def record_action(self, step: int, action: Action):
        """Record an action in history."""
        self.action_history.append((step, action))
    
    def update_position(
        self,
        tokens_delta: float = 0.0,
        eth_delta: float = 0.0,
        debt_delta: float = 0.0,
        locked_delta: float = 0.0,
        fees_paid: float = 0.0,
        floor_price: float = 0.0
    ):
        """Update agent's position after an action."""
        self.position.tokens_held += tokens_delta
        self.position.eth_balance += eth_delta
        self.position.debt += debt_delta
        self.position.tokens_locked += locked_delta
        self.position.total_fees_paid += fees_paid
        
        if floor_price > 0 and self.position.entry_floor == 0:
            self.position.entry_floor = floor_price
            
        if eth_delta < 0:  # Investment
            self.position.total_invested += abs(eth_delta)


class LeverageSeeker(Agent):
    """
    Aggressive leverage user who seeks maximum exposure when conditions are right.
    
    Behavior:
    - Enters with leverage when premium is low (< threshold)
    - Deleverages when underlying draws down significantly
    - Takes profits when gains exceed target
    - Re-levers when conditions improve
    
    Parameters:
    - target_ltv: Target LTV (default 85%)
    - deleverage_drawdown: Underlying drawdown that triggers deleverage (default 10%)
    - relever_premium_threshold: Premium below which to lever up (default 8%)
    - profit_target: Floor gain % to take profits (default 50%)
    - profit_take_fraction: Fraction to sell when taking profits (default 30%)
    """
    
    DEFAULT_PARAMS = {
        'target_ltv': 0.85,
        'deleverage_drawdown': 0.12,
        'relever_premium_threshold': 0.15,  # Lever up if premium < 15% (was 8%)
        'max_leverage_loops': 4,            # Up to 4 loops (was 3)
        'profit_target': 0.50,
        'profit_take_fraction': 0.30,
        'sell_premium_threshold': 0.25,     # Higher threshold (was 20%)
    }
    
    def __init__(self, agent_id: int, initial_eth: float = 10.0, params: Optional[Dict] = None):
        merged_params = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(agent_id, "LeverageSeeker", initial_eth, merged_params)
        self._is_deleveraged = False
    
    def decide_action(self, state: MarketState) -> Action:
        # 0. Update tracking
        self.position.holding_days += 1
        if self.position.total_tokens > 0:
            current_value = self.position.total_tokens * state.floor_price
            self.position.peak_value = max(self.position.peak_value, current_value)
        
        # 1. Check for deleverage trigger (stress conditions)
        if state.underlying_drawdown > self.params['deleverage_drawdown']:
            if self.position.debt > 0:
                self._is_deleveraged = True
                return Action(
                    ActionType.REPAY,
                    amount=self.position.debt,
                    reason=f"Deleveraging: drawdown {state.underlying_drawdown:.1%}"
                )
        
        # 2. Profit-taking: sell portion when gains exceed target
        if self.position.tokens_held > 0:
            pnl = self.position.unrealized_pnl(state.floor_price)
            if pnl > self.params['profit_target']:
                sell_amount = self.position.tokens_held * self.params['profit_take_fraction']
                return Action(
                    ActionType.SELL,
                    amount=sell_amount,
                    reason=f"Taking profits: {pnl:.1%} gain"
                )
        
        # 3. Sell some if premium is very high
        if self.position.tokens_held > 0 and state.premium > self.params['sell_premium_threshold']:
            sell_fraction = min(0.5, state.premium)  # Sell more at higher premium
            return Action(
                ActionType.SELL,
                amount=self.position.tokens_held * sell_fraction,
                reason=f"High premium exit: {state.premium:.1%}"
            )
        
        # 4. Check for re-leverage opportunity
        if self._is_deleveraged and state.premium < self.params['relever_premium_threshold']:
            if state.underlying_drawdown < self.params['deleverage_drawdown'] * 0.5:
                self._is_deleveraged = False
                return Action(
                    ActionType.LEVERAGE_LOOP,
                    loops=self.params['max_leverage_loops'],
                    reason=f"Re-levering: premium {state.premium:.1%}, recovery"
                )
        
        # 5. Initial entry if not positioned
        if self.position.total_tokens == 0 and self.position.eth_balance > 0:
            if state.premium < self.params['relever_premium_threshold']:
                return Action(
                    ActionType.BUY,
                    amount=self.position.eth_balance,
                    reason=f"Initial entry: premium {state.premium:.1%}"
                )
        
        # 6. Lever up if holding unleveraged - more aggressive
        if (self.position.tokens_held > 0 and 
            self.position.debt == 0 and 
            state.premium < self.params['relever_premium_threshold'] * 1.5 and  # Higher threshold
            not self._is_deleveraged):
            return Action(
                ActionType.LEVERAGE_LOOP,
                loops=self.params['max_leverage_loops'],
                reason=f"Levering up: premium low at {state.premium:.1%}"
            )
        
        return Action(ActionType.HOLD, reason="Waiting for opportunity")


class YieldSeeker(Agent):
    """
    Conservative holder who buys and holds for floor appreciation.
    
    Behavior:
    - Buys MORE aggressively when premium is low (better entry)
    - Holds for long periods
    - May use modest leverage when premium is very low
    - Sells portions when premium is high to take profits
    - Rebalances to maintain target allocation
    
    Parameters:
    - target_ltv: Conservative LTV (default 50%)
    - buy_premium_threshold: Max premium to buy at (default 5%)
    - sell_premium_threshold: Premium to start selling (default 15%)
    - aggressive_sell_premium: Premium for aggressive selling (default 25%)
    - target_token_allocation: Target % of portfolio in tokens (default 60%)
    """
    
    DEFAULT_PARAMS = {
        'target_ltv': 0.50,
        'buy_premium_threshold': 0.05,
        'sell_premium_threshold': 0.15,     # Start selling at 15% premium
        'aggressive_sell_premium': 0.25,    # Aggressive sell at 25%+
        'hold_probability': 0.50,           # 50% chance to act per step (was 70%)
        'daily_trade_fraction': 0.15,       # Trade 15% when active (was 8%)
        'target_token_allocation': 0.60,    # Target 60% in tokens
        'profit_take_threshold': 0.30,      # Take profits at 30% unrealized gain
    }
    
    def __init__(self, agent_id: int, initial_eth: float = 10.0, params: Optional[Dict] = None):
        merged_params = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(agent_id, "YieldSeeker", initial_eth, merged_params)
    
    def decide_action(self, state: MarketState) -> Action:
        # Update tracking
        self.position.holding_days += 1
        
        # Calculate current allocation
        token_value = self.position.tokens_held * state.floor_price
        total_value = token_value + self.position.eth_balance
        token_allocation = token_value / total_value if total_value > 0 else 0
        
        # Random activity check
        if np.random.random() < self.params['hold_probability']:
            return Action(ActionType.HOLD, reason="Passive holding")
        
        # 1. SELL LOGIC - Premium-based profit taking
        if self.position.tokens_held > 0:
            # Aggressive sell at high premium
            if state.premium > self.params['aggressive_sell_premium']:
                sell_fraction = 0.4 + (state.premium - 0.25) * 2  # More at higher premium
                sell_fraction = min(0.6, sell_fraction)
                return Action(
                    ActionType.SELL,
                    amount=self.position.tokens_held * sell_fraction,
                    reason=f"High premium profit-taking: {state.premium:.1%}"
                )
            
            # Moderate sell at elevated premium
            if state.premium > self.params['sell_premium_threshold']:
                sell_fraction = 0.15 + state.premium * 0.5  # Scale with premium
                return Action(
                    ActionType.SELL,
                    amount=self.position.tokens_held * sell_fraction,
                    reason=f"Premium profit-taking: {state.premium:.1%}"
                )
            
            # Rebalancing sell if over-allocated to tokens
            if token_allocation > self.params['target_token_allocation'] + 0.15:
                rebalance_amount = (token_allocation - self.params['target_token_allocation']) * token_value / state.floor_price
                return Action(
                    ActionType.SELL,
                    amount=min(rebalance_amount, self.position.tokens_held * 0.2),
                    reason=f"Rebalancing: {token_allocation:.0%} -> {self.params['target_token_allocation']:.0%}"
                )
        
        # 2. BUY LOGIC - More aggressive when premium is low
        if self.position.eth_balance > 0:
            if state.premium < 0:  # Below floor - very attractive
                return Action(
                    ActionType.BUY,
                    amount=self.position.eth_balance * 0.5,
                    reason=f"Below floor discount: {state.premium:.1%}"
                )
            
            if state.premium < self.params['buy_premium_threshold']:
                # Scale buy size inversely with premium
                buy_fraction = self.params['daily_trade_fraction'] * (1 + (0.05 - state.premium) * 5)
                buy_fraction = min(0.3, buy_fraction)
                return Action(
                    ActionType.BUY,
                    amount=self.position.eth_balance * buy_fraction,
                    reason=f"Low premium entry: {state.premium:.1%}"
                )
        
        # 3. Leverage at low premium (capital efficiency) - more aggressive
        if (self.position.tokens_held > 0 and 
            self.position.debt == 0 and 
            state.premium < self.params['buy_premium_threshold']):  # Use same threshold as buy
            return Action(
                ActionType.BORROW,
                amount=self.position.tokens_held * state.floor_price * self.params['target_ltv'],
                reason=f"Capital efficiency leverage: premium {state.premium:.1%}"
            )
        
        return Action(ActionType.HOLD, reason="Waiting for opportunity")


class DATAgent(Agent):
    """
    Dollar-cost Averaging Token agent with long time horizon.
    
    Estimates future floor price based on expected fee generation
    and buys when market price is below discounted future floor.
    Sells when overvalued or as horizon approaches.
    
    Uses a blended model:
    - Historical fee growth rate (if available)
    - Simple growth rate assumption
    
    Parameters:
    - horizon_years: Investment horizon (default 5)
    - discount_rate: Annual discount rate (default 10%)
    - expected_floor_growth: Annual floor growth assumption (default 5%)
    - buy_discount_threshold: Buy when price < fair_value * (1 - threshold) (default 5%)
    - sell_premium_threshold: Sell when premium > threshold (default 20%)
    - overvalued_threshold: Sell when market > fair_value * (1 + threshold) (default 15%)
    """
    
    DEFAULT_PARAMS = {
        'horizon_years': 5.0,
        'discount_rate': 0.10,
        'expected_floor_growth': 0.05,
        'buy_discount_threshold': 0.05,
        'historical_weight': 0.30,
        'target_ltv': 0.25,
        'daily_buy_probability': 0.25,   # 25% chance to buy per day (was 12%)
        'daily_trade_fraction': 0.15,    # Trade 15% of holdings when active (was 6%)
        'sell_premium_threshold': 0.20,  # Sell portion at 20%+ premium
        'overvalued_threshold': 0.15,    # Sell when 15% above fair value
        'max_position_pct': 0.70,        # Max 70% of portfolio in tokens
    }
    
    def __init__(self, agent_id: int, initial_eth: float = 10.0, params: Optional[Dict] = None):
        merged_params = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(agent_id, "DAT", initial_eth, merged_params)
        self._historical_floor_growth: Optional[float] = None
    
    def update_historical_growth(self, growth_rate: float):
        """Update the observed historical floor growth rate."""
        self._historical_floor_growth = growth_rate
    
    def estimate_future_floor(self, current_floor: float, years: float) -> float:
        """
        Estimate floor price N years from now.
        
        Uses blended model: weighted average of historical and assumed growth.
        """
        assumed_growth = self.params['expected_floor_growth']
        
        if self._historical_floor_growth is not None:
            # Blend historical and assumed
            weight = self.params['historical_weight']
            growth_rate = weight * self._historical_floor_growth + (1 - weight) * assumed_growth
        else:
            growth_rate = assumed_growth
        
        return current_floor * (1 + growth_rate) ** years
    
    def calculate_fair_value(self, state: MarketState) -> float:
        """Calculate fair value based on discounted future floor."""
        future_floor = self.estimate_future_floor(
            state.floor_price, 
            self.params['horizon_years']
        )
        
        # Discount to present value
        discount_rate = self.params['discount_rate']
        fair_value = future_floor / (1 + discount_rate) ** self.params['horizon_years']
        
        return fair_value
    
    def decide_action(self, state: MarketState) -> Action:
        # Update tracking
        self.position.holding_days += 1
        
        fair_value = self.calculate_fair_value(state)
        buy_threshold = fair_value * (1 - self.params['buy_discount_threshold'])
        sell_threshold = fair_value * (1 + self.params['overvalued_threshold'])
        
        # Calculate portfolio allocation
        token_value = self.position.tokens_held * state.floor_price
        total_value = token_value + self.position.eth_balance
        token_pct = token_value / total_value if total_value > 0 else 0
        
        # 1. SELL LOGIC - Premium and overvaluation based
        if self.position.tokens_held > 0:
            # Sell at high premium (short-term opportunity)
            if state.premium > self.params['sell_premium_threshold']:
                sell_fraction = 0.15 + (state.premium - 0.20) * 1.5
                sell_fraction = min(0.4, sell_fraction)
                return Action(
                    ActionType.SELL,
                    amount=self.position.tokens_held * sell_fraction,
                    reason=f"Premium profit-taking: {state.premium:.1%}"
                )
            
            # Sell if market price significantly above fair value
            if state.market_price > sell_threshold:
                overvaluation = (state.market_price - fair_value) / fair_value
                sell_fraction = min(0.3, 0.1 + overvaluation * 0.5)
                return Action(
                    ActionType.SELL,
                    amount=self.position.tokens_held * sell_fraction,
                    reason=f"Overvalued: market ${state.market_price:.3f} > fair ${fair_value:.3f}"
                )
            
            # Rebalance if over-allocated
            if token_pct > self.params['max_position_pct']:
                rebalance_tokens = (token_pct - self.params['max_position_pct']) * total_value / state.floor_price
                return Action(
                    ActionType.SELL,
                    amount=min(rebalance_tokens, self.position.tokens_held * 0.25),
                    reason=f"Rebalancing: {token_pct:.0%} -> {self.params['max_position_pct']:.0%}"
                )
        
        # 2. BUY LOGIC - Value-based accumulation
        if self.position.eth_balance > 0:
            # Strong buy if market price below fair value
            if state.market_price < buy_threshold:
                discount = (buy_threshold - state.market_price) / buy_threshold
                buy_fraction = min(0.5, 0.15 + discount)
                
                return Action(
                    ActionType.BUY,
                    amount=self.position.eth_balance * buy_fraction,
                    reason=f"Undervalued: market ${state.market_price:.3f} < fair ${fair_value:.3f}"
                )
            
            # DCA at low premium even at fair value
            if state.premium < 0.05 and np.random.random() < self.params.get('daily_buy_probability', 0.1):
                trade_fraction = self.params.get('daily_trade_fraction', 0.06)
                return Action(
                    ActionType.BUY,
                    amount=self.position.eth_balance * trade_fraction,
                    reason="DCA: low premium accumulation"
                )
        
        # 3. Conservative leverage at deep discount
        if (self.position.tokens_held > 0 and 
            self.position.debt == 0 and 
            state.market_price < fair_value * 0.85 and
            state.premium < 0.03):
            max_borrow = self.position.tokens_held * state.floor_price * self.params['target_ltv']
            return Action(
                ActionType.BORROW,
                amount=max_borrow,
                reason="Conservative leverage at deep discount"
            )
        
        return Action(ActionType.HOLD, reason=f"Fair value: ${fair_value:.3f}")


class Arbitrageur(Agent):
    """
    Short-term speculator who exploits price inefficiencies.
    
    Behavior:
    - Buys aggressively when premium is low/negative
    - Sells quickly when premium rises (short holding period)
    - Uses premium levels to scale position sizes
    - Time-based exit if position stale
    
    Parameters:
    - min_buy_spread: Buy threshold (low/negative premium)
    - min_sell_premium: Sell threshold (default 10%)
    - aggressive_sell_premium: Full exit threshold (default 20%)
    - max_holding_days: Exit even if unprofitable (default 14)
    """
    
    DEFAULT_PARAMS = {
        'min_buy_spread': 0.03,           # Buy when premium < 3%
        'min_sell_premium': 0.10,         # Start selling at 10% premium
        'aggressive_sell_premium': 0.20,  # Full exit at 20%+
        'position_size_pct': 0.50,        # Position size as % of capital (was 25%)
        'max_holding_days': 14,           # Max days to hold before exit
        'target_ltv': 0.0,                # No leverage
    }
    
    def __init__(self, agent_id: int, initial_eth: float = 10.0, params: Optional[Dict] = None):
        merged_params = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(agent_id, "Arbitrageur", initial_eth, merged_params)
        self._entry_day = 0
    
    def decide_action(self, state: MarketState) -> Action:
        # Track holding period
        self.position.holding_days += 1
        
        # 1. SELL LOGIC (Priority - arbs are profit-focused)
        if self.position.tokens_held > 0:
            # Aggressive sell at high premium - full exit
            if state.premium > self.params['aggressive_sell_premium']:
                return Action(
                    ActionType.SELL,
                    amount=self.position.tokens_held,
                    reason=f"Full exit at {state.premium:.1%} premium"
                )
            
            # Partial sell at moderate premium
            if state.premium > self.params['min_sell_premium']:
                sell_fraction = 0.5 + (state.premium - 0.10) * 2
                sell_fraction = min(0.8, sell_fraction)
                return Action(
                    ActionType.SELL,
                    amount=self.position.tokens_held * sell_fraction,
                    reason=f"Profit-taking at {state.premium:.1%} premium"
                )
            
            # Time-based exit - don't hold too long
            days_held = self.position.holding_days - self._entry_day
            if days_held > self.params['max_holding_days']:
                return Action(
                    ActionType.SELL,
                    amount=self.position.tokens_held,
                    reason=f"Time exit after {days_held} days"
                )
        
        # 2. BUY LOGIC - Opportunistic at low premium
        if self.position.eth_balance > 0:
            # Strong buy at negative premium (below floor)
            if state.premium < 0:
                buy_amount = self.position.eth_balance * 0.6  # Large position
                self._entry_day = self.position.holding_days
                return Action(
                    ActionType.BUY,
                    amount=buy_amount,
                    reason=f"Below floor: {state.premium:.1%}"
                )
            
            # Buy at very low premium
            if state.premium < self.params['min_buy_spread']:
                buy_fraction = self.params['position_size_pct'] * (1 + (0.03 - state.premium) * 10)
                buy_fraction = min(0.5, buy_fraction)
                self._entry_day = self.position.holding_days
                return Action(
                    ActionType.BUY,
                    amount=self.position.eth_balance * buy_fraction,
                    reason=f"Low premium entry: {state.premium:.1%}"
                )
            
            # Buy if strong volume imbalance suggests floor rise
            if (state.premium < 0.08 and 
                state.recent_buy_volume > state.recent_sell_volume * 2.0):
                buy_amount = self.position.eth_balance * self.params['position_size_pct']
                self._entry_day = self.position.holding_days
                return Action(
                    ActionType.BUY,
                    amount=buy_amount,
                    reason="Volume imbalance: anticipating premium expansion"
                )
        
        return Action(ActionType.HOLD, reason="No arb opportunity")


class FloorHolder(Agent):
    """
    Credit facility user who uses fTokens for capital efficiency.
    
    Behavior:
    - Holds fTokens as productive collateral
    - Borrows at target LTV for capital efficiency
    - Tops up when floor rises (new headroom available)
    - Doesn't actively trade
    
    Parameters:
    - target_ltv: Target LTV to maintain (default 70%)
    - topup_threshold: Floor rise % to trigger topup (default 2%)
    - entry_premium_max: Max premium to enter at (default 10%)
    """
    
    DEFAULT_PARAMS = {
        'target_ltv': 0.70,
        'topup_threshold': 0.02,
        'entry_premium_max': 0.10,
    }
    
    def __init__(self, agent_id: int, initial_eth: float = 10.0, params: Optional[Dict] = None):
        merged_params = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(agent_id, "FloorHolder", initial_eth, merged_params)
        self._last_topup_floor: float = 0.0
    
    def decide_action(self, state: MarketState) -> Action:
        # 1. Initial entry: buy and lever up
        if self.position.total_tokens == 0 and self.position.eth_balance > 0:
            if state.premium < self.params['entry_premium_max']:
                return Action(
                    ActionType.BUY,
                    amount=self.position.eth_balance,
                    reason=f"Initial entry at {state.premium:.1%} premium"
                )
        
        # 2. Initial leverage after buying
        if (self.position.tokens_held > 0 and 
            self.position.debt == 0):
            self._last_topup_floor = state.floor_price
            return Action(
                ActionType.BORROW,
                amount=self.position.tokens_held * state.floor_price * self.params['target_ltv'],
                reason="Initial leverage for capital efficiency"
            )
        
        # 3. Top-up when floor rises (headroom created)
        if self.position.debt > 0 and self._last_topup_floor > 0:
            floor_rise = (state.floor_price - self._last_topup_floor) / self._last_topup_floor
            
            if floor_rise >= self.params['topup_threshold']:
                # Calculate headroom
                current_collateral = self.position.tokens_locked * state.floor_price
                target_debt = current_collateral * self.params['target_ltv']
                headroom = max(0, target_debt - self.position.debt)
                
                if headroom > 0:
                    self._last_topup_floor = state.floor_price
                    return Action(
                        ActionType.TOPUP,
                        amount=headroom,
                        reason=f"Floor rose {floor_rise:.1%}, topping up"
                    )
        
        return Action(ActionType.HOLD, reason="Holding collateral position")


# Agent factory
AGENT_TYPES = {
    'LeverageSeeker': LeverageSeeker,
    'YieldSeeker': YieldSeeker,
    'DAT': DATAgent,
    'Arbitrageur': Arbitrageur,
    'FloorHolder': FloorHolder,
}


def create_agent(
    agent_type: str,
    agent_id: int,
    initial_eth: float = 10.0,
    params: Optional[Dict] = None
) -> Agent:
    """Factory function to create agents by type."""
    if agent_type not in AGENT_TYPES:
        raise ValueError(f"Unknown agent type: {agent_type}. Available: {list(AGENT_TYPES.keys())}")
    
    return AGENT_TYPES[agent_type](agent_id, initial_eth, params)


def create_population(
    population_config: Dict[str, Dict[str, Any]],
    base_eth: float = 10.0
) -> List[Agent]:
    """
    Create a population of agents from a config.
    
    Args:
        population_config: Dict mapping agent_type to config with 'count' and 'params'
        base_eth: Base ETH per agent (can be overridden in params)
        
    Returns:
        List of Agent instances
    """
    agents = []
    agent_id = 1
    
    for agent_type, config in population_config.items():
        count = config.get('count', 0)
        params = config.get('params', {})
        eth = config.get('initial_eth', base_eth)
        
        # Slight randomization of ETH amounts for realism
        for _ in range(count):
            actual_eth = eth * (0.5 + np.random.random())  # 50-150% of base
            agent = create_agent(agent_type, agent_id, actual_eth, params)
            agents.append(agent)
            agent_id += 1
    
    return agents
