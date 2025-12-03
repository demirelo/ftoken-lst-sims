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
    
    # fToken fees (per spec)
    'buy_fee': 0.003,       # 0.3%
    'sell_fee': 0.005,      # 0.5%
    'origination_fee': 0.02, # 2%
    
    # fToken governance (per Section 10)
    'debt_cap_bps': 5000,             # 50% max debt-to-liquidity
    'min_coverage_buffer_bps': 500,   # 5% extra coverage required
    'tier_schedule': 'harmonic',      # Per Appendix B
    'tier_capacity': 100000,          # Base tier capacity
    
    # LRE parameters (per Section 10.3)
    'lre_realloc_bps': 2000,          # 20% of excess per operation
    'lre_max_mkt_impact_bps': 200,    # 2% max price impact
    'lre_threshold': 2.0,             # Trigger when premium 2x floor
    
    # Credit facility
    'loan_ltv': 0.7,                  # 70% LTV
    
    # Bad debt (per Section 9.2)
    'bad_debt_lgd': 0.3,              # 30% loss-given-default
    'loan_default_prob_base': 0.001,  # 0.1% base default rate per step
    
    # LST yield
    'staking_yield': 0.05,            # 5% APY
    
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
        
        # Credit demand drops significantly
        'daily_loan_origination_mean': 500,
        'daily_loan_origination_std': 250,
        
        # Higher default risk in crisis
        'loan_default_prob_base': 0.003,  # 3x normal default rate
        
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
        
        # Some credit demand
        'daily_loan_origination_mean': 300,
        'daily_loan_origination_std': 150,
        
        # Normal default risk
        'loan_default_prob_base': 0.001,
        
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
        
        # Strong credit demand
        'daily_loan_origination_mean': 3000,
        'daily_loan_origination_std': 1500,
        
        # Lower default risk in bull
        'loan_default_prob_base': 0.0005,  # 0.05% default rate
        
        # Higher elevation threshold for batching
        'elevation_threshold': 5000,
    },
    
    # =========================================================================
    # ADDITIONAL STRESS SCENARIOS
    # =========================================================================
    
    # Flash crash with recovery
    'flash_crash': {
        **BASE_CONFIG,
        'n_paths': 500,
        'horizon_days': 30,
        
        # Sharp initial drop then recovery
        'mu': -1.5,           # Extreme negative drift
        'sigma': 1.2,         # Very high volatility
        
        # Maximum stress depeg conditions
        'p_depeg': 0.02,      # 2% daily during crash
        'depeg_mean': -0.08,
        'depeg_std': 0.05,
        
        # Volume spike during panic
        'daily_volume_mean': 100000,
        'daily_volume_std': 50000,
        
        # No new loans during crash
        'daily_loan_origination_mean': 0,
        'daily_loan_origination_std': 0,
        
        # High default risk
        'loan_default_prob_base': 0.01,
        
        'elevation_threshold': 1000,
    },
    
    # High leverage stress test
    'high_leverage': {
        **BASE_CONFIG,
        'n_paths': 500,
        
        # Moderate market conditions
        'mu': 0.0,
        'sigma': 0.5,
        
        'p_depeg': 0.002,
        'depeg_mean': -0.03,
        'depeg_std': 0.02,
        
        # Normal trading
        'daily_volume_mean': 50000,
        'daily_volume_std': 15000,
        
        # Aggressive lending
        'daily_loan_origination_mean': 5000,
        'daily_loan_origination_std': 2000,
        
        # Higher debt cap for this test
        'debt_cap_bps': 7000,  # 70% max debt
        
        # Normal defaults
        'loan_default_prob_base': 0.001,
        
        'elevation_threshold': 2000,
    },
    
    # Long-term accumulation (1 year)
    'long_term': {
        **BASE_CONFIG,
        'n_paths': 500,
        'horizon_days': 365,
        
        # Long-term average returns
        'mu': 0.15,           # 15% annualized
        'sigma': 0.5,         # Moderate volatility
        
        'p_depeg': 0.001,
        'depeg_mean': -0.03,
        'depeg_std': 0.02,
        
        'daily_volume_mean': 30000,
        'daily_volume_std': 10000,
        
        'daily_loan_origination_mean': 500,
        'daily_loan_origination_std': 250,
        
        'loan_default_prob_base': 0.001,
        
        'elevation_threshold': 3000,
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
    }
    return descriptions.get(name, f"No description available for scenario: {name}")
