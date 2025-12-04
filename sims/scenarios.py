"""
Simulation Scenarios for fToken/LST Monte Carlo Analysis

These scenarios are calibrated to test the fToken floor mechanics under
different market conditions, as described in the Structural Solvency report.

Key scenarios from spec Section 8:
- Crypto Winter: Severe drawdown (-75%), high volatility
- Crab Market: Sideways, low volatility, modest volume
- Super Cycle: Strong bull market, high volatility and volume

Parameters are aligned with:
- Appendix A.4: LST depeg model with stress correlation
- Section 9.3: FPR thresholds (green/yellow/red zones)
- Section 5.1: VaR framework assumptions
"""

# Base configuration shared across scenarios
BASE_CONFIG = {
    # Simulation structure
    'n_paths': 1000,
    'horizon_days': 90,
    'dt': 1/365,  # Daily steps
    
    # Initial fToken state - FPR = 1.10 (green zone per Section 9.3)
    'initial_price': 100.0,
    'initial_reserves': 1100000,
    'initial_supply': 1000000,
    'initial_floor': 1.0,
    
    # fToken fees (per spec) - 0.5% each direction
    'buy_fee': 0.005,        # 0.5%
    'sell_fee': 0.005,       # 0.5%
    'origination_fee': 0.02, # 2%
    'fee_to_floor_ratio': 0.70,  # 70% of fees to floor, 30% to governance

    
    # fToken governance (per Section 10)
    'debt_cap_bps': 5000,             # 50% max debt-to-liquidity
    'min_coverage_buffer_bps': 500,   # 5% extra coverage required
    'tier_schedule': 'harmonic',      # Per Appendix B
    'tier_capacity': 100000,          # Base tier capacity
    
    # LRE parameters (per Section 10.3)
    'lre_realloc_bps': 2000,          # 20% of excess per operation
    'lre_max_mkt_impact_bps': 200,    # 2% max price impact
    'lre_threshold': 2.0,             # Trigger when premium 2x floor
    
    # Credit facility - realistic loan activity
    'loan_ltv': 0.7,                  # 70% LTV
    'enable_loan_activity': True,     # Use realistic loan lifecycle model
    'target_lock_ratio': 0.50,        # Target 50% of floor supply locked
    'enable_topup': True,             # Allow top-ups when floor rises
    'repay_probability': 0.02,        # 2% chance per loan per step to repay (unloop)
    'partial_repay_ratio': 0.3,       # 30% partial repay when repaying
    
    # Leverage looping - people lever up when premium is low
    # This happens when market price is close to floor (low downside risk)
    'enable_leverage_looping': True,
    'is_presale': False,              # Post-presale: 2% origination fee per loop
    'leverage_probability_base': 0.025, # 2.5% base chance per step (~2x/month when premium low)
    'leverage_premium_threshold': 0.10, # Lever up when premium < 10%
    'average_leverage_loops': 1.5,    # Average 1.5 loops post-presale
    'leverage_ltv': 0.70,             # 70% LTV for leverage
    
    # Bad debt (per Section 9.2) - note: bad debt is structurally impossible
    'bad_debt_lgd': 0.3,              # 30% loss-given-default (unused)
    'loan_default_prob_base': 0.001,  # 0.1% base default rate per step (unused)
    
    # LST yield
    'staking_yield': 0.026,           # 2.6% APY (updated per user)
    
    # Stress correlation (per Section 5.1)
    'stress_depeg_multiplier': 3.0,   # 3x depeg probability in stress
    'volume_stress_multiplier': 0.5,  # Volume drops 50% in stress
}


