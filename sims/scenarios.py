SCENARIOS = {
    'crypto_winter': {
        'n_paths': 1000,  # Increased from 100 for better statistics (Paper A.2)
        'horizon_days': 90,
        'dt': 1/365,
        'initial_price': 100.0,
        'mu': -0.8,  # Severe drawdown
        'sigma': 0.8,  # High volatility
        'staking_yield': 0.05,
        'initial_reserves': 1100000,  # FPR = 1.10 initially (Paper Section 9.3)
        'initial_supply': 1000000,   
        'initial_floor': 1.0,
        'buy_fee': 0.003,  # 0.3% per user spec
        'sell_fee': 0.005,  # 0.5% per user spec
        'origination_fee': 0.02,  # 2% per user spec
        'elevation_threshold': 2000,  # ~0.2% of reserves
        'daily_volume_mean': 30000,  # Reduced in stress
        'daily_volume_std': 15000,
        'daily_loan_origination_mean': 500,  # Conservative in crisis
        'daily_loan_origination_std': 250,
        'p_depeg': 0.01,  # Paper A.4: ~1% per day in stress
        'depeg_mean': -0.05,  # Paper A.4: -5% center
        'depeg_std': 0.03,  # Tail to -20%
        'tier_schedule': 'harmonic',  # Paper Appendix B
        'tier_capacity': 100000  # kappa * S_base in harmonic formula
    },
    'crab_market': {
        'n_paths': 1000,
        'horizon_days': 90,
        'dt': 1/365,
        'initial_price': 100.0,
        'mu': 0.05,  # Slight upward drift
        'sigma': 0.4,  # Moderate volatility
        'staking_yield': 0.05,
        'initial_reserves': 1100000,  # FPR = 1.10
        'initial_supply': 1000000,
        'initial_floor': 1.0,
        'buy_fee': 0.003,
        'sell_fee': 0.005,
        'origination_fee': 0.02,
        'elevation_threshold': 1000,
        'daily_volume_mean': 20000,  # Low activity
        'daily_volume_std': 5000,
        'daily_loan_origination_mean': 300,
        'daily_loan_origination_std': 150,
        'p_depeg': 0.001,  # Paper A.4: rare in normal conditions
        'depeg_mean': -0.03,
        'depeg_std': 0.02,
        'tier_schedule': 'harmonic',
        'tier_capacity': 100000
    },
    'super_cycle': {
        'n_paths': 1000,
        'horizon_days': 90,
        'dt': 1/365,
        'initial_price': 100.0,
        'mu': 1.2,  # Strong bull market
        'sigma': 0.9,  # High volatility
        'staking_yield': 0.05,
        'initial_reserves': 1100000,  # FPR = 1.10
        'initial_supply': 1000000,
        'initial_floor': 1.0,
        'buy_fee': 0.003,
        'sell_fee': 0.005,
        'origination_fee': 0.02,
        'elevation_threshold': 5000,  # Large batch for high volume
        'daily_volume_mean': 150000,  # High demand
        'daily_volume_std': 50000,
        'daily_loan_origination_mean': 3000,  # Strong credit demand
        'daily_loan_origination_std': 1500,
        'p_depeg': 0.002,  # Low but non-zero
        'depeg_mean': -0.02,  # Smaller depegs in bull
        'depeg_std': 0.01,
        'tier_schedule': 'harmonic',
        'tier_capacity': 100000
    }
}
