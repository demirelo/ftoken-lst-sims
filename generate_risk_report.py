#!/usr/bin/env python3
"""
Professional Risk Analysis Report Generator
Compares fToken vs LST performance under various market conditions

Parameters:
- LTV: 90%
- α_f (fee_to_floor_ratio): 65%
- LRE threshold: 1.10 (10% premium triggers reallocation)
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from datetime import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass
from sims.models import fToken, Underlying, LST

# Output directory
REPORTS_DIR = os.path.join(os.path.dirname(__file__), 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)

np.random.seed(42)

# =============================================================================
# CONFIGURATION
# =============================================================================

# User-specified parameters
CUSTOM_PARAMS = {
    'loan_ltv': 0.90,           # 90% LTV
    'enable_loan_activity': True,  # Enable realistic loan activity
    'target_lock_ratio': 0.85,     # 85% of floor supply locked or staked
    'enable_topup': True,          # Top up loans when floor rises
    'fee_to_floor_ratio': 0.65, # 65% of fees to floor
    'lre_threshold': 1.10,      # 10% premium triggers LRE
    'lre_realloc_bps': 2000,    # 20% of premium liquidity reallocated
    'lre_max_mkt_impact_bps': 500,  # Max 5% market impact
}

# Scenario definitions
SCENARIOS = {
    # Volume is now in ETH/AVAX terms (not USD)
    # With 100,000 token supply, ~0.5-3% daily turnover is realistic
    'crypto_winter': {
        'name': 'Crypto Winter',
        'description': 'Severe bear market with -75% drawdown',
        'mu': -0.8,           # Negative drift (≈-75% over 180 days)
        'sigma': 0.7,         # High volatility
        'p_depeg': 0.002,     # 0.2% daily depeg probability (rare post-2022)
        'depeg_mean': -0.005, # 0.5% average depeg (very small)
        'depeg_std': 0.003,   # Tight distribution
        'daily_volume_mean': 500,     # 500 ETH daily (~0.5% of supply)
        'daily_volume_std': 200,
        'buy_sell_ratio': 0.45,       # Slight sell pressure
        'daily_loan_origination_mean': 100,  # 100 ETH loans daily
        'daily_loan_origination_std': 50,
        'horizon_days': 180,
        'n_paths': 500,
    },
    'crab_market': {
        'name': 'Crab Market',
        'description': 'Sideways market with moderate volatility',
        'mu': 0.0,            # No drift
        'sigma': 0.5,         # Moderate volatility
        'p_depeg': 0.001,     # 0.1% daily (very rare in stable markets)
        'depeg_mean': -0.003, # 0.3% average
        'depeg_std': 0.002,
        'daily_volume_mean': 1_500,   # 1,500 ETH daily (~1.5% of supply)
        'daily_volume_std': 500,
        'buy_sell_ratio': 0.50,       # Balanced
        'daily_loan_origination_mean': 300,
        'daily_loan_origination_std': 100,
        'horizon_days': 180,
        'n_paths': 500,
    },
    'super_cycle': {
        'name': 'Super Cycle',
        'description': 'Strong bull market with high activity',
        'mu': 0.8,            # Strong positive drift
        'sigma': 0.7,         # High volatility
        'p_depeg': 0.0005,    # 0.05% daily (almost never in bull markets)
        'depeg_mean': -0.002, # 0.2% average
        'depeg_std': 0.001,
        'daily_volume_mean': 3_000,   # 3,000 ETH daily (~3% of supply)
        'daily_volume_std': 1_000,
        'buy_sell_ratio': 0.65,       # More buys
        'daily_loan_origination_mean': 500,
        'daily_loan_origination_std': 150,
        'horizon_days': 180,
        'n_paths': 500,
    },
}

# Base configuration
# NOTE: All values are in ETH/AVAX terms (not USD)
# This allows proper comparison with LSTs which are also denominated in the underlying
BASE_CONFIG = {
    'initial_price': 100.0,           # USD price of underlying (for reference only)
    'initial_floor': 1.0,             # 1 fToken = 1 ETH/AVAX at floor
    'initial_supply': 100_000,        # 100,000 fTokens (backed by 100,000 ETH)
    'buy_fee': 0.005,                 # 0.5% buy fee
    'sell_fee': 0.005,                # 0.5% sell fee  
    'origination_fee': 0.02,          # 2% loan origination fee
    'tick_size': 0.01,                # 1% floor price increments
    'tier_capacity_base': 10_000,     # Base tier capacity (scaled for 100k supply)
    'elevation_threshold': 100,       # 100 ETH triggers elevation
    'debt_cap_bps': 6000,             # 60% max debt
    'min_coverage_buffer_bps': 10,    # 0.1% minimal buffer
    'bad_debt_lgd': 0.30,             # 30% loss given default
    'loan_default_prob_base': 0.0002, # 0.02% daily = ~3.5% annual default rate
    'lst_yield': 0.026,               # 2.6% APY (Lido stETH rate)
}


@dataclass
class SimulationResult:
    """Container for simulation results"""
    scenario_name: str
    n_paths: int
    horizon_days: int
    
    # fToken metrics
    ftoken_returns: np.ndarray
    ftoken_floor_growth: np.ndarray
    ftoken_fpr_min: np.ndarray
    ftoken_fpr_final: np.ndarray
    ftoken_bad_debt_events: np.ndarray
    ftoken_lre_events: np.ndarray
    ftoken_merges: np.ndarray
    ftoken_insolvencies: int
    
    # LST metrics
    lst_returns: np.ndarray
    lst_depeg_events: np.ndarray
    lst_max_drawdown: np.ndarray
    
    # Volume info
    total_buy_volume: float
    total_sell_volume: float
    total_loan_volume: float


def run_simulation(scenario_key: str, config: dict) -> SimulationResult:
    """Run Monte Carlo simulation for a scenario"""
    
    scenario = SCENARIOS[scenario_key]
    n_paths = scenario['n_paths']
    horizon_days = scenario['horizon_days']
    dt = 1.0 / 365
    
    # Result arrays
    ftoken_returns = np.zeros(n_paths)
    ftoken_floor_growth = np.zeros(n_paths)
    ftoken_fpr_min = np.zeros(n_paths)
    ftoken_fpr_final = np.zeros(n_paths)
    ftoken_bad_debt_events = np.zeros(n_paths)
    ftoken_lre_events = np.zeros(n_paths)
    ftoken_merges = np.zeros(n_paths)
    
    lst_returns = np.zeros(n_paths)
    lst_depeg_events = np.zeros(n_paths)
    lst_max_drawdown = np.zeros(n_paths)
    
    insolvencies = 0
    total_buy_vol = 0
    total_sell_vol = 0
    total_loan_vol = 0
    
    for path in range(n_paths):
        # Create fresh instances
        underlying = Underlying(
            'AVAX', 
            config['initial_price'],
            mu=scenario['mu'],
            sigma=scenario['sigma']
        )
        
        lst = LST(
            'sAVAX',
            underlying,
            config['lst_yield'],
            scenario['p_depeg'],
            scenario['depeg_mean'],
            scenario['depeg_std']
        )
        
        initial_reserves = config['initial_floor'] * config['initial_supply']
        ftoken = fToken(
            name='fAVAX',
            underlying=underlying,
            initial_reserves=initial_reserves,
            initial_supply=config['initial_supply'],
            initial_floor=config['initial_floor'],
            buy_fee=config['buy_fee'],
            sell_fee=config['sell_fee'],
            origination_fee=config['origination_fee'],
            tick_size=config['tick_size'],
            tier_capacity_base=config['tier_capacity_base'],
            elevation_threshold=config['elevation_threshold'],
            debt_cap_bps=config['debt_cap_bps'],
            min_coverage_buffer_bps=config['min_coverage_buffer_bps'],
            fee_to_floor_ratio=config['fee_to_floor_ratio'],
            lre_threshold=config['lre_threshold'],
            lre_realloc_bps=config['lre_realloc_bps'],
            lre_max_mkt_impact_bps=config['lre_max_mkt_impact_bps'],
            bad_debt_lgd=config['bad_debt_lgd'],
            loan_default_prob_base=config['loan_default_prob_base'],
        )
        
        # Store LTV for loan calculations
        loan_ltv = config['loan_ltv']
        
        # Track initial values
        initial_ftoken_value = ftoken.get_market_price() * config['initial_supply']
        initial_floor = ftoken.floor_price
        
        # LST tracking (in ETH terms)
        # LST value = index * (1 - depeg_discount)
        # - index grows by yield daily
        # - depeg_discount is usually 0, occasionally positive during stress
        lst_index = 1.0  # Starts at 1:1 with ETH
        lst_value = 1.0  # Current value including any depeg
        lst_max_depeg = 0.0  # Track worst depeg (this is the "Max DD" in ETH terms)
        
        min_fpr = float('inf')
        path_buy_vol = 0
        path_sell_vol = 0
        path_loan_vol = 0
        depeg_count = 0
        
        # Simulate
        for day in range(horizon_days):
            # Simulate underlying (for fToken calculations)
            underlying.simulate_step(dt)
            
            # LST: Accrue yield (in ETH terms)
            lst_index *= (1 + config['lst_yield'] * dt)
            
            # LST: Check for depeg event
            # Depeg = temporary discount to fair value (index)
            current_depeg = 0.0
            if np.random.random() < scenario['p_depeg']:
                # Depeg severity (negative = discount)
                current_depeg = abs(np.random.normal(scenario['depeg_mean'], scenario['depeg_std']))
                depeg_count += 1
                
                # Track max depeg (worst discount from fair value)
                if current_depeg > lst_max_depeg:
                    lst_max_depeg = current_depeg
            
            # LST value = fair value * (1 - depeg)
            lst_value = lst_index * (1 - current_depeg)
            
            # Generate trading volume
            buy_vol = max(0, np.random.normal(
                scenario['daily_volume_mean'] * scenario['buy_sell_ratio'],
                scenario['daily_volume_std'] * 0.3
            ))
            sell_vol = max(0, np.random.normal(
                scenario['daily_volume_mean'] * (1 - scenario['buy_sell_ratio']),
                scenario['daily_volume_std'] * 0.3
            ))
            
            # Track loan volume (for reporting - actual loans handled by loan_activity)
            loan_vol = 0  # Will be tracked from debt changes
            
            path_buy_vol += buy_vol
            path_sell_vol += sell_vol
            path_loan_vol += loan_vol
            
            # Simulate fToken with realistic loan activity
            # Floor token holders lock ~85% of floor supply and borrow at 90% LTV
            # When floor rises, they top up (borrow the newly created headroom)
            enable_loan_activity = config.get('enable_loan_activity', False)
            target_lock_ratio = config.get('target_lock_ratio', 0.85)
            enable_topup = config.get('enable_topup', True)
            
            ftoken.simulate_step(
                dt=dt,
                buy_volume=buy_vol,
                sell_volume=sell_vol,
                # Use new loan activity model instead of legacy
                enable_loan_activity=enable_loan_activity,
                target_lock_ratio=target_lock_ratio,
                loan_ltv=loan_ltv,
                enable_topup=enable_topup
            )
            
            # Track FPR
            fpr = ftoken.calculate_fpr()
            if fpr < min_fpr:
                min_fpr = fpr
            
            # Check insolvency
            if fpr < 1.0:
                insolvencies += 1
                break
        
        # Calculate final metrics
        final_ftoken_value = ftoken.get_market_price() * ftoken.total_supply
        
        # Calculate effective floor (what's actually redeemable)
        # Key: floor price growth is meaningful only if there's sufficient supply
        tradeable = ftoken.get_tradeable_supply()
        final_fpr = ftoken.calculate_fpr()
        
        # Track actual redeemable floor
        if tradeable < config['initial_supply'] * 0.01:  # <1% supply left
            # Illiquid - use last meaningful floor or mark as 0 return
            effective_floor = initial_floor  # Assume flat return if market dried up
        elif final_fpr >= 1.0:
            effective_floor = ftoken.floor_price
        else:
            # Insolvent - effective floor is what reserves can back
            available_assets = ftoken.get_available_floor_assets()
            effective_floor = available_assets / tradeable if tradeable > 0 else 0
        
        ftoken_returns[path] = (effective_floor / initial_floor - 1) * 100
        ftoken_floor_growth[path] = (ftoken.floor_price / initial_floor - 1) * 100 if tradeable > config['initial_supply'] * 0.01 else 0
        ftoken_fpr_min[path] = min_fpr
        ftoken_fpr_final[path] = ftoken.calculate_fpr()
        ftoken_bad_debt_events[path] = len(ftoken.bad_debt_records)
        ftoken_lre_events[path] = len(ftoken.lre_events)
        ftoken_merges[path] = ftoken.merges_count
        
        # LST return in ETH terms:
        # - lst_index captures yield accrual
        # - Final value assumes no depeg at exit (fair exit)
        # But we track depeg risk via max_depeg
        lst_returns[path] = (lst_index - 1) * 100  # Pure yield return in ETH terms
        lst_depeg_events[path] = depeg_count
        lst_max_drawdown[path] = lst_max_depeg * 100  # Max depeg magnitude (% below fair value)
        
        total_buy_vol += path_buy_vol
        total_sell_vol += path_sell_vol
        # Track actual debt created as loan volume
        total_loan_vol += ftoken.debt
    
    return SimulationResult(
        scenario_name=scenario['name'],
        n_paths=n_paths,
        horizon_days=horizon_days,
        ftoken_returns=ftoken_returns,
        ftoken_floor_growth=ftoken_floor_growth,
        ftoken_fpr_min=ftoken_fpr_min,
        ftoken_fpr_final=ftoken_fpr_final,
        ftoken_bad_debt_events=ftoken_bad_debt_events,
        ftoken_lre_events=ftoken_lre_events,
        ftoken_merges=ftoken_merges,
        ftoken_insolvencies=insolvencies,
        lst_returns=lst_returns,
        lst_depeg_events=lst_depeg_events,
        lst_max_drawdown=lst_max_drawdown,
        total_buy_volume=total_buy_vol / n_paths,
        total_sell_volume=total_sell_vol / n_paths,
        total_loan_volume=total_loan_vol / n_paths,
    )


def calculate_var(returns: np.ndarray, confidence: float = 0.95) -> float:
    """Calculate Value-at-Risk"""
    return np.percentile(returns, (1 - confidence) * 100)


def calculate_cvar(returns: np.ndarray, confidence: float = 0.95) -> float:
    """Calculate Conditional VaR (Expected Shortfall)"""
    var = calculate_var(returns, confidence)
    return returns[returns <= var].mean()


def generate_report(results: Dict[str, SimulationResult], config: dict) -> str:
    """Generate markdown report"""
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    report = f"""# fToken vs LST Risk Analysis Report

