"""
Agent-Based Simulation Engine

Integrates presale phase and agent-based modeling with the fToken simulation.
Supports both presale → live market transitions and pure agent-based runs.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

from .models import Underlying, LST, fToken
from .presale import PresalePhase, PresaleConfig
from .agents import (
    Agent, Action, ActionType, MarketState,
    create_population, AGENT_TYPES
)


def scale_agents_to_volume(
    agents: List[Agent],
    daily_volume_target: float,
    horizon_days: int = 90,
    turnover_rate: float = 0.10
) -> List[Agent]:
    """
    Scale agent ETH balances to match a target daily trading volume.
    
    The logic:
    - Each agent trades a fraction of their holdings per day
    - turnover_rate = average fraction traded per day (default 10%)
    - Total daily volume ≈ total_agent_eth * turnover_rate
    - Scale factor = daily_volume_target / (current_total_eth * turnover_rate)
    
    Args:
        agents: List of agents to scale
        daily_volume_target: Target average daily volume (ETH)
        horizon_days: Simulation horizon (for reference)
        turnover_rate: Expected fraction of holdings traded per day
        
    Returns:
        The same agents with scaled ETH balances
    """
    if not agents:
        return agents
    
    # Calculate current total ETH
    current_total_eth = sum(a.position.eth_balance for a in agents)
    
    if current_total_eth <= 0:
        return agents
    
    # Expected daily volume from current holdings
    expected_daily_volume = current_total_eth * turnover_rate
    
    # Scale factor needed
    scale_factor = daily_volume_target / expected_daily_volume
    
    # Apply scaling
    for agent in agents:
        agent.position.eth_balance *= scale_factor
    
    return agents


def calibrate_from_scenario(
    agents: List[Agent],
    scenario_config: Dict[str, Any]
) -> List[Agent]:
    """
    Calibrate agent inventories based on scenario parameters.
    
    Uses scenario's daily_volume_mean to scale agent holdings.
    
    Observed turnover rates are ~1.5-2.5% daily based on agent behavior:
    - YieldSeeker: 20% active × 5% trade = ~1% daily
    - DAT: 15% active × 8% trade = ~1.2% daily
    - Others: one-time entry pattern
    
    Args:
        agents: List of agents
        scenario_config: Scenario configuration dict
        
    Returns:
        Agents with calibrated ETH balances
    """
    daily_volume = scenario_config.get('daily_volume_mean', 50000)
    horizon_days = scenario_config.get('horizon_days', 90)
    
    # Realistic turnover based on observed agent behavior (~1.5-2.5%)
    mu = scenario_config.get('mu', 0.0)
    if mu > 0.3:
        turnover = 0.025  # Bull: higher activity
    elif mu < -0.3:
        turnover = 0.012  # Bear: lower turnover  
    else:
        turnover = 0.018  # Neutral
    
    return scale_agents_to_volume(agents, daily_volume, horizon_days, turnover)


@dataclass
class ChurnConfig:
    """Configuration for agent churn (exits and entries)."""
    enabled: bool = True
    
    # Exit triggers
    profit_exit_threshold: float = 0.50    # Exit probability peaks at 50%+ profit
    loss_exit_threshold: float = -0.30     # Exit if down 30%+
    max_holding_days: int = 180            # Max days before considering exit
    base_exit_probability: float = 0.01   # 1% base daily exit probability
    
    # Entry parameters
    new_entrant_eth_mean: float = 100.0    # Mean ETH for new entrants
    new_entrant_eth_std: float = 50.0      # Std dev for new entrant ETH
    
    # Population targets
    maintain_population: bool = True       # Replace exiting agents


def should_agent_exit(
    agent: Agent,
    state: MarketState,
    config: ChurnConfig
) -> bool:
    """
    Determine if an agent should exit the market.
    
    Exit triggers:
    1. Profit target reached (scales with profit level)
    2. Stop-loss hit
    3. Time-based exit (random after max holding days)
    """
    # No position to exit
    if agent.position.total_tokens <= 0 and agent.position.eth_balance <= 0:
        return False
    
    # Calculate P&L
    if agent.position.entry_floor > 0 and agent.position.total_tokens > 0:
        pnl = (state.floor_price - agent.position.entry_floor) / agent.position.entry_floor
    else:
        pnl = 0.0
    
    # 1. Profit-taking exit (probability scales with profit)
    if pnl > config.profit_exit_threshold:
        # Higher profit = higher exit probability
        exit_prob = min(0.3, 0.05 + (pnl - config.profit_exit_threshold) * 0.5)
        if np.random.random() < exit_prob:
            return True
    
    # 2. Stop-loss exit
    if pnl < config.loss_exit_threshold:
        if np.random.random() < 0.15:  # 15% chance to cut losses
            return True
    
    # 3. Time-based exit (for aged positions)
    if agent.position.holding_days > config.max_holding_days:
        # Probability increases with time over max
        age_factor = (agent.position.holding_days - config.max_holding_days) / config.max_holding_days
        exit_prob = min(0.1, config.base_exit_probability + age_factor * 0.02)
        if np.random.random() < exit_prob:
            return True
    
    # 4. Base exit probability (random churn)
    if np.random.random() < config.base_exit_probability:
        return True
    
    return False


def create_new_entrant(
    agent_id: int,
    agent_type: str,
    config: ChurnConfig,
    market_state: MarketState
) -> Agent:
    """
    Create a new entrant agent with fresh capital.
    
    New entrants start with:
    - No existing position
    - Fresh ETH allocation
    - Some tokens already purchased (fresh money entry)
    """
    from .agents import create_agent
    
    # Random ETH allocation
    eth = max(10.0, np.random.normal(config.new_entrant_eth_mean, config.new_entrant_eth_std))
    
    # Create fresh agent
    agent = create_agent(agent_type, agent_id, eth)
    
    # New entrants are eager - they buy based on premium attractiveness
    # This simulates "fresh money" entering the market
    if market_state.premium < 0.25:  # Buy if premium < 25%
        # Buy more at lower premium, but cap lower to reduce supply growth
        buy_fraction = 0.2 + (0.25 - market_state.premium) * 1.5
        buy_fraction = min(0.6, buy_fraction)  # Cap at 60%
        
        buy_amount = eth * buy_fraction
        tokens_to_receive = buy_amount / market_state.market_price * 0.995  # After fee
        
        agent.position.eth_balance -= buy_amount
        agent.position.tokens_held = tokens_to_receive
        agent.position.entry_floor = market_state.floor_price
        agent.position.entry_price = market_state.market_price
        agent.position.total_invested = buy_amount
    
    return agent


def process_agent_exit(
    agent: Agent,
    ftoken: 'fToken',
    state: MarketState
) -> float:
    """
    Process an agent's full exit from the market.
    
    Sells all tokens, repays all debt, returns ETH received.
    """
    eth_received = 0.0
    
    # First repay any debt
    if agent.position.debt > 0:
        # Need to unlock collateral and repay
        # For simplicity, we assume they use ETH to repay
        repay_amount = agent.position.debt
        if agent.position.eth_balance >= repay_amount:
            success, fee = ftoken.repay_loan_simple(
                agent.position.debt,
                agent.position.tokens_locked
            )
            if success:
                agent.position.tokens_held += agent.position.tokens_locked
                agent.position.tokens_locked = 0
                agent.position.eth_balance -= repay_amount
                agent.position.debt = 0
    
    # Sell all tokens
    if agent.position.tokens_held > 0:
        eth_out, fee, success = ftoken.sell(agent.position.tokens_held)
        if success:
            eth_received = eth_out
            agent.position.eth_balance += eth_out
            agent.position.tokens_held = 0
    
    return eth_received




@dataclass
class AgentSimConfig:
    """Configuration for agent-based simulation."""
    # Simulation structure
    n_paths: int = 100
    horizon_days: int = 90
    dt: float = 1/365
    
    # Presale phase (optional)
    run_presale: bool = False
    presale_config: Optional[PresaleConfig] = None
    
    # Underlying asset
    initial_price: float = 100.0
    mu: float = 0.0
    sigma: float = 0.5
    
    # LST parameters
    staking_yield: float = 0.05
    p_depeg: float = 0.001
    depeg_mean: float = -0.05
    depeg_std: float = 0.02
    
    # fToken initial state (overridden if presale runs)
    initial_reserves: float = 1100000
    initial_supply: float = 1000000
    initial_floor: float = 1.0
    
    # fToken fees (0.5% each direction)
    buy_fee: float = 0.005
    sell_fee: float = 0.005
    origination_fee: float = 0.02
    fee_to_floor_ratio: float = 0.70
    
    # fToken governance
    debt_cap_bps: int = 5000
    min_coverage_buffer_bps: int = 500
    elevation_threshold: float = 1.0  # Elevate floor when ~1 ETH in fees collected
    tick_size: float = 0.01  # 1% per tick (matches protocol: 1.0 -> 1.01 -> 1.02)
    
    # LRE parameters
    lre_threshold: float = 2.0
    lre_realloc_bps: int = 2000
    
    # Agent population
    population_config: Optional[Dict[str, Dict[str, Any]]] = None
    
    # Agent churn (exits and entries)
    churn_config: Optional[ChurnConfig] = None


class AgentSimulationEngine:
    """
    Agent-based simulation engine.
    
    Supports:
    1. Presale phase (optional) with fixed pricing
    2. Agent-driven trading after presale
    3. Market state tracking for agent decisions
    """
    
    def __init__(
        self,
        config: AgentSimConfig,
        agents: Optional[List[Agent]] = None,
        population_config: Optional[Dict[str, Dict[str, Any]]] = None,
        scenario_config: Optional[Dict[str, Any]] = None
    ):
        self.config = config
        self.scenario_config = scenario_config  # Store for calibration
        
        # Create agents from population config if not provided directly
        if agents is not None:
            self.agents = agents
        elif population_config is not None:
            self.agents = create_population(population_config)
        elif config.population_config is not None:
            self.agents = create_population(config.population_config)
        else:
            self.agents = []
        
        # Calibrate agent inventories to match expected volume if scenario provided
        # Note: Calibration is disabled for now as it can lead to extreme scaling
        # Users should set appropriate agent inventories directly
        # if self.agents and scenario_config:
        #     self.agents = calibrate_from_scenario(self.agents, scenario_config)
        
        # Store original agent type distribution for churn
        self._agent_type_counts = {}
        for agent in self.agents:
            self._agent_type_counts[agent.agent_type] = \
                self._agent_type_counts.get(agent.agent_type, 0) + 1
        
        # Churn tracking
        self._next_agent_id = len(self.agents) + 1
        self._churn_stats = {'exits': 0, 'entries': 0, 'exit_volume': 0.0}
        
        self.paths: List[pd.DataFrame] = []
        self.presale_results: Optional[Dict[str, Any]] = None
        
    def run(self) -> List[pd.DataFrame]:
        """
        Run the full simulation.
        
        Returns:
            List of DataFrames, one per path
        """
        n_paths = self.config.n_paths
        print(f"Starting agent-based simulation: {n_paths} paths, {len(self.agents)} agents...")
        
        self.paths = []
        
        for path_idx in range(n_paths):
            # Reset agents for each path
            self._reset_agents()
            
            # Run presale if configured
            if self.config.run_presale:
                self.presale_results = self._run_presale()
            
            # Run live market phase
            path_data = self._run_live_market()
            self.paths.append(path_data)
            
            if (path_idx + 1) % 10 == 0:
                print(f"Completed {path_idx + 1}/{n_paths} paths")
        
        print("Simulation complete.")
        return self.paths
    
    def _reset_agents(self):
        """Reset agent positions for a new path."""
        for agent in self.agents:
            # Store original ETH balance
            original_eth = agent.position.eth_balance + agent.position.total_invested
            agent.position = type(agent.position)(eth_balance=original_eth)
            agent.action_history = []
    
    def _run_presale(self) -> Dict[str, Any]:
        """
        Run the presale phase.
        
        Uses agents to participate in presale with fixed pricing.
        """
        config = self.config.presale_config or PresaleConfig()
        presale = PresalePhase(config)
        
        # Each agent decides whether to participate
        for agent in self.agents:
            if agent.position.eth_balance <= 0:
                continue
            
            # Participation rate varies by agent type
            participation_rates = {
                'LeverageSeeker': 0.90,  # Almost always participates
                'YieldSeeker': 0.60,
                'DAT': 0.80,  # Long-term holders see value
                'Arbitrageur': 0.30,  # Less interested in presale
                'FloorHolder': 0.70,
            }
            
            rate = participation_rates.get(agent.agent_type, 0.5)
            if np.random.random() > rate:
                continue
            
            # Mint initial tokens
            eth_to_spend = agent.position.eth_balance * np.random.uniform(0.3, 0.8)
            tokens, fee, participant = presale.mint(
                eth_to_spend, 
                agent.agent_type
            )
            
            # Update agent position
            agent.position.eth_balance -= eth_to_spend
            agent.position.tokens_held = tokens
            agent.position.total_fees_paid += fee
            agent.position.entry_floor = config.fixed_price
            agent.position.entry_price = config.fixed_price
            
            # Leverage seekers will loop
            if agent.agent_type == 'LeverageSeeker':
                loops = np.random.randint(2, 5)  # 2-4 loops
                loop_tokens, loop_debt, loop_fees = presale.leverage_loop(
                    participant, loops
                )
                agent.position.tokens_held += loop_tokens
                agent.position.tokens_locked = participant.tokens_locked
                agent.position.debt = loop_debt
                agent.position.total_fees_paid += loop_fees
                agent.position.leverage_loops = loops
            
            # Floor holders may do modest leverage
            elif agent.agent_type == 'FloorHolder':
                if np.random.random() < 0.6:  # 60% lever up
                    loops = np.random.randint(1, 2)
                    loop_tokens, loop_debt, loop_fees = presale.leverage_loop(
                        participant, loops
                    )
                    agent.position.tokens_held += loop_tokens
                    agent.position.tokens_locked = participant.tokens_locked
                    agent.position.debt = loop_debt
                    agent.position.total_fees_paid += loop_fees
                    agent.position.leverage_loops = loops
        
        # Close presale
        return presale.close()
    
    def _run_live_market(self) -> pd.DataFrame:
        """
        Run the live market phase with agent-driven activity.
        """
        # Initialize assets
        underlying = Underlying(
            name="AVAX",
            initial_price=self.config.initial_price,
            mu=self.config.mu,
            sigma=self.config.sigma
        )
        
        lst = LST(
            name="sAVAX",
            underlying=underlying,
            staking_yield=self.config.staking_yield,
            p_depeg_base=self.config.p_depeg,
            depeg_severity_mean=self.config.depeg_mean,
            depeg_severity_std=self.config.depeg_std
        )
        
        # Initialize fToken (possibly from presale results)
        if self.presale_results:
            ftoken = fToken(
                name="fAVAX",
                underlying=underlying,
                initial_reserves=self.presale_results['initial_reserves'],
                initial_supply=self.presale_results['initial_supply'],
                initial_floor=self.presale_results['initial_floor'],
                buy_fee=self.config.buy_fee,
                sell_fee=self.config.sell_fee,
                origination_fee=self.config.origination_fee,
                elevation_threshold=self.config.elevation_threshold,
                debt_cap_bps=self.config.debt_cap_bps,
                min_coverage_buffer_bps=self.config.min_coverage_buffer_bps,
                lre_threshold=self.config.lre_threshold,
                lre_realloc_bps=self.config.lre_realloc_bps,
                fee_to_floor_ratio=self.config.fee_to_floor_ratio,
                tick_size=self.config.tick_size,
            )
            
            # Apply presale state
            ftoken.locked_supply = self.presale_results['locked_supply']
            ftoken.debt = self.presale_results['total_debt']
            
            # Presale fee split: 50% to team, 50% to floor elevation
            presale_fees = self.presale_results['pending_fees']
            team_share = presale_fees * 0.50
            floor_share = presale_fees * 0.50
            
            ftoken.team_fees_accumulated += team_share
            ftoken.pending_fees = floor_share
            
            # Process initial elevation from presale fees
            ftoken.process_elevation()
        else:
            ftoken = fToken(
                name="fAVAX",
                underlying=underlying,
                initial_reserves=self.config.initial_reserves,
                initial_supply=self.config.initial_supply,
                initial_floor=self.config.initial_floor,
                buy_fee=self.config.buy_fee,
                sell_fee=self.config.sell_fee,
                origination_fee=self.config.origination_fee,
                elevation_threshold=self.config.elevation_threshold,
                debt_cap_bps=self.config.debt_cap_bps,
                min_coverage_buffer_bps=self.config.min_coverage_buffer_bps,
                lre_threshold=self.config.lre_threshold,
                lre_realloc_bps=self.config.lre_realloc_bps,
                fee_to_floor_ratio=self.config.fee_to_floor_ratio,
                tick_size=self.config.tick_size,
            )
        
        # Tracking
        history = self._init_history()
        steps = int(self.config.horizon_days / (self.config.dt * 365))
        
        prev_underlying = underlying.current_price()
        recent_high = underlying.current_price()
        
        # Record initial t=0 state BEFORE any trading
        self._record_step(
            history, -1, self.config.dt,  # step=-1 means t=0
            underlying, lst, ftoken,
            0.0, 0.0, 0.0  # No volume yet
        )
        
        for step in range(steps):
            # 1. Update market
            u_price = underlying.simulate_step(self.config.dt)
            u_return = (u_price - prev_underlying) / prev_underlying if prev_underlying > 0 else 0
            
            # Track drawdown
            recent_high = max(recent_high, u_price)
            drawdown = (recent_high - u_price) / recent_high if recent_high > 0 else 0
            
            prev_underlying = u_price
            lst_price = lst.simulate_step(self.config.dt)
            
            # 2. Build market state for agents
            market_state = MarketState(
                underlying_price=u_price,
                underlying_return=u_return,
                underlying_drawdown=drawdown,
                floor_price=ftoken.floor_price,
                market_price=ftoken.get_market_price(),
                premium=ftoken.get_premium_multiple() - 1,
                fpr=ftoken.calculate_fpr(),
                total_debt=ftoken.debt,
                total_locked=ftoken.locked_supply,
                debt_utilization=ftoken.debt / ftoken.get_debt_cap() if ftoken.get_debt_cap() > 0 else 0,
                recent_buy_volume=history['buy_volume'][-1] if history['buy_volume'] else 0,
                recent_sell_volume=history['sell_volume'][-1] if history['sell_volume'] else 0,
                step=step,
                days_elapsed=step * self.config.dt * 365
            )
            
            # 3. Agents decide and execute actions
            buy_volume = 0.0
            sell_volume = 0.0
            loan_originations = 0.0
            loan_repayments = 0.0
            
            # Shuffle agents for random execution order
            shuffled_agents = list(self.agents)
            np.random.shuffle(shuffled_agents)
            
            for agent in shuffled_agents:
                action = agent.decide_action(market_state)
                
                result = self._execute_action(agent, action, ftoken, market_state)
                
                if result:
                    agent.record_action(step, action)
                    
                    if action.action_type == ActionType.BUY:
                        buy_volume += action.amount
                    elif action.action_type == ActionType.SELL:
                        sell_volume += result.get('eth_received', 0)
                    elif action.action_type in (ActionType.BORROW, ActionType.TOPUP, ActionType.LEVERAGE_LOOP):
                        loan_originations += result.get('debt_created', 0)
                    elif action.action_type == ActionType.REPAY:
                        loan_repayments += result.get('debt_repaid', 0)
            
            # 4. Process agent churn (exits and new entries)
            churn_config = self.config.churn_config
            if churn_config and churn_config.enabled:
                exit_sell_vol, entry_buy_vol = self._process_churn(ftoken, market_state, churn_config)
                sell_volume += exit_sell_vol
                buy_volume += entry_buy_vol
            
            # 5. Process elevation
            ftoken.process_elevation()
            
            # 6. Record history
            self._record_step(
                history, step, self.config.dt,
                underlying, lst, ftoken,
                buy_volume, sell_volume, loan_originations
            )
        
        return pd.DataFrame(history)
    
    def _process_churn(
        self, 
        ftoken: fToken, 
        state: MarketState,
        config: ChurnConfig
    ) -> Tuple[float, float]:
        """
        Process agent churn: exits and new entries.
        
        Returns (sell_volume from exits, buy_volume from entries).
        """
        exit_volume = 0.0
        entry_buy_volume = 0.0
        agents_to_remove = []
        
        # Check each agent for exit
        for agent in self.agents:
            if should_agent_exit(agent, state, config):
                # Process exit (sell all tokens)
                eth_received = process_agent_exit(agent, ftoken, state)
                exit_volume += eth_received
                agents_to_remove.append(agent)
                self._churn_stats['exits'] += 1
                self._churn_stats['exit_volume'] += eth_received
        
        # Remove exiting agents
        for agent in agents_to_remove:
            self.agents.remove(agent)
        
        # Add new entrants to maintain population
        if config.maintain_population and agents_to_remove:
            for exiting_agent in agents_to_remove:
                # New entrant of same type
                new_agent = create_new_entrant(
                    self._next_agent_id,
                    exiting_agent.agent_type,
                    config,
                    state
                )
                
                # Execute new entrant's entry buy on the fToken
                if state.premium < 0.20 and new_agent.position.tokens_held > 0:
                    # The tokens were pre-calculated, now actually execute the buy
                    buy_amount = new_agent.position.total_invested
                    if buy_amount > 0:
                        tokens, fee_f, fee_g, actual_spent = ftoken.buy(buy_amount)
                        new_agent.position.tokens_held = tokens  # Use actual minted amount
                        # Refund unspent ETH if cap hit
                        if actual_spent < buy_amount:
                             refund = buy_amount - actual_spent
                             new_agent.position.eth_balance += refund
                             new_agent.position.total_invested -= refund
                        entry_buy_volume += actual_spent
                
                self.agents.append(new_agent)
                self._next_agent_id += 1
                self._churn_stats['entries'] += 1
        
        return exit_volume, entry_buy_volume
    
    def _execute_action(
        self,
        agent: Agent,
        action: Action,
        ftoken: fToken,
        state: MarketState
    ) -> Optional[Dict[str, float]]:
        """Execute an agent's action on the fToken."""
        
        if action.action_type == ActionType.HOLD:
            return None
        
        if action.action_type == ActionType.BUY:
            if action.amount <= 0 or agent.position.eth_balance < action.amount:
                return None
            
            tokens, fee_f, fee_g, actual_spent = ftoken.buy(action.amount)
            
            agent.update_position(
                tokens_delta=tokens,
                eth_delta=-actual_spent,
                fees_paid=fee_f + fee_g,
                floor_price=state.floor_price
            )
            
            return {'tokens_bought': tokens, 'fees': fee_f + fee_g}
        
        if action.action_type == ActionType.SELL:
            tokens_to_sell = min(action.amount, agent.position.tokens_held)
            if tokens_to_sell <= 0:
                return None
            
            eth_received, fee, success = ftoken.sell(tokens_to_sell)
            
            if success:
                agent.update_position(
                    tokens_delta=-tokens_to_sell,
                    eth_delta=eth_received,
                    fees_paid=fee
                )
                return {'eth_received': eth_received, 'fees': fee}
            
            return None
        
        if action.action_type == ActionType.BORROW:
            if agent.position.tokens_held <= 0:
                return None
            
            # Lock all held tokens as collateral
            collateral = agent.position.tokens_held
            
            success, fee_f, fee_g, loan_id = ftoken.originate_loan(
                action.amount, collateral
            )
            
            if success:
                agent.update_position(
                    tokens_delta=-collateral,  # Move from held to locked
                    locked_delta=collateral,
                    debt_delta=action.amount,
                    fees_paid=fee_f + fee_g
                )
                agent.position.tokens_locked = collateral
                
                return {'debt_created': action.amount, 'collateral_locked': collateral}
            
            return None
        
        if action.action_type == ActionType.TOPUP:
            if agent.position.tokens_locked <= 0:
                return None
            
            # Top-up: borrow more against existing collateral
            success, fee_f, fee_g, _ = ftoken.originate_loan(
                action.amount, 0  # No new collateral
            )
            
            if success:
                agent.update_position(
                    debt_delta=action.amount,
                    fees_paid=fee_f + fee_g
                )
                return {'debt_created': action.amount}
            
            return None
        
        if action.action_type == ActionType.REPAY:
            if agent.position.debt <= 0:
                return None
            
            repay_amount = min(action.amount, agent.position.debt)
            
            # Find agent's loan (simplified: assume single loan)
            agent_loans = [l for l in ftoken.loans if l.is_active]
            if not agent_loans:
                return None
            
            loan = agent_loans[0]
            success, flash_fee = ftoken.repay_loan(loan.loan_id, repay_amount)
            
            if success:
                agent.update_position(
                    debt_delta=-repay_amount,
                    fees_paid=flash_fee
                )
                
                # If fully repaid, unlock collateral
                if agent.position.debt <= 0:
                    unlocked = agent.position.tokens_locked
                    agent.position.tokens_held += unlocked
                    agent.position.tokens_locked = 0
                
                return {'debt_repaid': repay_amount}
            
            return None
        
        if action.action_type == ActionType.LEVERAGE_LOOP:
            if agent.position.tokens_held <= 0:
                return None
            
            total_debt = 0.0
            total_tokens = 0.0
            total_fees = 0.0
            
            current_tokens = agent.position.tokens_held
            ltv = agent.params.get('target_ltv', 0.70)
            
            for loop in range(action.loops):
                if current_tokens <= 0:
                    break
                
                # Lock and borrow
                collateral_value = current_tokens * state.floor_price
                borrow = collateral_value * ltv
                
                success, fee_f, fee_g, _ = ftoken.originate_loan(
                    borrow, current_tokens
                )
                
                if not success:
                    break
                
                total_debt += borrow
                total_fees += fee_f + fee_g
                
                agent.update_position(
                    tokens_delta=-current_tokens,
                    locked_delta=current_tokens,
                    debt_delta=borrow,
                    fees_paid=fee_f + fee_g
                )
                
                # Buy more tokens
                net_eth = borrow * (1 - ftoken.buy_fee)
                tokens_bought, buy_fee_f, buy_fee_g, actual_spent = ftoken.buy(borrow)
                
                total_tokens += tokens_bought
                total_fees += buy_fee_f + buy_fee_g
                
                # If we spent less than borrowed, we keep the difference as ETH
                unused_borrow = borrow - actual_spent
                
                agent.update_position(
                    tokens_delta=tokens_bought,
                    eth_delta=unused_borrow,  # Add unused borrowed ETH to balance
                    fees_paid=buy_fee_f + buy_fee_g
                )
                
                current_tokens = tokens_bought
            
            agent.position.leverage_loops += action.loops
            
            return {
                'debt_created': total_debt,
                'tokens_acquired': total_tokens,
                'fees': total_fees
            }
        
        return None
    
    def _init_history(self) -> Dict[str, List]:
        """Initialize history tracking dict."""
        return {
            'time': [],
            'step': [],
            'underlying_price': [],
            'underlying_return': [],
            'lst_price': [],
            'ftoken_floor': [],
            'ftoken_market_price': [],
            'ftoken_reserves': [],
            'ftoken_supply': [],
            'ftoken_fpr': [],
            'ftoken_debt': [],
            'ftoken_locked_supply': [],
            'ftoken_lre_triggered': [],
            'ftoken_bad_debt_cumulative': [],
            'ftoken_is_solvent': [],
            'buy_volume': [],
            'sell_volume': [],
            'loan_volume': [],
            'lst_depeg_event': [],
            'stakers_fees': [],
            'team_fees': [],
        }
    
    def _record_step(
        self,
        history: Dict[str, List],
        step: int,
        dt: float,
        underlying, lst, ftoken,
        buy_volume: float,
        sell_volume: float,
        loan_volume: float
    ):
        """Record a step's data in history."""
        history['time'].append(step * dt)
        history['step'].append(step)
        history['underlying_price'].append(underlying.current_price())
        
        if len(underlying.price_history) >= 2:
            prev = underlying.price_history[-2]
            curr = underlying.price_history[-1]
            history['underlying_return'].append((curr - prev) / prev if prev > 0 else 0)
        else:
            history['underlying_return'].append(0)
        
        history['lst_price'].append(lst.current_price())
        history['ftoken_floor'].append(ftoken.floor_price)
        history['ftoken_market_price'].append(ftoken.get_market_price())
        history['ftoken_reserves'].append(ftoken.reserves)
        history['ftoken_supply'].append(ftoken.total_supply)
        history['ftoken_fpr'].append(ftoken.calculate_fpr())
        history['ftoken_debt'].append(ftoken.debt)
        history['ftoken_locked_supply'].append(ftoken.locked_supply)
        
        lre_triggered = len(ftoken.lre_events) > 0 and ftoken.lre_events[-1][0] == ftoken._step_count
        history['ftoken_lre_triggered'].append(lre_triggered)
        history['ftoken_bad_debt_cumulative'].append(ftoken.get_total_bad_debt())
        history['ftoken_is_solvent'].append(ftoken.is_solvent())
        
        history['buy_volume'].append(buy_volume)
        history['sell_volume'].append(sell_volume)
        history['loan_volume'].append(loan_volume)
        
        depeg_event = len(lst.depeg_events) > 0 and lst.depeg_events[-1][0] == lst._step_count
        history['lst_depeg_event'].append(depeg_event)
        
        # Fee tracking
        history['stakers_fees'].append(ftoken.stakers_fees_accumulated)
        history['team_fees'].append(ftoken.team_fees_accumulated)
