"""
Presale Phase Simulation

Models the presale mechanics where:
1. Fixed price - all buys occur at a predetermined price
2. Fees accumulate but don't elevate floor until presale closes
3. At close: inject accumulated fees → floor goes "live"

This module handles the presale phase separately from the main simulation.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any, Optional


@dataclass
class PresaleConfig:
    """Configuration for presale phase."""
    duration_days: int = 7
    fixed_price: float = 1.0       # All buys/sells at this price
    base_fee: float = 0.02         # 2% fee on all mints
    loop_fee: float = 0.025        # 2.5% per leverage loop
    max_leverage: float = 10.0     # Max 10x leverage (90% LTV)
    max_ltv: float = 0.90          # 90% LTV for max leverage


@dataclass
class PresaleParticipant:
    """Tracks a presale participant's position."""
    participant_id: int
    agent_type: str
    tokens_bought: float = 0.0
    tokens_locked: float = 0.0
    debt: float = 0.0
    fees_paid: float = 0.0
    leverage_loops: int = 0
    entry_step: int = 0


@dataclass 
class PresaleState:
    """State of the presale phase."""
    # Supply tracking
    total_supply: float = 0.0
    locked_supply: float = 0.0
    
    # Reserves and fees
    total_reserves: float = 0.0      # ETH collected from mints
    accumulated_fees: float = 0.0     # Fees waiting to elevate floor
    total_debt: float = 0.0           # Outstanding loans
    
    # The fixed price (no curve during presale)
    fixed_price: float = 1.0
    
    # Participants
    participants: List[PresaleParticipant] = field(default_factory=list)
    _next_participant_id: int = 1
    
    # History
    daily_mint_volume: List[float] = field(default_factory=list)
    daily_leverage_volume: List[float] = field(default_factory=list)