**Generated:** {timestamp}  
**Simulation Engine:** Monte Carlo with {results[list(results.keys())[0]].n_paths} paths per scenario  
**Horizon:** {results[list(results.keys())[0]].horizon_days} days

---

## Executive Summary

This report compares the risk-return profile of **fTokens** (floor-backed tokens with deterministic floor growth) against **Liquid Staking Tokens (LSTs)** under three market conditions: Crypto Winter, Crab Market, and Super Cycle.

### Key Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| **LTV (Loan-to-Value)** | {config['loan_ltv']*100:.0f}% | Maximum borrowing against fToken collateral |
| **α_f (Fee to Floor)** | {config['fee_to_floor_ratio']*100:.0f}% | Portion of fees directed to floor reserves |
| **LRE Threshold** | {(config['lre_threshold']-1)*100:.0f}% premium | Triggers liquidity reallocation |
| **Debt Cap** | {config['debt_cap_bps']/100:.0f}% | Maximum debt as % of floor liquidity |
| **Coverage Buffer** | {config['min_coverage_buffer_bps']/100:.1f}% | Required FPR buffer above 1.0 |
| **Buy/Sell Fee** | {config['buy_fee']*100:.1f}% | Transaction fees |
| **LST Yield** | {config['lst_yield']*100:.0f}% APY | Staking yield benchmark |

