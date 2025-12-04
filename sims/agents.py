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
    - Re-levers when conditions improve
    
    Parameters:
    - target_ltv: Target LTV (default 85%)
    - deleverage_drawdown: Underlying drawdown that triggers deleverage (default 10%)
    - relever_premium_threshold: Premium below which to lever up (default 8%)
    """
    
    DEFAULT_PARAMS = {
        'target_ltv': 0.85,
        'deleverage_drawdown': 0.10,
        'relever_premium_threshold': 0.08,
        'max_leverage_loops': 3,
    }
    
    def __init__(self, agent_id: int, initial_eth: float = 10.0, params: Optional[Dict] = None):
        merged_params = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(agent_id, "LeverageSeeker", initial_eth, merged_params)
        self._is_deleveraged = False
    
    def decide_action(self, state: MarketState) -> Action:
        # 1. Check for deleverage trigger (stress conditions)
        if state.underlying_drawdown > self.params['deleverage_drawdown']:
            if self.position.debt > 0:
                self._is_deleveraged = True
                return Action(
                    ActionType.REPAY,
                    amount=self.position.debt,
                    reason=f"Deleveraging: drawdown {state.underlying_drawdown:.1%}"
                )
        
        # 2. Check for re-leverage opportunity
        if self._is_deleveraged and state.premium < self.params['relever_premium_threshold']:
            if state.underlying_drawdown < self.params['deleverage_drawdown'] * 0.5:
                self._is_deleveraged = False
                return Action(
                    ActionType.LEVERAGE_LOOP,
                    loops=self.params['max_leverage_loops'],
                    reason=f"Re-levering: premium {state.premium:.1%}, recovery"
                )
        
        # 3. Initial entry if not positioned
        if self.position.total_tokens == 0 and self.position.eth_balance > 0:
            if state.premium < self.params['relever_premium_threshold']:
                return Action(
                    ActionType.BUY,
                    amount=self.position.eth_balance,
                    reason=f"Initial entry: premium {state.premium:.1%}"
                )
        
        # 4. Lever up if holding unleveraged
        if (self.position.tokens_held > 0 and 
            self.position.debt == 0 and 
            state.premium < self.params['relever_premium_threshold'] and
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
    - Buys when price is reasonable (low premium)
    - Holds for long periods
    - May use modest leverage for capital efficiency
    - Rarely sells, only in extreme premium
    
    Parameters:
    - target_ltv: Conservative LTV (default 50%)
    - buy_premium_threshold: Max premium to buy at (default 5%)
    - sell_premium_threshold: Premium to consider selling (default 30%)
    - hold_probability: Probability of holding vs acting (default 95%)
    """
    
    DEFAULT_PARAMS = {
        'target_ltv': 0.50,
        'buy_premium_threshold': 0.05,
        'sell_premium_threshold': 0.30,
        'hold_probability': 0.80,  # 20% chance to act per step
        'daily_trade_fraction': 0.05,  # Trade 5% of holdings per active day
    }
    
    def __init__(self, agent_id: int, initial_eth: float = 10.0, params: Optional[Dict] = None):
        merged_params = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(agent_id, "YieldSeeker", initial_eth, merged_params)
    
    def decide_action(self, state: MarketState) -> Action:
        # Probability-based activity (allows recurring trading)
        if np.random.random() < self.params['hold_probability']:
            return Action(ActionType.HOLD, reason="Passive holding")
        
        # 1. Buy if premium is attractive and have ETH
        if self.position.eth_balance > 0 and state.premium < self.params['buy_premium_threshold']:
            # Trade a fraction of holdings for DCA behavior
            trade_fraction = self.params.get('daily_trade_fraction', 0.1)
            return Action(
                ActionType.BUY,
                amount=self.position.eth_balance * trade_fraction,
                reason=f"DCA entry: premium {state.premium:.1%}"
            )
        
        # 2. Consider modest leverage if positioned and premium low
        if (self.position.tokens_held > 0 and 
            self.position.debt == 0 and 
            state.premium < self.params['buy_premium_threshold'] * 0.5):
            return Action(
                ActionType.BORROW,
                amount=self.position.tokens_held * state.floor_price * self.params['target_ltv'],
                reason=f"Capital efficiency: conservative borrow"
            )
        
        # 3. Consider selling if premium is extreme (rare)
        if (self.position.tokens_held > 0 and 
            state.premium > self.params['sell_premium_threshold']):
            return Action(
                ActionType.SELL,
                amount=self.position.tokens_held * 0.25,
                reason=f"Premium too high: {state.premium:.1%}"
            )
        
        # 4. Rebalance by buying if no other action
        if self.position.eth_balance > 0:
            trade_fraction = self.params.get('daily_trade_fraction', 0.1)
            return Action(
                ActionType.BUY,
                amount=self.position.eth_balance * trade_fraction,
                reason="Rebalancing: deploying idle capital"
            )
        
        return Action(ActionType.HOLD, reason="Fully deployed")


