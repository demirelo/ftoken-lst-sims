"""
Simulation Engine for fToken/LST Monte Carlo Analysis

This engine runs Monte Carlo simulations comparing fToken floor-backed tokens
against LST (Liquid Staking Tokens) under various market conditions.

Reference: Structural_Solvency_and_Risk_Topology.md, Appendix A
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from .models import Underlying, LST, fToken


@dataclass
class SimulationConfig:
    """Configuration for a simulation run."""
    # Path parameters
    n_paths: int = 1000
    horizon_days: int = 90
    dt: float = 1/365  # Time step in years
    
    # Underlying asset
    initial_price: float = 100.0
    mu: float = 0.0
    sigma: float = 0.5
    
    # LST parameters
    staking_yield: float = 0.05
    p_depeg: float = 0.001
    depeg_mean: float = -0.05
    depeg_std: float = 0.02
    stress_depeg_multiplier: float = 3.0
    
    # fToken initial state
    initial_reserves: float = 1100000
    initial_supply: float = 1000000
    initial_floor: float = 1.0
    
    # fToken fees
    buy_fee: float = 0.003
    sell_fee: float = 0.005
    origination_fee: float = 0.02
    
    # fToken governance
    elevation_threshold: float = 2000
    tier_schedule: str = 'harmonic'
    tier_capacity: float = 100000
    debt_cap_bps: int = 5000
    min_coverage_buffer_bps: int = 500
    
    # LRE parameters
    lre_realloc_bps: int = 2000
    lre_max_mkt_impact_bps: int = 200
    lre_threshold: float = 2.0
    
    # Credit facility simulation
    daily_volume_mean: float = 50000
    daily_volume_std: float = 15000
    daily_loan_origination_mean: float = 1000
    daily_loan_origination_std: float = 500
    loan_ltv: float = 0.7  # 70% LTV for loans
    
    # Bad debt parameters
    bad_debt_lgd: float = 0.3
    loan_default_prob_base: float = 0.001
    
    # Volume correlation with market
    volume_stress_multiplier: float = 0.5  # Volume drops 50% in stress


class SimulationEngine:
    """
    Monte Carlo simulation engine for fToken vs LST comparison.
    
    Per spec Appendix A.2-A.9, this engine:
    1. Simulates underlying price paths (GBM)
    2. Tracks LST with stress-correlated depegs
    3. Tracks fToken with full floor mechanics
    4. Computes VaR and failure metrics
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize engine with configuration dict.
        
        Args:
            config: Dictionary of simulation parameters (can be from SCENARIOS)
        """
        self.config = config
        self.paths: List[pd.DataFrame] = []
        self.summary_stats: Dict[str, Any] = {}
    
    def run(self) -> List[pd.DataFrame]:
        """
        Run Monte Carlo simulation.
        
        Returns:
            List of DataFrames, one per path
        """
        n_paths = self.config['n_paths']
        horizon_days = self.config['horizon_days']
        dt = self.config['dt']
        steps = int(horizon_days / (dt * 365))
        
        print(f"Starting simulation: {n_paths} paths, {steps} steps...")
        
        self.paths = []
        
        for i in range(n_paths):
            path_data = self._run_single_path(steps, dt)
            self.paths.append(path_data)
            
            if (i + 1) % 100 == 0:
                print(f"Completed {i + 1}/{n_paths} paths")
        
        print("Simulation complete. Computing summary statistics...")
        self._compute_summary_stats()
        
        return self.paths
    
    def _run_single_path(self, steps: int, dt: float) -> pd.DataFrame:
        """
        Run a single simulation path.
        
        Args:
            steps: Number of time steps
            dt: Time step size in years
            
        Returns:
            DataFrame with path history
        """
        # Initialize assets
        underlying = Underlying(
            name="AVAX",
            initial_price=self.config['initial_price'],
            mu=self.config['mu'],
            sigma=self.config['sigma']
        )
        
        lst = LST(
            name="sAVAX",
            underlying=underlying,
            staking_yield=self.config['staking_yield'],
            p_depeg_base=self.config.get('p_depeg', 0),
            depeg_severity_mean=self.config.get('depeg_mean', -0.05),
            depeg_severity_std=self.config.get('depeg_std', 0.02),
            stress_depeg_multiplier=self.config.get('stress_depeg_multiplier', 3.0)
        )
        
        ftoken = fToken(
            name="fAVAX",
            underlying=underlying,
            initial_reserves=self.config['initial_reserves'],
            initial_supply=self.config['initial_supply'],
            initial_floor=self.config['initial_floor'],
            buy_fee=self.config['buy_fee'],
            sell_fee=self.config['sell_fee'],
            origination_fee=self.config['origination_fee'],
            elevation_threshold=self.config.get('elevation_threshold', 0),
            tier_schedule=self.config.get('tier_schedule', 'harmonic'),
            tier_capacity_base=self.config.get('tier_capacity', 100000),
            debt_cap_bps=self.config.get('debt_cap_bps', 5000),
            min_coverage_buffer_bps=self.config.get('min_coverage_buffer_bps', 500),
            lre_realloc_bps=self.config.get('lre_realloc_bps', 2000),
            lre_max_mkt_impact_bps=self.config.get('lre_max_mkt_impact_bps', 200),
            lre_threshold=self.config.get('lre_threshold', 2.0),
            bad_debt_lgd=self.config.get('bad_debt_lgd', 0.3),
            loan_default_prob_base=self.config.get('loan_default_prob_base', 0.001),
            fee_to_floor_ratio=self.config.get('fee_to_floor_ratio', 0.70)
        )
        
        # Initialize history storage
        history = {
            'time': [],
            'step': [],
            # Underlying
            'underlying_price': [],
            'underlying_return': [],
            # LST
            'lst_price': [],
            'lst_index': [],
            'lst_depeg_event': [],
            # fToken - core
            'ftoken_floor': [],
            'ftoken_market_price': [],
            'ftoken_reserves': [],
            'ftoken_supply': [],
            'ftoken_floor_supply': [],
            'ftoken_premium_supply': [],
            # fToken - solvency metrics
            'ftoken_fpr': [],
            'ftoken_coverage_bps': [],
            'ftoken_headroom': [],
            'ftoken_premium_multiple': [],
            'ftoken_fpr_zone': [],
            # fToken - credit facility
            'ftoken_debt': [],
            'ftoken_locked_supply': [],
            'ftoken_tradeable_supply': [],
            'ftoken_max_borrowable': [],
            'ftoken_active_loans': [],
            # fToken - LRE
            'ftoken_lre_triggered': [],
            'ftoken_premium_liquidity': [],
            # fToken - bad debt
            'ftoken_bad_debt_cumulative': [],
            'ftoken_is_solvent': [],
            # Volume
            'buy_volume': [],
            'sell_volume': [],
            'loan_volume': [],
        }
        
        prev_underlying_price = underlying.current_price()
        
        for step in range(steps):
            t = step * dt
            
            # 1. Update Underlying (GBM)
            u_price = underlying.simulate_step(dt)
            u_return = (u_price - prev_underlying_price) / prev_underlying_price if prev_underlying_price > 0 else 0
            prev_underlying_price = u_price
            
            # 2. Update LST (with stress-correlated depeg)
            lst_price = lst.simulate_step(dt, underlying_return=u_return)
            depeg_event = len(lst.depeg_events) > 0 and lst.depeg_events[-1][0] == lst._step_count
            
            # 3. Calculate volumes (stress-adjusted)
            vol_mean = self.config.get('daily_volume_mean', 10000) * dt * 365
            vol_std = self.config.get('daily_volume_std', 2000) * dt * 365
            
            # Volume drops during stress (negative returns)
            stress_mult = self.config.get('volume_stress_multiplier', 0.5)
            if u_return < -0.03:  # Significant stress
                vol_mean *= stress_mult
            
            total_volume = max(0, np.random.normal(vol_mean, vol_std))
            
            # Buy/sell split varies with market direction
            if u_return > 0.01:  # Bull - more buying
                buy_ratio = 0.6
            elif u_return < -0.01:  # Bear - more selling
                buy_ratio = 0.4
            else:  # Sideways
                buy_ratio = 0.5
            
            buy_volume = total_volume * buy_ratio
            sell_volume = total_volume * (1 - buy_ratio)
            
            # 4. Calculate loan demand (drops in crisis)
            loan_mean = self.config.get('daily_loan_origination_mean', 0) * dt * 365
            loan_std = self.config.get('daily_loan_origination_std', 0) * dt * 365
            
            # Loan demand drops during stress
            if u_return < -0.05:
                loan_mean *= 0.3  # 70% drop in crisis
            elif u_return < -0.02:
                loan_mean *= 0.6
            
            new_loan = max(0, np.random.normal(loan_mean, loan_std)) if loan_mean > 0 else 0
            
            # Calculate collateral for loan (based on LTV)
            loan_ltv = self.config.get('loan_ltv', 0.7)
            if new_loan > 0 and ftoken.floor_price > 0:
                loan_collateral = (new_loan / loan_ltv) / ftoken.floor_price
                # Cap at available tradeable supply
                loan_collateral = min(loan_collateral, ftoken.get_tradeable_supply() * 0.1)
            else:
                loan_collateral = 0
            
            # 5. Update fToken
            ft_price = ftoken.simulate_step(
                dt=dt,
                buy_volume=buy_volume,
                sell_volume=sell_volume,
                new_loan_amount=new_loan,
                new_loan_collateral=loan_collateral
            )
            
            # 6. Record history
            history['time'].append(t)
            history['step'].append(step)
            
            # Underlying
            history['underlying_price'].append(u_price)
            history['underlying_return'].append(u_return)
            
            # LST
            history['lst_price'].append(lst_price)
            history['lst_index'].append(lst.index)
            history['lst_depeg_event'].append(depeg_event)
            
            # fToken - core
            history['ftoken_floor'].append(ftoken.floor_price)
            history['ftoken_market_price'].append(ftoken.get_market_price())
            history['ftoken_reserves'].append(ftoken.reserves)
            history['ftoken_supply'].append(ftoken.total_supply)
            history['ftoken_floor_supply'].append(ftoken.floor_supply)
            history['ftoken_premium_supply'].append(ftoken.premium_supply)
            
            # fToken - solvency
            history['ftoken_fpr'].append(ftoken.calculate_fpr())
            history['ftoken_coverage_bps'].append(ftoken.get_coverage_ratio_bps())
            history['ftoken_headroom'].append(ftoken.calculate_headroom())
            history['ftoken_premium_multiple'].append(ftoken.get_premium_multiple())
            history['ftoken_fpr_zone'].append(ftoken.get_fpr_zone())
            
            # fToken - credit
            history['ftoken_debt'].append(ftoken.debt)
            history['ftoken_locked_supply'].append(ftoken.locked_supply)
            history['ftoken_tradeable_supply'].append(ftoken.get_tradeable_supply())
            history['ftoken_max_borrowable'].append(ftoken.get_max_borrowable())
            history['ftoken_active_loans'].append(ftoken.get_active_loan_count())
            
            # fToken - LRE
            lre_triggered = len(ftoken.lre_events) > 0 and ftoken.lre_events[-1][0] == ftoken._step_count
            history['ftoken_lre_triggered'].append(lre_triggered)
            history['ftoken_premium_liquidity'].append(ftoken.get_premium_liquidity())
            
            # fToken - bad debt
            history['ftoken_bad_debt_cumulative'].append(ftoken.get_total_bad_debt())
            history['ftoken_is_solvent'].append(ftoken.is_solvent())
            
            # Volume
            history['buy_volume'].append(buy_volume)
            history['sell_volume'].append(sell_volume)
            history['loan_volume'].append(new_loan)
        
        return pd.DataFrame(history)
    
    def _compute_summary_stats(self):
        """Compute summary statistics across all paths."""
        if len(self.paths) == 0:
            return
        
        # Extract terminal values
        lst_terminal = [df['lst_price'].iloc[-1] for df in self.paths]
        ftoken_floor_terminal = [df['ftoken_floor'].iloc[-1] for df in self.paths]
        underlying_terminal = [df['underlying_price'].iloc[-1] for df in self.paths]
        
        # Calculate USD values for fToken
        ftoken_usd_terminal = [
            df['ftoken_floor'].iloc[-1] * df['underlying_price'].iloc[-1] 
            for df in self.paths
        ]
        
        # FPR metrics
        min_fpr_per_path = [df['ftoken_fpr'].min() for df in self.paths]
        
        # Insolvency events
        insolvency_paths = sum(1 for df in self.paths if df['ftoken_fpr'].min() < 1.0)
        stress_paths = sum(1 for df in self.paths if df['ftoken_fpr'].min() < 1.05)
        
        # Bad debt
        total_bad_debt_per_path = [df['ftoken_bad_debt_cumulative'].iloc[-1] for df in self.paths]
        paths_with_bad_debt = sum(1 for bd in total_bad_debt_per_path if bd > 0)
        
        # LRE events
        lre_count_per_path = [df['ftoken_lre_triggered'].sum() for df in self.paths]
        
        # Depeg events
        depeg_count_per_path = [df['lst_depeg_event'].sum() for df in self.paths]
        
        self.summary_stats = {
            'n_paths': len(self.paths),
            'n_steps': len(self.paths[0]) if len(self.paths) > 0 else 0,
            
            # Terminal price stats
            'underlying_terminal_mean': np.mean(underlying_terminal),
            'underlying_terminal_std': np.std(underlying_terminal),
            'lst_terminal_mean': np.mean(lst_terminal),
            'lst_terminal_std': np.std(lst_terminal),
            'ftoken_floor_terminal_mean': np.mean(ftoken_floor_terminal),
            'ftoken_floor_terminal_std': np.std(ftoken_floor_terminal),
            'ftoken_usd_terminal_mean': np.mean(ftoken_usd_terminal),
            'ftoken_usd_terminal_std': np.std(ftoken_usd_terminal),
            
            # FPR stats
            'min_fpr_mean': np.mean(min_fpr_per_path),
            'min_fpr_5th_percentile': np.percentile(min_fpr_per_path, 5),
            'insolvency_probability': insolvency_paths / len(self.paths),
            'stress_probability': stress_paths / len(self.paths),
            
            # Bad debt
            'paths_with_bad_debt': paths_with_bad_debt,
            'bad_debt_probability': paths_with_bad_debt / len(self.paths),
            'total_bad_debt_mean': np.mean(total_bad_debt_per_path),
            'total_bad_debt_max': np.max(total_bad_debt_per_path),
            
            # LRE
            'lre_events_mean': np.mean(lre_count_per_path),
            'lre_events_max': np.max(lre_count_per_path),
            
            # Depeg
            'depeg_events_mean': np.mean(depeg_count_per_path),
            'depeg_events_max': np.max(depeg_count_per_path),
        }
    
    def get_terminal_returns(self, asset: str = 'lst') -> np.ndarray:
        """
        Get terminal returns for all paths.
        
        Args:
            asset: 'lst', 'ftoken_floor', 'ftoken_usd', 'underlying'
            
        Returns:
            Array of terminal returns
        """
        returns = []
        
        for df in self.paths:
            if asset == 'lst':
                start = df['lst_price'].iloc[0]
                end = df['lst_price'].iloc[-1]
            elif asset == 'ftoken_floor':
                start = df['ftoken_floor'].iloc[0]
                end = df['ftoken_floor'].iloc[-1]
            elif asset == 'ftoken_usd':
                start = df['ftoken_floor'].iloc[0] * df['underlying_price'].iloc[0]
                end = df['ftoken_floor'].iloc[-1] * df['underlying_price'].iloc[-1]
            elif asset == 'underlying':
                start = df['underlying_price'].iloc[0]
                end = df['underlying_price'].iloc[-1]
            else:
                raise ValueError(f"Unknown asset: {asset}")
            
            ret = (end / start) - 1 if start > 0 else 0
            returns.append(ret)
        
        return np.array(returns)
    
    def get_fpr_paths(self) -> List[np.ndarray]:
        """Get FPR time series for all paths."""
        return [df['ftoken_fpr'].values for df in self.paths]
    
    def get_min_fpr_distribution(self) -> np.ndarray:
        """Get distribution of minimum FPR across paths."""
        return np.array([df['ftoken_fpr'].min() for df in self.paths])