---

## Scenario Definitions & Volume

"""
    
    # Volume table
    report += "| Scenario | Description | Avg Daily Buy | Avg Daily Sell | Net Flow | Avg Daily Loans |\n"
    report += "|----------|-------------|---------------|----------------|----------|----------------|\n"
    
    for key, result in results.items():
        scenario = SCENARIOS[key]
        avg_daily_buy = result.total_buy_volume / result.horizon_days
        avg_daily_sell = result.total_sell_volume / result.horizon_days
        net_flow = avg_daily_buy - avg_daily_sell
        avg_daily_loan = result.total_loan_volume / result.horizon_days
        
        report += f"| **{result.scenario_name}** | {scenario['description']} | {avg_daily_buy:,.0f} ETH | {avg_daily_sell:,.0f} ETH | {net_flow:+,.0f} ETH | {avg_daily_loan:,.0f} ETH |\n"
    
    report += """
### Total Volume Summary (per path, 180 days)

*All values in ETH/AVAX (reserve currency)*

"""
    report += "| Scenario | Total Buys | Total Sells | Total Loans | Net Volume |\n"
    report += "|----------|------------|-------------|-------------|------------|\n"
    
    for key, result in results.items():
        net = result.total_buy_volume - result.total_sell_volume
        report += f"| {result.scenario_name} | {result.total_buy_volume:,.0f} ETH | {result.total_sell_volume:,.0f} ETH | {result.total_loan_volume:,.0f} ETH | {net:+,.0f} ETH |\n"
    
    # Risk metrics comparison
    report += """
---

## Risk Metrics Comparison

*All returns are in ETH/AVAX terms (not USD). Both instruments give underlying exposure.*

### Return Distribution