SCENARIOS = {
    # =========================================================================
    # CRYPTO WINTER (Section 8.1)
    # =========================================================================
    # Severe drawdown scenario: AVAX drops 75% over 90 days
    # Tests floor protection under maximum stress
    # Expected: fToken preserves AVAX-denominated value at floor
    #           LST suffers full drawdown + potential depegs
    'crypto_winter': {
        **BASE_CONFIG,
        
        # Market dynamics
        'mu': -0.8,           # ~55% annualized decline (gives ~75% over 90d with vol)
        'sigma': 0.8,         # High volatility (80% annualized)
        
        # LST depeg risk elevated (per Section 5.1)
        # "Much larger dislocations (20%+) in distressed tokens"
        'p_depeg': 0.01,      # 1% daily depeg probability in stress
        'depeg_mean': -0.05,  # 5% average discount
        'depeg_std': 0.03,    # Tail extends to -15%+
        
        # Trading activity drops in crisis
        'daily_volume_mean': 30000,   # Reduced volume
        'daily_volume_std': 15000,
        
        # Loan activity in crisis - deleveraging mode
        'target_lock_ratio': 0.30,    # Lower target - borrowers cautious
        'repay_probability': 0.05,    # Higher repays - deleveraging
        'enable_topup': False,        # No one wants more leverage in crash
        
        # Leverage looping - almost none in crash
        'enable_leverage_looping': True,
        'leverage_probability_base': 0.005,  # Very low - no one wants leverage in crash
        'leverage_premium_threshold': 0.05,  # Only at very low premium
        'average_leverage_loops': 1.0,       # Minimal loops
        
        # Elevation params
        'elevation_threshold': 2000,
    },
    
    # =========================================================================
    # CRAB MARKET (Section 8.2)
    # =========================================================================
    # Sideways market: Low volatility, modest activity
    # Tests floor elevation from fees vs LST yield accumulation
    # Expected: LST likely outperforms on raw return
    #           fToken provides strong collateral with modest floor growth
    'crab_market': {
        **BASE_CONFIG,
        
        # Market dynamics - slight upward drift
        'mu': 0.05,           # 5% annualized drift
        'sigma': 0.4,         # Moderate volatility (40% annualized)
        
        # LST depeg rare in calm markets
        'p_depeg': 0.001,     # 0.1% daily depeg probability
        'depeg_mean': -0.03,  # Smaller depegs when they occur
        'depeg_std': 0.02,
        
        # Steady but modest trading
        'daily_volume_mean': 20000,
        'daily_volume_std': 5000,
        
        # Loan activity in sideways market - steady state
        # Floor doesn't move much → limited new headroom for top-ups
        # But steady origination/repayment cycle continues
        'target_lock_ratio': 0.45,    # Moderate target
        'repay_probability': 0.025,   # Normal repayment rate (~40 day avg loan duration)
        'enable_topup': True,         # Top-ups when floor rises (slowly)
        
        # Leverage looping - moderate when premium is low
        'enable_leverage_looping': True,
        'leverage_probability_base': 0.02,  # 2% base - moderate activity
        'leverage_premium_threshold': 0.08, # Lever up when premium < 8%
        'average_leverage_loops': 1.5,      # 1-2 loops typical
        
        # Lower elevation threshold (fees accumulate slowly)
        'elevation_threshold': 1000,
    },
    
    # =========================================================================
    # SUPER CYCLE (Section 8.3)
    # =========================================================================
    # Strong bull market: High returns, high volatility, high volume
    # Tests floor elevation and LRE in uptrend
    # Expected: LST captures full upside
    #           fToken captures upside while building floor protection
    'super_cycle': {
        **BASE_CONFIG,
        
        # Market dynamics - strong bull
        'mu': 0.7,            # 70% annualized growth (realistic bull market)
        'sigma': 0.7,         # High volatility (70% annualized)
        
        # LST depeg still possible but less likely
        'p_depeg': 0.002,     # 0.2% daily depeg probability
        'depeg_mean': -0.02,  # Smaller depegs in bull
        'depeg_std': 0.01,
        
        # High trading activity
        'daily_volume_mean': 150000,
        'daily_volume_std': 50000,
        
        # Loan activity in bull market - high demand
        # Floor rises fast → lots of headroom for top-ups
        # Borrowers want leverage to participate in upside
        'target_lock_ratio': 0.55,    # Moderate base lock ratio
        'repay_probability': 0.02,    # Normal repays
        'enable_topup': True,         # Active top-ups as floor rises
        'loan_ltv': 0.70,             # Standard LTV
        
        # Leverage looping - active in bull market when premium is low
        'enable_leverage_looping': True,
        'leverage_probability_base': 0.04,  # 4% base - active but not extreme
        'leverage_premium_threshold': 0.12, # Willing to lever at 12% premium in bull
        'average_leverage_loops': 2.0,      # 2 loops average
        
        # Higher elevation threshold for batching
        'elevation_threshold': 5000,
    },
    
    # =========================================================================
    # PRESALE SCENARIOS (7-day precursor to market scenarios)
    # =========================================================================
    # Presale is a 7-day period where:
    # - 2% base fee on all mints
    # - 2.5% per-loop fee for leveraged positions
    # - Max 10x leverage (90% LTV)
    # - Predetermined supply minted (varies by following scenario)
    # 
    # After presale, the market scenario plays out
    
    # Presale → Super Cycle (high participation, bullish sentiment)
    'presale_bull': {
        **BASE_CONFIG,
        'n_paths': 500,
        'horizon_days': 7,    # 7-day presale
        
        # Bullish sentiment during presale
        'mu': 0.5,            # 50% annualized growth expectation
        'sigma': 0.3,         # Lower vol in controlled presale
        
        # No depeg risk during presale
        'p_depeg': 0.0,
        'depeg_mean': 0,
        'depeg_std': 0,
        
        # High volume during bullish presale
        'daily_volume_mean': 120000,  # ~12% of supply daily
        'daily_volume_std': 30000,
        
        # Loan activity - aggressive in bull presale
        'target_lock_ratio': 0.50,    # High lock ratio - people want leverage
        'repay_probability': 0.005,   # Very low repays - building positions
        'enable_topup': True,
        'loan_ltv': 0.90,             # 90% LTV for max 10x leverage
        
        # PRESALE leverage looping
        # 2% base fee on mint (handled by buy_fee)
        # 2.5% per-loop fee
        'buy_fee': 0.02,              # 2% base fee during presale
        'enable_leverage_looping': True,
        'is_presale': True,           # 2.5% per-loop fee
        'leverage_probability_base': 0.15,  # High - many want to lever up
        'leverage_premium_threshold': 0.05, # Lever up even at 5% premium
        'average_leverage_loops': 2.0,      # Avg ~2.5x leverage (2 loops at 90% LTV)
        'leverage_ltv': 0.90,               # 90% LTV for looping
        
        'elevation_threshold': 1500,
    },
    
    # Presale → Crab Market (moderate participation)
    'presale_neutral': {
        **BASE_CONFIG,
        'n_paths': 500,
        'horizon_days': 7,    # 7-day presale
        
        # Neutral sentiment
        'mu': 0.1,            # Slight positive drift
        'sigma': 0.3,         # Low vol in controlled presale
        
        'p_depeg': 0.0,
        'depeg_mean': 0,
        'depeg_std': 0,
        
        # Moderate volume
        'daily_volume_mean': 80000,   # ~8% of supply daily
        'daily_volume_std': 20000,
        
        # Moderate loan activity
        'target_lock_ratio': 0.40,
        'repay_probability': 0.01,
        'enable_topup': True,
        'loan_ltv': 0.90,
        
        # Moderate leverage looping
        'buy_fee': 0.02,              # 2% base fee
        'enable_leverage_looping': True,
        'is_presale': True,
        'leverage_probability_base': 0.10,
        'leverage_premium_threshold': 0.05,
        'average_leverage_loops': 1.5,      # Avg ~2x leverage
        'leverage_ltv': 0.90,
        
        'elevation_threshold': 1000,
    },
    
    # Presale → Crypto Winter (low participation, cautious)
    'presale_bear': {
        **BASE_CONFIG,
        'n_paths': 500,
        'horizon_days': 7,    # 7-day presale
        
        # Bearish sentiment - people are cautious
        'mu': -0.2,           # Slight negative drift
        'sigma': 0.4,         # Higher uncertainty
        
        'p_depeg': 0.0,
        'depeg_mean': 0,
        'depeg_std': 0,
        
        # Lower volume - less participation
        'daily_volume_mean': 40000,   # ~4% of supply daily (lower participation)
        'daily_volume_std': 15000,
        
        # Conservative loan activity
        'target_lock_ratio': 0.25,    # Lower lock - people cautious
        'repay_probability': 0.02,    # Some early exits
        'enable_topup': False,        # No top-ups in bearish presale
        'loan_ltv': 0.90,
        
        # Limited leverage looping - people cautious
        'buy_fee': 0.02,              # 2% base fee
        'enable_leverage_looping': True,
        'is_presale': True,
        'leverage_probability_base': 0.05,  # Low - cautious participants
        'leverage_premium_threshold': 0.03, # Only lever at very low premium
        'average_leverage_loops': 1.0,      # Avg ~1.9x leverage (1 loop)
        'leverage_ltv': 0.90,
        
        'elevation_threshold': 800,
    },
    
    # =========================================================================
    # ADDITIONAL STRESS SCENARIOS
    # =========================================================================
    
    # =========================================================================
    # HIGH LEVERAGE SCENARIOS - LTV STRESS TESTS
    # =========================================================================
    
    # LTV 80% - Aggressive but common
    'leverage_ltv80': {
        **BASE_CONFIG,
        'n_paths': 500,
        'horizon_days': 90,
        
        # Moderate bull to generate credit demand
        'mu': 0.3,            # 30% annualized growth
        'sigma': 0.6,         # Moderate-high volatility
        
        # Depeg risk present
        'p_depeg': 0.003,
        'depeg_mean': -0.03,
        'depeg_std': 0.02,
        
        # HIGH VOLUME to activate LRE
        'daily_volume_mean': 150000,   # 15% of supply daily
        'daily_volume_std': 50000,
        
        # AGGRESSIVE LENDING at 80% LTV
        'loan_ltv': 0.80,              # 80% LTV
        'target_lock_ratio': 0.60,     # High lock ratio - aggressive borrowers
        'repay_probability': 0.02,     # Normal repayment cycle
        'enable_topup': True,
        
        # Leverage looping - active with 80% LTV
        'enable_leverage_looping': True,
        'leverage_probability_base': 0.04,
        'leverage_premium_threshold': 0.12,
        'average_leverage_loops': 2.0,
        'leverage_ltv': 0.80,          # Match LTV
        
        # Higher debt cap to allow aggressive lending
        'debt_cap_bps': 6000,          # 60% max debt
        
        # Lower LRE threshold for activation
        'lre_threshold': 1.5,          # Trigger when premium 1.5x floor
        'lre_realloc_bps': 2500,       # 25% reallocation
        
        'elevation_threshold': 6000,
    },
    
    # LTV 90% - Very aggressive
    'leverage_ltv90': {
        **BASE_CONFIG,
        'n_paths': 500,
        'horizon_days': 90,
        
        # Strong bull market for stress testing
        'mu': 0.4,            # 40% annualized growth
        'sigma': 0.7,         # High volatility
        
        # Depeg risk elevated
        'p_depeg': 0.004,
        'depeg_mean': -0.04,
        'depeg_std': 0.025,
        
        # HIGH VOLUME
        'daily_volume_mean': 180000,   # 18% of supply daily
        'daily_volume_std': 60000,
        
        # VERY AGGRESSIVE LENDING at 90% LTV
        'loan_ltv': 0.90,              # 90% LTV - DANGER ZONE
        'target_lock_ratio': 0.65,     # High lock ratio
        'repay_probability': 0.02,     # Normal repays
        'enable_topup': True,
        
        # Leverage looping - aggressive with 90% LTV
        'enable_leverage_looping': True,
        'leverage_probability_base': 0.05,
        'leverage_premium_threshold': 0.15,
        'average_leverage_loops': 2.5,
        'leverage_ltv': 0.90,          # Match LTV
        
        # Maximum debt cap
        'debt_cap_bps': 7000,          # 70% max debt
        
        # Lower LRE threshold + aggressive reallocation
        'lre_threshold': 1.3,          # Very sensitive LRE
        'lre_realloc_bps': 3000,       # 30% reallocation
        
        'elevation_threshold': 8000,
    },
    
    # LTV 99% - Extreme stress test
    'leverage_ltv99': {
        **BASE_CONFIG,
        'n_paths': 500,
        'horizon_days': 60,    # Shorter horizon for extreme stress
        
        # Volatile bull market
        'mu': 0.5,            # 50% annualized growth
        'sigma': 0.8,         # Very high volatility
        
        # Maximum depeg risk
        'p_depeg': 0.005,
        'depeg_mean': -0.05,
        'depeg_std': 0.03,
        
        # HIGH VOLUME
        'daily_volume_mean': 200000,   # 20% of supply daily
        'daily_volume_std': 80000,
        
        # EXTREME LENDING at 99% LTV
        'loan_ltv': 0.99,              # 99% LTV - MAXIMUM RISK
        'target_lock_ratio': 0.70,     # High lock ratio
        'repay_probability': 0.015,    # Low repays - max leverage
        'enable_topup': True,
        
        # Leverage looping - extreme with 99% LTV
        'enable_leverage_looping': True,
        'leverage_probability_base': 0.06,
        'leverage_premium_threshold': 0.20,  # Even at higher premium
        'average_leverage_loops': 3.0,
        'leverage_ltv': 0.99,          # Match LTV
        
        # Maximum debt cap
        'debt_cap_bps': 8000,          # 80% max debt (extreme)
        
        # Minimum coverage buffer reduced for extreme test
        'min_coverage_buffer_bps': 300,  # 3% buffer (reduced)
        
        # Aggressive LRE
        'lre_threshold': 1.2,          # Hair-trigger LRE
        'lre_realloc_bps': 3500,       # 35% reallocation
        'lre_max_mkt_impact_bps': 300, # Allow 3% price impact
        
        'elevation_threshold': 10000,
    },
}


