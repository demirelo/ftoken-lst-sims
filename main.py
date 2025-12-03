"""
fToken/LST Monte Carlo Simulation Main Script

This script runs Monte Carlo simulations comparing fToken floor-backed tokens
against LST (Liquid Staking Tokens) under various market conditions.

The simulation models are designed as Python twins of the Solidity Floor_v1.sol
contract, implementing:
- Solvency invariant: L_f - D >= P_f * S_tradeable
- FPR (Floor Protection Ratio) tracking
- LRE (Liquidity Reallocation Elevation)
- Bad debt mechanics
- Tier merging with harmonic schedule

Reference: Structural_Solvency_and_Risk_Topology.md
"""

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
from datetime import datetime

from sims.engine import SimulationEngine
from sims.scenarios import SCENARIOS, get_scenario, describe_scenario, list_scenarios
from sims.analysis import (
    generate_full_analysis,
    print_analysis_summary,
    calculate_var,
    calculate_cvar,
    analyze_fpr,
    get_ftoken_usd_returns,
    get_terminal_returns,
)


def run_scenario(scenario_name: str, plot: bool = True, verbose: bool = True) -> dict:
    """
    Run simulation for a specific scenario.
    
    Args:
        scenario_name: Name of scenario from SCENARIOS
        plot: Whether to generate plots
        verbose: Whether to print progress
        
    Returns:
        Analysis results dictionary
    """
    if verbose:
        print(f"\n{'#'*60}")
        print(f"# Running Scenario: {scenario_name.upper()}")
        print(f"{'#'*60}")
        print(describe_scenario(scenario_name))
    
    config = get_scenario(scenario_name)
    engine = SimulationEngine(config)
    paths = engine.run()
    
    # Generate analysis
    analysis = generate_full_analysis(paths, scenario_name)
    
    if verbose:
        print_analysis_summary(analysis)
    
    if plot:
        plot_scenario_results(paths, analysis, scenario_name)
    
    return analysis