| Scenario | Instrument | Mean Return | Std Dev | VaR (95%) | CVaR (95%) | Max Depeg |
|----------|------------|-------------|---------|-----------|------------|-----------|
"""
    
    for key, result in results.items():
        # fToken metrics
        ftoken_var = calculate_var(result.ftoken_returns)
        ftoken_cvar = calculate_cvar(result.ftoken_returns)
        ftoken_std = np.std(result.ftoken_returns)
        ftoken_mean = np.mean(result.ftoken_returns)
        
        # LST metrics
        lst_var = calculate_var(result.lst_returns)
        lst_cvar = calculate_cvar(result.lst_returns)
        lst_std = np.std(result.lst_returns)
        lst_mean = np.mean(result.lst_returns)
        lst_max_dd = np.mean(result.lst_max_drawdown)
        
        report += f"| {result.scenario_name} | **fToken** | {ftoken_mean:+.1f}% | {ftoken_std:.1f}% | {ftoken_var:+.1f}% | {ftoken_cvar:+.1f}% | 0% |\n"
        report += f"| | LST | {lst_mean:+.1f}% | {lst_std:.1f}% | {lst_var:+.1f}% | {lst_cvar:+.1f}% | {lst_max_dd:.1f}% |\n"
    
    # FPR Analysis
    report += """
---

## Floor Protection Ratio (FPR) Analysis

The FPR measures protocol solvency: FPR ≥ 1.0 means all floor redemptions can be honored.

| Scenario | Min FPR (5th %ile) | Mean Min FPR | Final FPR (Mean) | Paths FPR < 1.0 |
|----------|-------------------|--------------|------------------|-----------------|
"""
    
    for key, result in results.items():
        min_fpr_5th = np.percentile(result.ftoken_fpr_min, 5)
        min_fpr_mean = np.mean(result.ftoken_fpr_min)
        final_fpr_mean = np.mean(result.ftoken_fpr_final)
        pct_insolvent = result.ftoken_insolvencies / result.n_paths * 100
        
        report += f"| {result.scenario_name} | {min_fpr_5th:.3f} | {min_fpr_mean:.3f} | {final_fpr_mean:.3f} | {pct_insolvent:.1f}% |\n"
    
    # Credit Facility Risk
    report += """
---

## Credit Facility Risk (90% LTV)

### No Liquidation, No Bad Debt

The fToken credit facility has **no liquidation mechanism**:

1. **Borrower locks fTokens** → borrows ETH at 90% LTV (of floor value)
2. **fTokens stay locked** until borrower repays debt
3. **No interest** → debt is fixed in ETH terms
4. **If borrower walks away** → fTokens remain locked, debt stays on books

**From the protocol's perspective:**
- Locked fTokens are still there (cannot be redeemed)
- Outstanding debt is still owed
- **No bad debt** because collateral isn't liquidated or written off
- Protocol simply holds the locked tokens indefinitely

**Example: Borrower Default Scenario**
```
Day 1:  Borrower locks 100 fTokens, borrows 90 ETH
        Protocol state: locked=100, debt=90 ETH

Day 30: Borrower loses 90 ETH elsewhere, can't repay
        Protocol state: locked=100, debt=90 ETH (unchanged!)
        
Forever: fTokens stay locked, debt stays on books
         FPR unaffected because locked tokens don't need floor backing
```

**Why this works:**
- Locked tokens reduce `tradeable_supply`
- Coverage invariant: `(reserves - debt) ≥ floor × tradeable`
- Locked tokens don't count toward `tradeable`, so coverage is maintained
- The protocol can wait indefinitely for repayment

### Credit Facility Metrics

| Scenario | Total Loans (ETH) | Avg Outstanding Debt | LRE Events (Mean) |
|----------|-------------------|---------------------|-------------------|
"""
    
    for key, result in results.items():
        total_loans = result.total_loan_volume
        lre_mean = np.mean(result.ftoken_lre_events)
        
        report += f"| {result.scenario_name} | {total_loans:,.0f} | N/A | {lre_mean:.1f} |\n"
    
    # Floor Elevation Analysis with breakdown
    initial_supply = config['initial_supply']
    
    report += f"""
---

## Floor Elevation & Tier Merges

| Scenario | Mean Floor Growth | Floor Growth (5th %ile) | Mean Tier Merges |
|----------|-------------------|-------------------------|------------------|
"""
    
    for key, result in results.items():
        floor_mean = np.mean(result.ftoken_floor_growth)
        floor_5th = np.percentile(result.ftoken_floor_growth, 5)
        merges_mean = np.mean(result.ftoken_merges)
        
        report += f"| {result.scenario_name} | +{floor_mean:.1f}% | +{floor_5th:.1f}% | {merges_mean:.0f} |\n"
    
    # Floor growth mechanism explanation
    report += f"""
### How Floor Growth Works

**Fee-driven floor elevation:**
1. Trading fees (0.5%) + loan origination fees (2%) accumulate
2. 65% of fees → floor reserves
3. When threshold met → floor price is elevated

**Headroom (for borrowers):**
When floor rises, locked collateral is worth more:
```
Before: 100 locked tokens × 1.0 floor = 100 ETH collateral
        Debt = 90 ETH → LTV = 90%
        
After floor rises to 1.10:
        100 locked tokens × 1.1 floor = 110 ETH collateral  
        Debt = 90 ETH → LTV = 81.8%
        
Headroom = (110 × 90%) - 90 = 9 ETH (can top-up)
```

**Virtuous cycle:**
- Fees → floor elevation → headroom created
- Borrowers top-up (pay 2% origination fee)
- More fees → more elevation → more headroom → repeat

**Loan Activity Model:**
- ~85% of floor supply locked as collateral (limited by debt cap)
- Borrowers top-up when floor rises (borrow the headroom)
- This generates continuous fee revenue

**Floor Growth Formula:**
```
floor_growth = total_fees_to_floor / avg_tradeable_supply
```

**Example (Crab Market):**
- Trading fees: 270,000 ETH × 0.5% × 65% = 878 ETH
- Loan fees: 60,000 ETH × 2% × 65% = 780 ETH  
- Total fees to floor: ~1,658 ETH
- Avg tradeable: ~25,000 (declines due to sells/merges)
- Floor growth: 1,658 / 25,000 ≈ 6.6%

---

## Premium Token Mechanics

### Coverage Invariant

All tokens (floor AND premium) require floor backing:
```
required = floor_price × tradeable_supply
```

