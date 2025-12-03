"""
Run High Leverage LTV Stress Tests

This script runs the three high-leverage scenarios with different LTV levels
to test system behavior under extreme credit stress.
"""

import numpy as np
from sims.engine import SimulationEngine
from sims.scenarios import get_scenario, describe_scenario
from sims.analysis import generate_full_analysis, print_analysis_summary

def run_ltv_scenarios():
    """Run all LTV stress test scenarios."""
    
    scenarios = ['leverage_ltv80', 'leverage_ltv90', 'leverage_ltv99']
    results = {}
    
    np.random.seed(42)
    
    for scenario_name in scenarios:
        print(f"\n{'#'*70}")
        print(f"# Running LTV Stress Test: {scenario_name.upper()}")
        print(f"{'#'*70}")
        print(describe_scenario(scenario_name))
        
        config = get_scenario(scenario_name)
        engine = SimulationEngine(config)
        paths = engine.run()
        
        # Generate analysis
        analysis = generate_full_analysis(paths, scenario_name)
        results[scenario_name] = analysis
        
        # Print summary
        print_analysis_summary(analysis)
        
        # Print LRE-specific metrics
        print("\n--- LRE Activity ---")
        print(f"Mean LRE Events: {analysis['lre_metrics']['mean_lre_events']:.1f}")
        print(f"Max LRE Events:  {analysis['lre_metrics']['max_lre_events']}")
        print(f"Paths with LRE:  {analysis['lre_metrics']['paths_with_lre']}/{analysis['n_paths']}")
    
    # Comparison table
    print(f"\n{'='*90}")
    print("LTV STRESS TEST COMPARISON")
    print(f"{'='*90}")
    
    headers = ['Metric'] + scenarios
    header_fmt = '{:<35}' + '{:>17}' * len(scenarios)
    print(header_fmt.format(*headers))
    print('-' * 90)
    
    metrics = [
        ('LTV Level', lambda r: f"{r['ftoken_usd']['var_5pct']:.0%}" if 'ltv80' in r.get('scenario', '') else f"{r['ftoken_usd']['var_5pct']:.0%}"),
        ('fToken USD VaR (95%)', lambda r: f"{r['var_analysis']['ftoken_usd']['var_5pct']:+.1%}"),
        ('fToken Mean Return', lambda r: f"{r['var_analysis']['ftoken_usd']['mean']:+.1%}"),
        ('Prob Insolvency', lambda r: f"{r['fpr_analysis']['prob_ever_insolvent']:.2%}"),
        ('Prob Red Zone', lambda r: f"{r['fpr_analysis']['prob_ever_red_zone']:.2%}"),
        ('Min FPR (5th pctl)', lambda r: f"{r['fpr_analysis']['min_fpr_5th_percentile']:.3f}"),
        ('Final FPR Mean', lambda r: f"{r['fpr_analysis']['final_fpr_mean']:.3f}"),
        ('Prob Bad Debt', lambda r: f"{r['bad_debt_analysis']['probability_of_bad_debt']:.1%}"),
        ('Mean Bad Debt', lambda r: f"{r['bad_debt_analysis']['mean_bad_debt']:,.0f}"),
        ('Floor Growth Mean', lambda r: f"{r['floor_metrics']['mean_floor_growth']:+.1%}"),
        ('LRE Events Mean', lambda r: f"{r['lre_metrics']['mean_lre_events']:.1f}"),
        ('LRE Events Max', lambda r: f"{r['lre_metrics']['max_lre_events']}"),
        ('Paths with LRE', lambda r: f"{r['lre_metrics']['paths_with_lre']}"),
    ]
    
    # Add LTV labels
    ltv_labels = {'leverage_ltv80': '80%', 'leverage_ltv90': '90%', 'leverage_ltv99': '99%'}
    row_fmt = '{:<35}' + '{:>17}' * len(scenarios)
    values = [ltv_labels[s] for s in scenarios]
    print(row_fmt.format('LTV Level', *values))
    
    for metric_name, metric_fn in metrics[1:]:  # Skip LTV Level since we printed it
        values = [metric_fn(results[s]) for s in scenarios]
        print(row_fmt.format(metric_name, *values))
    
    print(f"{'='*90}\n")
    
    # Summary insights
    print("\n### KEY INSIGHTS ###\n")
    
    for scenario_name in scenarios:
        r = results[scenario_name]
        ltv = ltv_labels[scenario_name]
        print(f"\n**{scenario_name.upper()} (LTV {ltv})**:")
        print(f"  - Insolvency Risk: {r['fpr_analysis']['prob_ever_insolvent']:.2%}")
        print(f"  - LRE Activation: {r['lre_metrics']['paths_with_lre']}/{r['n_paths']} paths")
        print(f"  - Mean LRE Events: {r['lre_metrics']['mean_lre_events']:.1f}")
        print(f"  - Floor Growth: {r['floor_metrics']['mean_floor_growth']:+.1%}")
        print(f"  - Bad Debt: {r['bad_debt_analysis']['mean_bad_debt']:,.0f} AVAX mean")
    
    return results

if __name__ == '__main__':
    results = run_ltv_scenarios()