def get_scenario(name: str) -> dict:
    """Get a scenario configuration by name."""
    if name not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {name}. Available: {list(SCENARIOS.keys())}")
    return SCENARIOS[name].copy()


def list_scenarios() -> list:
    """List all available scenarios."""
    return list(SCENARIOS.keys())


def describe_scenario(name: str) -> str:
    """Get a human-readable description of a scenario."""
    descriptions = {
        'crypto_winter': """
Crypto Winter (Section 8.1)
---------------------------
Severe market drawdown: ~75% decline over 90 days
- High volatility (80% annualized)
- Elevated depeg risk (1% daily with stress correlation)
- Reduced trading volume
- Conservative lending, higher default risk

Tests: Floor protection under maximum stress
Expected: fToken floor preserves AVAX-denominated value
          LST suffers full drawdown + potential depegs
""",
        'crab_market': """
Crab Market (Section 8.2)
-------------------------
Sideways market: Low volatility, modest activity
- Slight upward drift (5% annualized)
- Moderate volatility (40%)
- Rare depegs (0.1% daily)
- Steady but modest trading

Tests: Floor elevation from fees vs LST yield
Expected: LST likely outperforms on raw return
          fToken provides strong collateral, modest floor growth
""",
        'super_cycle': """
Super Cycle (Section 8.3)
-------------------------
Strong bull market: High returns, high volatility
- Strong positive drift (70% annualized)
- High volatility (70%)
- Low depeg risk (0.2% daily)
- High trading volume and credit demand

Tests: Floor elevation and LRE in uptrend
Expected: LST captures full upside
          fToken builds floor protection while participating in gains
""",
        'flash_crash': """
Flash Crash
-----------
Extreme short-term stress: Sharp drop then recovery
- Very negative drift (-150% annualized)
- Extreme volatility (120%)
- Maximum depeg risk (2% daily)
- Volume spike, no new lending

Tests: System resilience to acute stress
Expected: Reveals maximum FPR drawdown under extreme conditions
""",
        'high_leverage': """
High Leverage Stress Test
-------------------------
Tests credit facility under aggressive lending
- Neutral market conditions
- Moderate volatility
- High loan origination
- Elevated debt cap (70%)

Tests: Credit facility risk when fully utilized
Expected: Shows headroom competition between loans and floor elevation
""",
        'long_term': """
Long-Term Accumulation
----------------------
One-year simulation with average market conditions
- Moderate positive drift (15% annualized)
- Moderate volatility (50%)
- Steady activity over extended period

Tests: Floor elevation compound effects over time
Expected: Shows long-term floor growth trajectory
""",
        'leverage_ltv80': """
High Leverage LTV 80%
---------------------
Aggressive lending at 80% LTV with high volume
- Moderate bull market (30% annualized)
- HIGH trading volume (250k daily mean)
- Aggressive lending (8k daily mean)
- LRE threshold lowered to 1.5

Tests: LRE activation and 80% LTV stress
Expected: Frequent LRE events, manageable risk
""",
        'leverage_ltv90': """
High Leverage LTV 90%
---------------------
Very aggressive lending at 90% LTV (danger zone)
- Strong bull market (40% annualized)
- VERY HIGH trading volume (300k daily mean)
- Very aggressive lending (10k daily mean)
- LRE threshold lowered to 1.3

Tests: LRE under extreme leverage, insolvency risk
Expected: High LRE activity, potential FPR stress
""",
        'leverage_ltv99': """
High Leverage LTV 99% - EXTREME
-------------------------------
Maximum stress test at 99% LTV
- Volatile bull market (50% annualized)
- EXTREME trading volume (400k daily mean)
- EXTREME lending (12k daily mean)
- LRE hair-trigger at 1.2
- Reduced coverage buffer (3%)

Tests: System limits, insolvency probability
Expected: Maximum LRE, high bad debt, stress testing boundaries
""",
    }
    return descriptions.get(name, f"No description available for scenario: {name}")