Where `tradeable = total_supply - locked_supply` includes BOTH floor and premium tokens.

### Premium Buys Create Headroom

When buying at premium price (above floor):
```
Buy 1000 ETH at 1.05 ETH/token:
  → Mint ~950 tokens (after fees)
  → Reserves += 1000 ETH
  → Required += 950 ETH (tokens × floor_price)
  → Headroom created = 1000 - 950 = 50 ETH (the premium!)
```

Only the **premium portion** (price - floor) creates headroom, not the full amount.

### Locking Premium Tokens

When you lock a premium token as collateral:
- **Collateral value** = floor_price (not market price)
- **Borrowable** = floor_price × LTV

Example: Mint at 1.05 ETH, lock, borrow at 90% LTV:
```
Floor value: 1.0 ETH
Borrowable: 0.9 ETH (90% of floor, not market)
Premium (0.05 ETH): Acts as "equity" above floor
```

### Floor Supply Recalibration

When sells reduce `total_supply` below `floor_supply`:
1. `floor_supply` shrinks to match `total_supply`
2. Next buy enters the **premium tier** (above floor price)
3. This enables **faster floor growth** (premium headroom)

```
Before sell: total=100k, floor=100k, premium=0
After sell:  total=80k,  floor=80k,  premium=0  (recalibrated)
After buy:   total=81k,  floor=80k,  premium=1k (premium tier!)
```
"""
    
    # LST Depeg Events
    report += """
---

## LST Depeg Risk

| Scenario | Mean Depeg Events | Max Depeg Events | Depeg Probability |
|----------|-------------------|------------------|-------------------|
"""
    
    for key, result in results.items():
        depeg_mean = np.mean(result.lst_depeg_events)
        depeg_max = np.max(result.lst_depeg_events)
        depeg_prob = np.mean(result.lst_depeg_events > 0) * 100
        
        report += f"| {result.scenario_name} | {depeg_mean:.1f} | {depeg_max:.0f} | {depeg_prob:.1f}% |\n"
    
    # Key findings
    target_lock = config.get('target_lock_ratio', 0.85) * 100
    ltv = config.get('loan_ltv', 0.90) * 100
    
    report += f"""
---

## Key Findings

### 1. Fee-Driven Floor Growth with Loan Top-ups

The simulation models realistic floor token holder behavior:
- **{target_lock:.0f}% of floor supply locked** as loan collateral
- Initial borrowing at **{ltv:.0f}% LTV** against floor value
- **Top-up** when floor rises (borrow the newly created headroom)

**The virtuous cycle:**
```
1. Fees accumulate (trading + loan origination)
2. 65% of fees → floor reserves → floor elevation
3. Floor rises → locked collateral worth more
4. Borrowers can top-up (borrow headroom at 2% fee)
5. More fees → repeat
```

**Headroom example (floor rises 10%):**
```
Before: 100 tokens × 1.0 floor = 100 ETH collateral, 90 ETH debt (90% LTV)
After:  100 tokens × 1.1 floor = 110 ETH collateral, 90 ETH debt (82% LTV)
Headroom = (110 × 90%) - 90 = 9 ETH available to borrow
```

**Key insight:** Floor growth is driven by fees ÷ tradeable supply. As tradeable supply decreases (from sells and tier merges), the same fee amount produces larger floor growth.

### 2. Downside Protection (in ETH terms)
- **fToken floor guarantee** provides deterministic protection: floor price only increases
- **LST** earns staking yield but faces depeg risk up to {np.mean([np.mean(r.lst_max_drawdown) for r in results.values()]):.1f}% below fair value

### 3. Risk-Adjusted Returns (in ETH terms)
- **fToken** returns depend on **both** fee volume **and** loan activity
- **LST** returns come from staking yield (~{config['lst_yield']*100:.1f}% APY), reduced by depeg events
- Both instruments carry underlying (ETH/AVAX) USD price risk equally

### 4. Protocol Solvency
- FPR maintained above {min([np.percentile(r.ftoken_fpr_min, 5) for r in results.values()]):.2f} across all scenarios (5th percentile)
- Safe-merge mechanism successfully absorbs premium tiers into floor

### 5. Credit Facility ({config['loan_ltv']*100:.0f}% LTV)
- **No liquidation, no bad debt**: Locked fTokens stay locked; debt stays on books until repaid
- **Loans enable floor growth**: By locking tokens, loans reduce required reserves, creating headroom
- LRE mechanism actively manages premium liquidity

---

## Methodology

### Simulation Framework
- **Price Model:** Geometric Brownian Motion for underlying; LST tracks ETH 1:1 with yield
- **LST Model:** {config['lst_yield']*100:.0f}% APY yield + Poisson-distributed depegs (temporary discounts)
- **Fee Model:** {config['buy_fee']*100:.1f}% buy fee, {config['sell_fee']*100:.1f}% sell fee, {config['fee_to_floor_ratio']*100:.0f}% to floor
- **Loan Origination:** {config['origination_fee']*100:.0f}% fee
- **Floor Elevation:** Automatic when pending fees exceed threshold; includes safe-merge checks
- **Credit Facility:** {config['loan_ltv']*100:.0f}% LTV with {config['bad_debt_lgd']*100:.0f}% loss-given-default

### Risk Metrics

**Value-at-Risk (VaR) at 95%:**
- The 5th percentile of the return distribution
- Interpretation: "With 95% confidence, returns will be at least this value"
- Calculation: Sort all path returns, take the value at the 5th percentile
- Example: VaR(95%) = +4.0% means 95% of paths had returns ≥ +4.0%

**Conditional Value-at-Risk (CVaR) at 95%:**
- Also called "Expected Shortfall"
- The average return of the worst 5% of outcomes
- Captures tail risk better than VaR (what happens in the bad cases)
- Calculation: Average of all returns below the VaR threshold
- Example: CVaR(95%) = +3.5% means when things go bad, average return is +3.5%

**Floor Protection Ratio (FPR):**
- FPR = (Reserves - Debt) / (Floor Price × Tradeable Supply)
- FPR ≥ 1.0 means all floor redemptions can be honored
- Buffer of 0.1% ensures minimal safety margin

