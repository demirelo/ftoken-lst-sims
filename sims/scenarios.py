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
        'daily_volume_mean': 250000,   # 2.5x higher than super_cycle
        'daily_volume_std': 80000,
        
        # AGGRESSIVE LENDING at 80% LTV
        'daily_loan_origination_mean': 8000,
        'daily_loan_origination_std': 3000,
        'loan_ltv': 0.80,              # 80% LTV
        
        # Higher debt cap to allow aggressive lending
        'debt_cap_bps': 6000,          # 60% max debt
        
        # Lower LRE threshold for activation
        'lre_threshold': 1.5,          # Trigger when premium 1.5x floor
        'lre_realloc_bps': 2500,       # 25% reallocation
        
        # Default risk
        'loan_default_prob_base': 0.0008,
        
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
        
        # VERY HIGH VOLUME
        'daily_volume_mean': 300000,   # 3x super_cycle
        'daily_volume_std': 100000,
        
        # VERY AGGRESSIVE LENDING at 90% LTV
        'daily_loan_origination_mean': 10000,
        'daily_loan_origination_std': 4000,
        'loan_ltv': 0.90,              # 90% LTV - DANGER ZONE
        
        # Maximum debt cap
        'debt_cap_bps': 7000,          # 70% max debt
        
        # Lower LRE threshold + aggressive reallocation
        'lre_threshold': 1.3,          # Very sensitive LRE
        'lre_realloc_bps': 3000,       # 30% reallocation
        
        # Higher default risk
        'loan_default_prob_base': 0.0012,
        
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
        
        # EXTREME VOLUME to stress-test system
        'daily_volume_mean': 400000,   # 4x super_cycle
        'daily_volume_std': 150000,
        
        # EXTREME LENDING at 99% LTV
        'daily_loan_origination_mean': 12000,
        'daily_loan_origination_std': 5000,
        'loan_ltv': 0.99,              # 99% LTV - MAXIMUM RISK
        
        # Maximum debt cap
        'debt_cap_bps': 8000,          # 80% max debt (extreme)
        
        # Minimum coverage buffer reduced for extreme test
        'min_coverage_buffer_bps': 300,  # 3% buffer (reduced)
        
        # Aggressive LRE
        'lre_threshold': 1.2,          # Hair-trigger LRE
        'lre_realloc_bps': 3500,       # 35% reallocation
        'lre_max_mkt_impact_bps': 300, # Allow 3% price impact
        
        # Very high default risk
        'loan_default_prob_base': 0.002,
        'bad_debt_lgd': 0.4,           # 40% loss-given-default
        
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