def plot_scenario_results(paths: list, analysis: dict, scenario_name: str):
    """Generate comprehensive plots for scenario results."""
    
    fig = plt.figure(figsize=(16, 12))
    fig.suptitle(f'fToken vs LST Simulation: {scenario_name.upper()}', fontsize=14, fontweight='bold')
    
    # Sample paths for path plots (don't plot all 1000)
    n_sample = min(50, len(paths))
    sample_indices = np.random.choice(len(paths), n_sample, replace=False)
    
    # 1. Price Paths (top left)
    ax1 = fig.add_subplot(2, 3, 1)
    for i in sample_indices[:20]:  # Show 20 paths
        df = paths[i]
        ax1.plot(df['underlying_price'] / df['underlying_price'].iloc[0], 
                alpha=0.3, color='gray', linewidth=0.5)
        ax1.plot(df['lst_price'] / df['lst_price'].iloc[0], 
                alpha=0.3, color='blue', linewidth=0.5)
        ax1.plot((df['ftoken_floor'] * df['underlying_price']) / 
                (df['ftoken_floor'].iloc[0] * df['underlying_price'].iloc[0]),
                alpha=0.3, color='green', linewidth=0.5)
    
    # Add legend with dummy lines
    ax1.plot([], [], color='gray', label='Underlying', alpha=0.7)
    ax1.plot([], [], color='blue', label='LST', alpha=0.7)
    ax1.plot([], [], color='green', label='fToken USD', alpha=0.7)
    ax1.axhline(y=1, color='black', linestyle='--', alpha=0.5)
    ax1.set_xlabel('Time Step')
    ax1.set_ylabel('Normalized Price')
    ax1.set_title('Sample Price Paths')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)
    
    # 2. FPR Paths (top middle)
    ax2 = fig.add_subplot(2, 3, 2)
    for i in sample_indices[:30]:
        df = paths[i]
        ax2.plot(df['ftoken_fpr'], alpha=0.2, color='purple', linewidth=0.5)
    
    ax2.axhline(y=1.0, color='red', linestyle='--', label='Insolvency (1.0)', alpha=0.8)
    ax2.axhline(y=1.05, color='orange', linestyle='--', label='Red Zone (1.05)', alpha=0.8)
    ax2.axhline(y=1.10, color='yellow', linestyle='--', label='Yellow Zone (1.10)', alpha=0.8)
    ax2.set_xlabel('Time Step')
    ax2.set_ylabel('FPR')
    ax2.set_title('Floor Protection Ratio Paths')
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)
    
    # 3. Floor Price Evolution (top right)
    ax3 = fig.add_subplot(2, 3, 3)
    for i in sample_indices[:30]:
        df = paths[i]
        ax3.plot(df['ftoken_floor'], alpha=0.3, color='green', linewidth=0.5)
    
    ax3.set_xlabel('Time Step')
    ax3.set_ylabel('Floor Price')
    ax3.set_title('Floor Price Evolution')
    ax3.grid(True, alpha=0.3)
    
    # 4. Return Distributions (bottom left)
    ax4 = fig.add_subplot(2, 3, 4)
    lst_returns = get_terminal_returns(paths, 'lst_price')
    ftoken_usd_returns = get_ftoken_usd_returns(paths)
    
    bins = np.linspace(
        min(lst_returns.min(), ftoken_usd_returns.min()),
        max(lst_returns.max(), ftoken_usd_returns.max()),
        50
    )
    
    ax4.hist(lst_returns, bins=bins, alpha=0.5, label='LST', color='blue', density=True)
    ax4.hist(ftoken_usd_returns, bins=bins, alpha=0.5, label='fToken USD', color='green', density=True)
    
    # Add VaR lines
    lst_var = calculate_var(lst_returns, 0.05)
    ft_var = calculate_var(ftoken_usd_returns, 0.05)
    ax4.axvline(lst_var, color='blue', linestyle='--', label=f'LST VaR: {lst_var:.1%}')
    ax4.axvline(ft_var, color='green', linestyle='--', label=f'fToken VaR: {ft_var:.1%}')
    
    ax4.set_xlabel('Return')
    ax4.set_ylabel('Density')
    ax4.set_title('Terminal Return Distributions')
    ax4.legend(loc='best')
    ax4.grid(True, alpha=0.3)
    
    # 5. Min FPR Distribution (bottom middle)
    ax5 = fig.add_subplot(2, 3, 5)
    min_fpr = [df['ftoken_fpr'].min() for df in paths]
    
    ax5.hist(min_fpr, bins=50, alpha=0.7, color='purple', edgecolor='black')
    ax5.axvline(1.0, color='red', linestyle='--', label='Insolvency', linewidth=2)
    ax5.axvline(1.05, color='orange', linestyle='--', label='Red Zone', linewidth=2)
    ax5.axvline(np.percentile(min_fpr, 5), color='black', linestyle=':',
               label=f'5th Percentile: {np.percentile(min_fpr, 5):.3f}', linewidth=2)
    
    ax5.set_xlabel('Minimum FPR')
    ax5.set_ylabel('Frequency')
    ax5.set_title('Distribution of Minimum FPR')
    ax5.legend(loc='best')
    ax5.grid(True, alpha=0.3)
    
    # 6. Bad Debt vs Final FPR (bottom right)
    ax6 = fig.add_subplot(2, 3, 6)
    bad_debt = [df['ftoken_bad_debt_cumulative'].iloc[-1] for df in paths]
    final_fpr = [df['ftoken_fpr'].iloc[-1] for df in paths]
    
    scatter = ax6.scatter(bad_debt, final_fpr, alpha=0.3, c='purple', s=10)
    ax6.axhline(1.0, color='red', linestyle='--', alpha=0.5)
    ax6.axhline(1.05, color='orange', linestyle='--', alpha=0.5)
    ax6.set_xlabel('Cumulative Bad Debt')
    ax6.set_ylabel('Final FPR')
    ax6.set_title('Bad Debt Impact on FPR')
    ax6.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Save figure
    output_path = f'{scenario_name}_results.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Saved plot to {output_path}")
    
    plt.close()


def run_all_scenarios(scenarios: list = None):
    """Run all scenarios and generate comparison report."""
    
    if scenarios is None:
        scenarios = ['crypto_winter', 'crab_market', 'super_cycle']
    
    results = {}
    
    for scenario in scenarios:
        results[scenario] = run_scenario(scenario, plot=True, verbose=True)
    
    # Generate comparison report
    print_comparison_report(results)
    
    return results