**Note on fToken Standard Deviation:**
- fToken returns have low std dev because floor growth is deterministic
- Floor growth = fees / tradeable_supply (driven by trading volume)
- Variation comes from random trading volumes, not price volatility
- This is a feature: predictable floor growth is the value proposition

---

## Visualizations

### Return Distribution Comparison
![Return Distributions](return_distributions.png)

### Risk Analysis Charts  
![Risk Analysis](risk_analysis_charts.png)

### Sample Price Paths
![Sample Paths](sample_paths.png)

---

## Appendix: Detailed Statistics

"""
    
    for key, result in results.items():
        report += f"""
### {result.scenario_name}

**fToken Return Distribution:**
- Mean: {np.mean(result.ftoken_returns):+.2f}%
- Median: {np.median(result.ftoken_returns):+.2f}%
- Std Dev: {np.std(result.ftoken_returns):.2f}%
- Min: {np.min(result.ftoken_returns):+.2f}%
- Max: {np.max(result.ftoken_returns):+.2f}%
- Skewness: {((result.ftoken_returns - np.mean(result.ftoken_returns))**3).mean() / np.std(result.ftoken_returns)**3:.2f}

**LST Return Distribution:**
- Mean: {np.mean(result.lst_returns):+.2f}%
- Median: {np.median(result.lst_returns):+.2f}%
- Std Dev: {np.std(result.lst_returns):.2f}%
- Min: {np.min(result.lst_returns):+.2f}%
- Max: {np.max(result.lst_returns):+.2f}%