# =============================================================================
# AGENT POPULATION CONFIGURATIONS
# =============================================================================
# ETH amounts calibrated to match scenario daily_volume_mean:
# - super_cycle:    150,000 ETH/day  → agents need ~1M total ETH (15% turnover)
# - crab_market:     20,000 ETH/day  → agents need ~200k total ETH (10% turnover)
# - crypto_winter:   30,000 ETH/day  → agents need ~600k total ETH (5% turnover)

AGENT_POPULATIONS = {
    # Super Cycle: 150k daily volume, 15% turnover → ~1M total ETH
    'super_cycle': {
        'LeverageSeeker': {'count': 50, 'initial_eth': 12000.0, 'params': {'target_ltv': 0.85}},
        'YieldSeeker': {'count': 20, 'initial_eth': 8000.0},
        'DAT': {'count': 10, 'initial_eth': 15000.0},
        'Arbitrageur': {'count': 15, 'initial_eth': 6000.0},
        'FloorHolder': {'count': 5, 'initial_eth': 10000.0},
    },
    # Crab Market: 20k daily volume, 10% turnover → ~200k total ETH
    'crab_market': {
        'LeverageSeeker': {'count': 15, 'initial_eth': 2000.0},
        'YieldSeeker': {'count': 45, 'initial_eth': 2000.0},
        'DAT': {'count': 20, 'initial_eth': 2500.0},
        'FloorHolder': {'count': 15, 'initial_eth': 2000.0},
        'Arbitrageur': {'count': 5, 'initial_eth': 1500.0},
    },
    # Crypto Winter: 30k daily volume, 5% turnover → ~600k total ETH
    'crypto_winter': {
        'LeverageSeeker': {'count': 10, 'initial_eth': 4000.0, 'params': {'deleverage_drawdown': 0.05}},
        'YieldSeeker': {'count': 35, 'initial_eth': 6000.0},
        'DAT': {'count': 30, 'initial_eth': 8000.0},
        'FloorHolder': {'count': 15, 'initial_eth': 5000.0},
        'Arbitrageur': {'count': 10, 'initial_eth': 4000.0},
    },
    # Presale scenarios
    'presale_bull': {
        'LeverageSeeker': {'count': 50, 'initial_eth': 15000.0, 'params': {'target_ltv': 0.85}},
        'YieldSeeker': {'count': 30, 'initial_eth': 8000.0},
        'DAT': {'count': 20, 'initial_eth': 12000.0},
        'FloorHolder': {'count': 25, 'initial_eth': 10000.0},
    },
    'presale_neutral': {
        'LeverageSeeker': {'count': 35, 'initial_eth': 10000.0},
        'YieldSeeker': {'count': 40, 'initial_eth': 8000.0},
        'DAT': {'count': 20, 'initial_eth': 10000.0},
        'Arbitrageur': {'count': 15, 'initial_eth': 5000.0},
        'FloorHolder': {'count': 20, 'initial_eth': 8000.0},
    },
    'presale_bear': {
        'LeverageSeeker': {'count': 15, 'initial_eth': 6000.0},
        'YieldSeeker': {'count': 45, 'initial_eth': 7000.0},
        'DAT': {'count': 30, 'initial_eth': 10000.0},
        'FloorHolder': {'count': 20, 'initial_eth': 7000.0},
        'Arbitrageur': {'count': 15, 'initial_eth': 4000.0},
    },
    # High leverage stress tests
    'leverage_ltv80': {
        'LeverageSeeker': {'count': 60, 'initial_eth': 10000.0, 'params': {'target_ltv': 0.80}},
        'FloorHolder': {'count': 25, 'initial_eth': 8000.0, 'params': {'target_ltv': 0.75}},
        'YieldSeeker': {'count': 10, 'initial_eth': 5000.0},
        'DAT': {'count': 5, 'initial_eth': 8000.0},
    },
    'leverage_ltv90': {
        'LeverageSeeker': {'count': 70, 'initial_eth': 12000.0, 'params': {'target_ltv': 0.90}},
        'FloorHolder': {'count': 20, 'initial_eth': 8000.0, 'params': {'target_ltv': 0.85}},
        'YieldSeeker': {'count': 5, 'initial_eth': 4000.0},
        'DAT': {'count': 5, 'initial_eth': 8000.0},
    },
}


def get_agent_population(scenario_name: str) -> dict:
    """Get agent population config for a scenario."""
    config = AGENT_POPULATIONS.get(scenario_name, AGENT_POPULATIONS.get('crab_market', {}))
    return {k: v.copy() if isinstance(v, dict) else v for k, v in config.items()}