class DATAgent(Agent):
    """
    Dollar-cost Averaging Token agent with long time horizon.
    
    Estimates future floor price based on expected fee generation
    and buys when market price is below discounted future floor.
    
    Uses a blended model:
    - Historical fee growth rate (if available)
    - Simple growth rate assumption
    
    Parameters:
    - horizon_years: Investment horizon (default 5)
    - discount_rate: Annual discount rate (default 10%)
    - expected_floor_growth: Annual floor growth assumption (default 5%)
    - buy_discount_threshold: Buy when price < fair_value * (1 - threshold) (default 5%)
    - historical_weight: Weight for historical data vs assumption (default 0.3)
    """
    
    DEFAULT_PARAMS = {
        'horizon_years': 5.0,
        'discount_rate': 0.10,
        'expected_floor_growth': 0.05,
        'buy_discount_threshold': 0.05,
        'historical_weight': 0.30,
        'target_ltv': 0.25,
        'daily_buy_probability': 0.15,  # 15% chance to buy per day
        'daily_trade_fraction': 0.08,   # Trade 8% of holdings when active
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
        fair_value = self.calculate_fair_value(state)
        buy_threshold = fair_value * (1 - self.params['buy_discount_threshold'])
        
        # 1. Buy if market price is below discounted fair value
        if self.position.eth_balance > 0 and state.market_price < buy_threshold:
            discount = (buy_threshold - state.market_price) / buy_threshold
            buy_fraction = min(0.5, 0.1 + discount)
            
            return Action(
                ActionType.BUY,
                amount=self.position.eth_balance * buy_fraction,
                reason=f"Undervalued: market ${state.market_price:.3f} < fair ${fair_value:.3f}"
            )
        
        # 2. DCA behavior - periodic buying even at fair value
        if (self.position.eth_balance > 0 and 
            np.random.random() < self.params.get('daily_buy_probability', 0.1)):
            trade_fraction = self.params.get('daily_trade_fraction', 0.08)
            return Action(
                ActionType.BUY,
                amount=self.position.eth_balance * trade_fraction,
                reason="DCA: periodic accumulation"
            )
        
        # 3. Consider very modest leverage if positioned
        if (self.position.tokens_held > 0 and 
            self.position.debt == 0 and 
            state.market_price < fair_value * 0.90):
            max_borrow = self.position.tokens_held * state.floor_price * self.params['target_ltv']
            return Action(
                ActionType.BORROW,
                amount=max_borrow,
                reason="Conservative leverage at deep discount"
            )
        
        return Action(ActionType.HOLD, reason=f"Fair value: ${fair_value:.3f}")


class Arbitrageur(Agent):
    """
    Arbitrageur who exploits price inefficiencies.
    
    Behavior:
    - Buys when market < expected floor (anticipating floor rise)
    - Sells when premium is high
    - Quick turnover, not long-term holder
    
    Parameters:
    - min_buy_spread: Min discount to floor to buy (default 2%)
    - min_sell_premium: Min premium to sell (default 15%)
    - position_size_pct: Position size as % of capital (default 20%)
    """
    
    DEFAULT_PARAMS = {
        'min_buy_spread': 0.02,
        'min_sell_premium': 0.15,
        'position_size_pct': 0.20,
        'target_ltv': 0.0,  # No leverage
    }
    
    def __init__(self, agent_id: int, initial_eth: float = 10.0, params: Optional[Dict] = None):
        merged_params = {**self.DEFAULT_PARAMS, **(params or {})}
        super().__init__(agent_id, "Arbitrageur", initial_eth, merged_params)
    
    def decide_action(self, state: MarketState) -> Action:
        # 1. Sell if holding and premium is high
        if self.position.tokens_held > 0 and state.premium > self.params['min_sell_premium']:
            return Action(
                ActionType.SELL,
                amount=self.position.tokens_held,  # Full exit
                reason=f"Taking profit: premium {state.premium:.1%}"
            )
        
        # 2. Buy if price is at/below floor (rare but possible)
        if self.position.eth_balance > 0 and state.premium < -self.params['min_buy_spread']:
            position_size = self.position.eth_balance * self.params['position_size_pct']
            return Action(
                ActionType.BUY,
                amount=position_size,
                reason=f"Below floor: discount {-state.premium:.1%}"
            )
        
        # 3. Buy if anticipating floor rise (low premium + high fee activity)
        if (self.position.eth_balance > 0 and 
            state.premium < self.params['min_buy_spread'] and
            state.recent_buy_volume > state.recent_sell_volume * 1.5):  # Net buying
            position_size = self.position.eth_balance * self.params['position_size_pct']
            return Action(
                ActionType.BUY,
                amount=position_size,
                reason=f"Anticipating floor rise: strong buying"
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