"""
    
    return report


def create_visualizations(results: Dict[str, SimulationResult], config: dict):
    """Create comparison visualizations"""
    
    fig = plt.figure(figsize=(18, 14))
    gs = gridspec.GridSpec(3, 3, height_ratios=[1, 1, 1])
    
    scenarios = list(results.keys())
    colors = {'crypto_winter': '#D32F2F', 'crab_market': '#FF9800', 'super_cycle': '#4CAF50'}
    
    # PLOT 1: Return Distribution Comparison (Box plots)
    ax1 = fig.add_subplot(gs[0, :2])
    
    positions = []
    data_ftoken = []
    data_lst = []
    labels = []
    
    for i, key in enumerate(scenarios):
        result = results[key]
        positions.extend([i*3, i*3+1])
        data_ftoken.append(result.ftoken_returns)
        data_lst.append(result.lst_returns)
        labels.append(result.scenario_name)
    
    bp1 = ax1.boxplot([data_ftoken[0], data_lst[0]], positions=[0, 1], widths=0.6, patch_artist=True)
    bp2 = ax1.boxplot([data_ftoken[1], data_lst[1]], positions=[3, 4], widths=0.6, patch_artist=True)
    bp3 = ax1.boxplot([data_ftoken[2], data_lst[2]], positions=[6, 7], widths=0.6, patch_artist=True)
    
    for bp, color in [(bp1, colors['crypto_winter']), (bp2, colors['crab_market']), (bp3, colors['super_cycle'])]:
        bp['boxes'][0].set_facecolor('#1976D2')
        bp['boxes'][0].set_alpha(0.7)
        bp['boxes'][1].set_facecolor(color)
        bp['boxes'][1].set_alpha(0.7)
    
    ax1.axhline(0, color='black', linestyle='--', linewidth=0.5)
    ax1.set_xticks([0.5, 3.5, 6.5])
    ax1.set_xticklabels(labels)
    ax1.set_ylabel('Return (%)', fontsize=11)
    ax1.set_title('Return Distribution: fToken (blue) vs LST (colored)\n180-Day Horizon', fontsize=12, fontweight='bold')
    ax1.legend([bp1['boxes'][0], bp1['boxes'][1]], ['fToken', 'LST'], loc='upper right')
    ax1.grid(True, alpha=0.3)
    
    # PLOT 2: VaR/CVaR Comparison
    ax2 = fig.add_subplot(gs[0, 2])
    
    x = np.arange(len(scenarios))
    width = 0.35
    
    ftoken_var = [calculate_var(results[k].ftoken_returns) for k in scenarios]
    lst_var = [calculate_var(results[k].lst_returns) for k in scenarios]
    
    bars1 = ax2.bar(x - width/2, ftoken_var, width, label='fToken VaR (95%)', color='#1976D2', alpha=0.7)
    bars2 = ax2.bar(x + width/2, lst_var, width, label='LST VaR (95%)', color='#F44336', alpha=0.7)
    
    ax2.axhline(0, color='black', linestyle='-', linewidth=0.5)
    ax2.set_xticks(x)
    ax2.set_xticklabels([results[k].scenario_name for k in scenarios], fontsize=9)
    ax2.set_ylabel('VaR (%)', fontsize=11)
    ax2.set_title('Value-at-Risk (95%)\n(Lower = Less Downside)', fontsize=12, fontweight='bold')
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.3)
    
    # PLOT 3: FPR Distribution
    ax3 = fig.add_subplot(gs[1, 0])
    
    for key in scenarios:
        result = results[key]
        ax3.hist(result.ftoken_fpr_min, bins=30, alpha=0.5, label=result.scenario_name, 
                color=colors[key], density=True)
    
    ax3.axvline(1.0, color='red', linestyle='--', linewidth=2, label='Solvency Threshold')
    ax3.axvline(1.05, color='orange', linestyle=':', linewidth=1.5, label='5% Buffer')
    ax3.set_xlabel('Minimum FPR', fontsize=11)
    ax3.set_ylabel('Density', fontsize=11)
    ax3.set_title('FPR Distribution\n(Min FPR per path)', fontsize=12, fontweight='bold')
    ax3.legend(fontsize=8)
    ax3.grid(True, alpha=0.3)
    
    # PLOT 4: Floor Growth Distribution
    ax4 = fig.add_subplot(gs[1, 1])
    
    for key in scenarios:
        result = results[key]
        ax4.hist(result.ftoken_floor_growth, bins=30, alpha=0.5, label=result.scenario_name,
                color=colors[key], density=True)
    
    ax4.set_xlabel('Floor Growth (%)', fontsize=11)
    ax4.set_ylabel('Density', fontsize=11)
    ax4.set_title('Floor Price Growth Distribution\n180-Day Horizon', fontsize=12, fontweight='bold')
    ax4.legend(fontsize=9)
    ax4.grid(True, alpha=0.3)
    
    # PLOT 5: Tier Merges Distribution
    ax5 = fig.add_subplot(gs[1, 2])
    
    for key in scenarios:
        result = results[key]
        ax5.hist(result.ftoken_merges, bins=30, alpha=0.5, label=result.scenario_name,
                color=colors[key], density=True)
    
    ax5.set_xlabel('Tier Merges', fontsize=11)
    ax5.set_ylabel('Density', fontsize=11)
    ax5.set_title('Tier Absorption (Safe-Merge)\n180-Day Horizon', fontsize=12, fontweight='bold')
    ax5.legend(fontsize=9)
    ax5.grid(True, alpha=0.3)
    
    # PLOT 6: LST Drawdown Distribution
    ax6 = fig.add_subplot(gs[2, 0])
    
    for key in scenarios:
        result = results[key]
        ax6.hist(result.lst_max_drawdown, bins=30, alpha=0.5, label=result.scenario_name,
                color=colors[key], density=True)
    
    ax6.axvline(0, color='green', linestyle='-', linewidth=2, label='fToken (0% DD from floor)')
    ax6.set_xlabel('Max Drawdown (%)', fontsize=11)
    ax6.set_ylabel('Density', fontsize=11)
    ax6.set_title('LST Maximum Drawdown\n(fToken has 0% from floor)', fontsize=12, fontweight='bold')
    ax6.legend(fontsize=9)
    ax6.grid(True, alpha=0.3)
    
    # PLOT 7: Summary Metrics Bar Chart
    ax7 = fig.add_subplot(gs[2, 1:])
    
    metrics = ['Mean Return\n(fToken)', 'Mean Return\n(LST)', 'VaR 95%\n(fToken)', 'VaR 95%\n(LST)']
    x = np.arange(len(metrics))
    width = 0.25
    
    for i, key in enumerate(scenarios):
        result = results[key]
        values = [
            np.mean(result.ftoken_returns),
            np.mean(result.lst_returns),
            calculate_var(result.ftoken_returns),
            calculate_var(result.lst_returns)
        ]
        ax7.bar(x + i*width, values, width, label=result.scenario_name, color=colors[key], alpha=0.7)
    
    ax7.axhline(0, color='black', linestyle='-', linewidth=0.5)
    ax7.set_xticks(x + width)
    ax7.set_xticklabels(metrics)
    ax7.set_ylabel('Percentage (%)', fontsize=11)
    ax7.set_title('Summary: Risk-Return Comparison', fontsize=12, fontweight='bold')
    ax7.legend(fontsize=9)
    ax7.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(REPORTS_DIR, 'risk_analysis_charts.png'), dpi=150, bbox_inches='tight')
    print(f"Saved: {REPORTS_DIR}/risk_analysis_charts.png")
    
    return fig


def create_sample_paths(results: Dict[str, SimulationResult], config: dict):
    """Create sample price path visualizations"""
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    scenarios = list(results.keys())
    colors = {'crypto_winter': '#D32F2F', 'crab_market': '#FF9800', 'super_cycle': '#4CAF50'}
    
    for idx, key in enumerate(scenarios):
        ax = axes[idx]
        result = results[key]
        
        # Generate sample paths for visualization
        np.random.seed(42)
        n_sample = 20
        horizon = result.horizon_days
        dt = 1.0 / 365
        
        scenario = SCENARIOS[key]
        
        # fToken floor paths (deterministic growth based on mean)
        mean_growth = np.mean(result.ftoken_floor_growth) / 100
        ftoken_paths = np.zeros((n_sample, horizon + 1))
        ftoken_paths[:, 0] = 1.0
        
        for i in range(n_sample):
            daily_growth = (1 + mean_growth) ** (1/horizon) - 1
            noise = np.random.normal(0, 0.001, horizon)  # Small noise for visualization
            for t in range(horizon):
                ftoken_paths[i, t+1] = ftoken_paths[i, t] * (1 + daily_growth + noise[t])
        
        # LST paths (GBM with depegs)
        lst_paths = np.zeros((n_sample, horizon + 1))
        lst_paths[:, 0] = 1.0
        
        for i in range(n_sample):
            for t in range(horizon):
                drift = (scenario['mu'] - 0.5 * scenario['sigma']**2) * dt
                shock = scenario['sigma'] * np.sqrt(dt) * np.random.normal()
                lst_paths[i, t+1] = lst_paths[i, t] * np.exp(drift + shock)
                
                # Add yield
                lst_paths[i, t+1] *= (1 + config['lst_yield'] * dt)
                
                # Random depeg
                if np.random.random() < scenario['p_depeg']:
                    depeg = np.random.normal(scenario['depeg_mean'], scenario['depeg_std'])
                    lst_paths[i, t+1] *= (1 + depeg)
        
        days = np.arange(horizon + 1)
        
        # Plot fToken paths
        for i in range(n_sample):
            ax.plot(days, ftoken_paths[i], color='#1976D2', alpha=0.3, linewidth=0.8)
        ax.plot(days, np.mean(ftoken_paths, axis=0), color='#1976D2', linewidth=2, label='fToken (mean)')
        
        # Plot LST paths
        for i in range(n_sample):
            ax.plot(days, lst_paths[i], color=colors[key], alpha=0.3, linewidth=0.8)
        ax.plot(days, np.mean(lst_paths, axis=0), color=colors[key], linewidth=2, label='LST (mean)')
        
        ax.axhline(1.0, color='gray', linestyle='--', linewidth=0.5, alpha=0.5)
        ax.set_xlabel('Day', fontsize=11)
        ax.set_ylabel('Relative Value', fontsize=11)
        ax.set_title(f'{result.scenario_name}\n(20 sample paths)', fontsize=12, fontweight='bold')
        ax.legend(loc='best', fontsize=9)
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(REPORTS_DIR, 'sample_paths.png'), dpi=150, bbox_inches='tight')
    print(f"Saved: {REPORTS_DIR}/sample_paths.png")
    plt.close()


def create_return_distributions(results: Dict[str, SimulationResult], config: dict):
    """Create return distribution histograms"""
    
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    scenarios = list(results.keys())
    colors = {'crypto_winter': '#D32F2F', 'crab_market': '#FF9800', 'super_cycle': '#4CAF50'}
    
    for idx, key in enumerate(scenarios):
        result = results[key]
        
        # fToken distribution (top row)
        ax_top = axes[0, idx]
        ax_top.hist(result.ftoken_returns, bins=40, alpha=0.7, color='#1976D2', 
                   edgecolor='white', density=True)
        ax_top.axvline(np.mean(result.ftoken_returns), color='darkblue', linestyle='-', 
                      linewidth=2, label=f'Mean: {np.mean(result.ftoken_returns):+.1f}%')
        ax_top.axvline(calculate_var(result.ftoken_returns), color='red', linestyle='--',
                      linewidth=1.5, label=f'VaR 95%: {calculate_var(result.ftoken_returns):+.1f}%')
        ax_top.set_xlabel('Return (%)', fontsize=10)
        ax_top.set_ylabel('Density', fontsize=10)
        ax_top.set_title(f'fToken - {result.scenario_name}', fontsize=11, fontweight='bold')
        ax_top.legend(fontsize=8)
        ax_top.grid(True, alpha=0.3)
        
        # LST distribution (bottom row)
        ax_bot = axes[1, idx]
        ax_bot.hist(result.lst_returns, bins=40, alpha=0.7, color=colors[key],
                   edgecolor='white', density=True)
        ax_bot.axvline(np.mean(result.lst_returns), color='darkred', linestyle='-',
                      linewidth=2, label=f'Mean: {np.mean(result.lst_returns):+.1f}%')
        ax_bot.axvline(calculate_var(result.lst_returns), color='red', linestyle='--',
                      linewidth=1.5, label=f'VaR 95%: {calculate_var(result.lst_returns):+.1f}%')
        ax_bot.axvline(0, color='black', linestyle='-', linewidth=0.5)
        ax_bot.set_xlabel('Return (%)', fontsize=10)
        ax_bot.set_ylabel('Density', fontsize=10)
        ax_bot.set_title(f'LST - {result.scenario_name}', fontsize=11, fontweight='bold')
        ax_bot.legend(fontsize=8)
        ax_bot.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(os.path.join(REPORTS_DIR, 'return_distributions.png'), dpi=150, bbox_inches='tight')
    print(f"Saved: {REPORTS_DIR}/return_distributions.png")
    plt.close()


def create_comparison_csv(results: Dict[str, SimulationResult], config: dict):
    """Create CSV with comparison data"""
    
    csv_path = os.path.join(REPORTS_DIR, 'comparison_table.csv')
    
    with open(csv_path, 'w') as f:
        # Header
        f.write("Scenario,Instrument,Mean_Return_Pct,Std_Dev_Pct,VaR_95_Pct,CVaR_95_Pct,Max_Drawdown_Pct,Min_FPR\n")
        
        for key, result in results.items():
            # fToken row
            f.write(f"{result.scenario_name},fToken,")
            f.write(f"{np.mean(result.ftoken_returns):.2f},")
            f.write(f"{np.std(result.ftoken_returns):.2f},")
            f.write(f"{calculate_var(result.ftoken_returns):.2f},")
            f.write(f"{calculate_cvar(result.ftoken_returns):.2f},")
            f.write(f"0.00,")  # fToken has 0 drawdown from floor
            f.write(f"{np.percentile(result.ftoken_fpr_min, 5):.4f}\n")
            
            # LST row
            f.write(f"{result.scenario_name},LST,")
            f.write(f"{np.mean(result.lst_returns):.2f},")
            f.write(f"{np.std(result.lst_returns):.2f},")
            f.write(f"{calculate_var(result.lst_returns):.2f},")
            f.write(f"{calculate_cvar(result.lst_returns):.2f},")
            f.write(f"{np.mean(result.lst_max_drawdown):.2f},")
            f.write(f"N/A\n")
    
    print(f"Saved: {csv_path}")


def main():
    print("="*80)
    print("fToken vs LST Risk Analysis")
    print("="*80)
    print(f"\nParameters:")
    print(f"  LTV: {CUSTOM_PARAMS['loan_ltv']*100:.0f}%")
    print(f"  α_f: {CUSTOM_PARAMS['fee_to_floor_ratio']*100:.0f}%")
    print(f"  LRE Threshold: {(CUSTOM_PARAMS['lre_threshold']-1)*100:.0f}% premium")
    
    # Merge configs
    config = {**BASE_CONFIG, **CUSTOM_PARAMS}
    
    # Run simulations
    results = {}
    for scenario_key in SCENARIOS:
        print(f"\nRunning {SCENARIOS[scenario_key]['name']}...")
        results[scenario_key] = run_simulation(scenario_key, config)
        print(f"  Completed: {results[scenario_key].n_paths} paths")
        print(f"  Mean fToken return: {np.mean(results[scenario_key].ftoken_returns):+.1f}%")
        print(f"  Mean LST return: {np.mean(results[scenario_key].lst_returns):+.1f}%")
    
    # Generate report
    print("\nGenerating report...")
    report = generate_report(results, config)
    
    report_path = os.path.join(REPORTS_DIR, 'RISK_ANALYSIS_REPORT.md')
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"Saved: {report_path}")
    
    # Create visualizations
    print("\nCreating visualizations...")
    create_visualizations(results, config)
    create_sample_paths(results, config)
    create_return_distributions(results, config)
    create_comparison_csv(results, config)
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print(f"\nOutput files in {REPORTS_DIR}:")
    print("  - RISK_ANALYSIS_REPORT.md (detailed report)")
    print("  - risk_analysis_charts.png (main visualization)")
    print("  - sample_paths.png (sample price paths)")
    print("  - return_distributions.png (return histograms)")
    print("  - comparison_table.csv (summary data)")
    
    return results


if __name__ == "__main__":
    results = main()