class PresalePhase:
    """
    Simulates the presale phase with fixed pricing.
    
    Key differences from live market:
    - Price is FIXED (no curve movement)
    - Fees ACCUMULATE (don't elevate floor)
    - At close: fees injected → curve goes live
    
    Leverage during presale:
    - 2% base fee on all mints
    - 2.5% per leverage loop
    - Max 10x leverage (90% LTV, 10 loops)
    """
    
    def __init__(self, config: PresaleConfig):
        self.config = config
        self.state = PresaleState(fixed_price=config.fixed_price)
        self._step_count = 0
        
    def mint(
        self, 
        eth_amount: float, 
        agent_type: str = "unknown",
        participant: Optional[PresaleParticipant] = None
    ) -> Tuple[float, float, PresaleParticipant]:
        """
        Mint fTokens during presale at fixed price.
        
        Args:
            eth_amount: ETH to spend on minting
            agent_type: Type of agent minting
            participant: Existing participant or None to create new
            
        Returns:
            (tokens_minted, fee_paid, participant)
        """
        if eth_amount <= 0:
            if participant is None:
                participant = self._create_participant(agent_type)
            return 0.0, 0.0, participant
        
        # Calculate fee (2% base fee during presale)
        fee = eth_amount * self.config.base_fee
        net_eth = eth_amount - fee
        
        # Mint at fixed price
        tokens_minted = net_eth / self.config.fixed_price
        
        # Update state
        self.state.total_supply += tokens_minted
        self.state.total_reserves += net_eth
        self.state.accumulated_fees += fee
        
        # Track participant
        if participant is None:
            participant = self._create_participant(agent_type)
        
        participant.tokens_bought += tokens_minted
        participant.fees_paid += fee
        
        return tokens_minted, fee, participant
    
    def leverage_loop(
        self, 
        participant: PresaleParticipant,
        num_loops: int = 1
    ) -> Tuple[float, float, float]:
        """
        Execute leverage loop(s) for a participant.
        
        Each loop:
        1. Lock tokens as collateral
        2. Borrow ETH at LTV
        3. Pay 2.5% loop fee
        4. Mint more tokens with borrowed ETH
        
        Args:
            participant: The participant executing the loop
            num_loops: Number of loops to execute
            
        Returns:
            (total_tokens_acquired, total_debt_created, total_fees_paid)
        """
        total_tokens = 0.0
        total_debt = 0.0
        total_fees = 0.0
        
        # Calculate effective loops (max 10 for 10x leverage)
        max_loops = int(np.log(self.config.max_leverage) / np.log(1 / (1 - self.config.max_ltv)))
        loops_to_execute = min(num_loops, max_loops - participant.leverage_loops)
        
        if loops_to_execute <= 0:
            return 0.0, 0.0, 0.0
        
        # Start with unlocked tokens
        tokens_available = participant.tokens_bought - participant.tokens_locked
        
        for loop in range(loops_to_execute):
            if tokens_available <= 0:
                break
            
            # Lock tokens as collateral
            tokens_to_lock = tokens_available
            collateral_value = tokens_to_lock * self.config.fixed_price
            
            # Borrow at max LTV
            borrow_amount = collateral_value * self.config.max_ltv
            
            # Pay loop fee (2.5%)
            loop_fee = borrow_amount * self.config.loop_fee
            net_borrow = borrow_amount - loop_fee
            
            # Update participant state
            participant.tokens_locked += tokens_to_lock
            participant.debt += borrow_amount
            participant.fees_paid += loop_fee
            participant.leverage_loops += 1
            
            # Update global state
            self.state.locked_supply += tokens_to_lock
            self.state.total_debt += borrow_amount
            self.state.accumulated_fees += loop_fee
            
            total_debt += borrow_amount
            total_fees += loop_fee
            
            # Mint more tokens with borrowed ETH (recursive mint)
            # Need to pay base fee on this mint too
            mint_fee = net_borrow * self.config.base_fee
            mint_net = net_borrow - mint_fee
            tokens_minted = mint_net / self.config.fixed_price
            
            # Update state
            self.state.total_supply += tokens_minted
            self.state.total_reserves += mint_net
            self.state.accumulated_fees += mint_fee
            
            participant.tokens_bought += tokens_minted
            participant.fees_paid += mint_fee
            
            total_tokens += tokens_minted
            total_fees += mint_fee
            
            # These new tokens become available for next loop
            tokens_available = tokens_minted
        
        return total_tokens, total_debt, total_fees
    
    def simulate_step(self, dt: float = 1/365) -> Dict[str, float]:
        """
        Simulate one time step of presale activity.
        
        This gets called by the engine with pre-computed volumes
        or agent-generated activity.
        
        Args:
            dt: Time step (unused, presale doesn't have time-varying prices)
            
        Returns:
            Dict with step metrics
        """
        self._step_count += 1
        
        return {
            'step': self._step_count,
            'total_supply': self.state.total_supply,
            'locked_supply': self.state.locked_supply,
            'total_reserves': self.state.total_reserves,
            'accumulated_fees': self.state.accumulated_fees,
            'total_debt': self.state.total_debt,
            'n_participants': len(self.state.participants),
            'fixed_price': self.state.fixed_price,
        }
    
    def close(self) -> Dict[str, Any]:
        """
        Close the presale and return final state for live market initialization.
        
        At presale close:
        1. All accumulated fees become available for floor elevation
        2. The curve "goes live" with the presale participants' positions
        
        Returns:
            Dict with data to initialize the live fToken
        """
        # Calculate effective initial floor
        # Fees will be injected into reserves and elevate floor
        total_supply = self.state.total_supply
        total_reserves = self.state.total_reserves
        tradeable_supply = total_supply - self.state.locked_supply
        
        # Initial floor is the fixed price
        initial_floor = self.config.fixed_price
        
        # After fee injection, floor can potentially rise
        # But this will be handled by the fToken's process_elevation()
        # We just need to set up the initial state correctly
        
        return {
            'initial_reserves': total_reserves,
            'initial_supply': total_supply,
            'initial_floor': initial_floor,
            'locked_supply': self.state.locked_supply,
            'total_debt': self.state.total_debt,
            'pending_fees': self.state.accumulated_fees,
            'participants': self.state.participants,
            'presale_duration_days': self.config.duration_days,
            'presale_stats': {
                'total_minted_eth': total_reserves + self.state.accumulated_fees,
                'total_fees': self.state.accumulated_fees,
                'avg_leverage': self._calculate_avg_leverage(),
                'n_participants': len(self.state.participants),
            }
        }
    
    def _create_participant(self, agent_type: str) -> PresaleParticipant:
        """Create a new presale participant."""
        participant = PresaleParticipant(
            participant_id=self.state._next_participant_id,
            agent_type=agent_type,
            entry_step=self._step_count
        )
        self.state.participants.append(participant)
        self.state._next_participant_id += 1
        return participant
    
    def _calculate_avg_leverage(self) -> float:
        """Calculate average leverage across participants."""
        if self.state.total_supply == 0:
            return 1.0
        
        # Leverage = total_supply / (total_supply - supply_from_leverage)
        # supply_from_leverage ≈ total_debt / fixed_price (approx)
        if self.state.total_reserves == 0:
            return 1.0
        
        # More accurate: total position value / initial capital
        initial_capital = self.state.total_reserves + self.state.accumulated_fees - self.state.total_debt
        if initial_capital <= 0:
            return self.config.max_leverage
        
        total_position_value = self.state.total_supply * self.config.fixed_price
        return total_position_value / initial_capital
    
    def get_participant_stats(self) -> Dict[str, Any]:
        """Get statistics about presale participants."""
        if not self.state.participants:
            return {}
        
        by_type = {}
        for p in self.state.participants:
            if p.agent_type not in by_type:
                by_type[p.agent_type] = {
                    'count': 0,
                    'tokens': 0.0,
                    'debt': 0.0,
                    'leverage_loops': 0,
                    'fees_paid': 0.0
                }
            stats = by_type[p.agent_type]
            stats['count'] += 1
            stats['tokens'] += p.tokens_bought
            stats['debt'] += p.debt
            stats['leverage_loops'] += p.leverage_loops
            stats['fees_paid'] += p.fees_paid
        
        return by_type


def run_presale_simulation(
    config: PresaleConfig,
    daily_mints: List[Tuple[float, str, int]],  # (eth_amount, agent_type, leverage_loops)
) -> Dict[str, Any]:
    """
    Run a complete presale simulation.
    
    Args:
        config: Presale configuration
        daily_mints: List of (eth_amount, agent_type, leverage_loops) for each participant
        
    Returns:
        Presale close data for initializing live market
    """
    presale = PresalePhase(config)
    
    # Process all participants
    for eth_amount, agent_type, leverage_loops in daily_mints:
        _, _, participant = presale.mint(eth_amount, agent_type)
        
        if leverage_loops > 0:
            presale.leverage_loop(participant, leverage_loops)
    
    # Simulate the duration (for history tracking)
    for day in range(config.duration_days):
        presale.simulate_step()
    
    # Close and return initialization data
    return presale.close()
