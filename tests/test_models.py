import unittest
import numpy as np
from sims.models import fToken, Underlying

class TestFToken(unittest.TestCase):
    def setUp(self):
        self.underlying = Underlying("TEST", 100, 0, 0)
        self.ftoken = fToken(
            "fTEST", 
            self.underlying, 
            initial_reserves=120, 
            initial_supply=100, 
            initial_floor=1.0,
            fee_rate_to_reserves=0.0,
            tier_schedule='naive',
            tier_capacity_base=10,
            tick_size=0.1
        )

    def test_initial_state(self):
        self.assertEqual(self.ftoken.floor_price, 1.0)
        self.assertEqual(self.ftoken.calculate_fpr(), 1.2) # 120 / (1.0 * 100) = 1.2
        self.assertEqual(self.ftoken.calculate_headroom(), 20.0) # 120 - 100 = 20

    def test_floor_raise(self):
        # Headroom is 20. Cost to raise by 0.1 is 0.1 * 100 = 10.
        # Should raise twice? 
        # 1st raise: P=1.1, Cost=10. New Liability = 1.1*100 = 110. Reserves=120. Headroom=10.
        # 2nd raise: P=1.2, Cost=10. New Liability = 1.2*100 = 120. Reserves=120. Headroom=0.
        
        # We simulate a step with 0 volume (no fees)
        self.ftoken.simulate_step(dt=0.01, trading_volume=0)
        
        self.assertAlmostEqual(self.ftoken.floor_price, 1.2)
        self.assertAlmostEqual(self.ftoken.calculate_headroom(), 0.0)
        self.assertAlmostEqual(self.ftoken.calculate_fpr(), 1.0)

    def test_tier_merge(self):
        # Setup specific case for merge
        # Reserves 200, Supply 100, Floor 1.0. Headroom 100.
        # Tick 0.1.
        # Next tier capacity 10.
        # We want to raise floor to 1.1. Cost 10.
        # Then check merge: P=1.1. New Supply = 100+10 = 110.
        # Required backing = 1.1 * 110 = 121.
        # Reserves = 200. 200 >= 121. Should merge.
        
        ft = fToken("fMERGE", self.underlying, 200, 100, 1.0, 0.0, tier_capacity_base=10, tick_size=0.1)
        
        ft.simulate_step(0.01, 0)
        
        # It should have raised floor multiple times because headroom is huge (100).
        # Let's trace:
        # P=1.0, H=100.
        # Raise -> P=1.1. H = 200 - 1.1*100 = 90.
        # Merge Check: 200 >= 1.1 * (100+10) = 121. Yes.
        # Merge! Supply -> 110.
        # H = 200 - 1.1*110 = 200 - 121 = 79.
        
        # Next loop:
        # Cost to raise = 0.1 * 110 = 11.
        # 79 >= 11. Raise -> P=1.2.
        # H = 200 - 1.2*110 = 200 - 132 = 68.
        # Merge Check (next tier also 10): 200 >= 1.2 * (110+10) = 1.2 * 120 = 144. Yes.
        # Merge! Supply -> 120.
        # ... and so on until headroom is exhausted.
        
        self.assertGreater(ft.floor_price, 1.0)
        self.assertGreater(ft.supply, 100)
        self.assertEqual(ft.calculate_fpr() >= 1.0, True)

if __name__ == '__main__':
    unittest.main()