def print_comparison_report(results: dict):
    """Print a comparison table across scenarios."""
    
    print(f"\n{'='*80}")
    print("SCENARIO COMPARISON REPORT")
    print(f"{'='*80}")
    
    # Header
    headers = ['Metric'] + list(results.keys())
    header_fmt = '{:<30}' + '{:>15}' * (len(headers) - 1)
    print(header_fmt.format(*headers))
    print('-' * 80)
    
    # Metrics to compare
    metrics = [
        ('LST VaR (95%)', lambda r: f"{r['var_analysis']['lst']['var_5pct']:+.1%}"),
        ('fToken USD VaR (95%)', lambda r: f"{r['var_analysis']['ftoken_usd']['var_5pct']:+.1%}"),
        ('LST Mean Return', lambda r: f"{r['var_analysis']['lst']['mean']:+.1%}"),
        ('fToken USD Mean Return', lambda r: f"{r['var_analysis']['ftoken_usd']['mean']:+.1%}"),
        ('Prob Insolvency', lambda r: f"{r['fpr_analysis']['prob_ever_insolvent']:.1%}"),
        ('Prob Red Zone', lambda r: f"{r['fpr_analysis']['prob_ever_red_zone']:.1%}"),
        ('Min FPR (5th pctl)', lambda r: f"{r['fpr_analysis']['min_fpr_5th_percentile']:.3f}"),
        ('Final FPR Mean', lambda r: f"{r['fpr_analysis']['final_fpr_mean']:.3f}"),
        ('Prob Bad Debt', lambda r: f"{r['bad_debt_analysis']['probability_of_bad_debt']:.1%}"),
        ('Floor Growth Mean', lambda r: f"{r['floor_metrics']['mean_floor_growth']:+.1%}"),
        ('LRE Events Mean', lambda r: f"{r['lre_metrics']['mean_lre_events']:.1f}"),
        ('Depeg Events Mean', lambda r: f"{r['depeg_metrics']['mean_depeg_events']:.1f}"),
    ]
    
    row_fmt = '{:<30}' + '{:>15}' * len(results)
    for metric_name, metric_fn in metrics:
        values = [metric_fn(results[s]) for s in results.keys()]
        print(row_fmt.format(metric_name, *values))
    
    print(f"{'='*80}\n")


def main():
    """Main entry point."""
    
    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║      fToken/LST Monte Carlo Simulation Suite                     ║
    ║      Python twin of Floor_v1.sol                                 ║
    ╚══════════════════════════════════════════════════════════════════╝
    
    This simulation compares fToken (floor-backed tokens) against LST
    (Liquid Staking Tokens) under various market conditions.
    
    Key mechanics modeled:
    - Solvency invariant: L_f - D >= P_f * S_tradeable
    - FPR (Floor Protection Ratio) tracking
    - LRE (Liquidity Reallocation Elevation)
    - Bad debt from loan defaults
    - Tier merging with harmonic schedule
    - Stress-correlated LST depegs
    """)
    
    # Set random seed for reproducibility
    np.random.seed(42)
    
    # Run main scenarios
    results = run_all_scenarios(['crypto_winter', 'crab_market', 'super_cycle'])
    
    # Print key takeaways
    print("\n" + "="*80)
    print("KEY TAKEAWAYS")
    print("="*80)
    
    print("""
    1. CRYPTO WINTER:
       - fToken provides strong downside protection vs LST
       - Floor price is non-decreasing in reserve terms
       - USD VaR captures underlying market risk
       - FPR may approach red zone but invariant holds
    
    2. CRAB MARKET:
       - LST may modestly outperform due to staking yield
       - fToken provides strong collateral value
       - Floor elevation steady but slow
       - Excellent FPR maintenance
    
    3. SUPER CYCLE:
       - Both assets participate in upside
       - fToken builds substantial floor protection
       - LRE events accelerate floor elevation
       - FPR typically in green zone
    
    The key differentiator is the fToken's floor guarantee:
    - LST: Full exposure to underlying volatility + depeg risk
    - fToken: Non-decreasing floor in reserve terms + premium upside
    """)
    
    return results


if __name__ == '__main__':
    results = main()
