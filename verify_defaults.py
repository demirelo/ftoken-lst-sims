
import sys
import os

# Add project root to path
sys.path.append('/Users/oemer.demirel/ftoken-lst-sims')

from sims.models import fToken, Underlying
from sims.scenarios import BASE_CONFIG
from sims.engine import SimulationConfig, SimulationEngine

def verify_models():
    print("Verifying sims/models.py defaults...")
    # Initialize minimal required args to test defaults
    u = Underlying("Test", 100, 0, 0)
    ft = fToken("fTest", u, 10000, 10000, 1.0, 0.005, 0.005, 0.02)
    
    # Check new defaults
    assert ft.debt_cap_bps == 8000, f"Expected debt_cap_bps=8000, got {ft.debt_cap_bps}"
    assert ft.fee_to_floor_ratio == 0.80, f"Expected fee_to_floor_ratio=0.80, got {ft.fee_to_floor_ratio}"
    assert ft.fee_to_stakers_ratio == 0.15, f"Expected fee_to_stakers_ratio=0.15, got {ft.fee_to_stakers_ratio}"
    assert ft.lre_realloc_bps == 2500, f"Expected lre_realloc_bps=2500, got {ft.lre_realloc_bps}"
    assert ft.lre_threshold == 1.2, f"Expected lre_threshold=1.2, got {ft.lre_threshold}"
    print("models.py defaults ok")

def verify_scenarios():
    print("Verifying sims/scenarios.py defaults...")
    c = BASE_CONFIG
    assert c['n_paths'] == 100, f"Expected n_paths=100, got {c['n_paths']}"
    assert c['initial_reserves'] == 10000, f"Expected initial_reserves=10000, got {c['initial_reserves']}"
    assert c['initial_supply'] == 10000, f"Expected initial_supply=10000, got {c['initial_supply']}"
    assert c['fee_to_floor_ratio'] == 0.80, f"Expected fee_to_floor_ratio=0.80, got {c['fee_to_floor_ratio']}"
    assert c['fee_to_stakers_ratio'] == 0.15, f"Expected fee_to_stakers_ratio=0.15, got {c['fee_to_stakers_ratio']}"
    assert c['debt_cap_bps'] == 8000, f"Expected debt_cap_bps=8000, got {c['debt_cap_bps']}"
    assert c['lre_realloc_bps'] == 2500, f"Expected lre_realloc_bps=2500, got {c['lre_realloc_bps']}"
    assert c['lre_threshold'] == 1.2, f"Expected lre_threshold=1.2, got {c['lre_threshold']}"
    print("scenarios.py defaults ok")

def verify_engine():
    print("Verifying sims/engine.py defaults...")
    # Check dataclass
    sc = SimulationConfig()
    assert sc.n_paths == 100, f"Expected n_paths=100, got {sc.n_paths}"
    assert sc.initial_reserves == 10000, f"Expected initial_reserves=10000, got {sc.initial_reserves}"
    assert sc.initial_supply == 10000, f"Expected initial_supply=10000, got {sc.initial_supply}"
    assert sc.debt_cap_bps == 8000, f"Expected debt_cap_bps=8000, got {sc.debt_cap_bps}"
    assert sc.lre_realloc_bps == 2500, f"Expected lre_realloc_bps=2500, got {sc.lre_realloc_bps}"
    assert sc.lre_threshold == 1.2, f"Expected lre_threshold=1.2, got {sc.lre_threshold}"

    # Check Engine fallback logic (by passing empty dict and checking used values if possible, 
    # but Engine applies config in init, hard to inspect private local vars in __init__ without running it.
    # However we updated the .get() calls so inspection of code was the verification step there.
    # We can check if `_run_single_path` creates fToken with correct params if we mock or inspect it,
    # but for now verifying the Dataclass defaults is a strong signal.)
    print("engine.py defaults ok")

if __name__ == "__main__":
    verify_models()
    verify_scenarios()
    verify_engine()
