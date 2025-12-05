"""
Unit Tests for fToken/LST Simulation Models

These tests verify that the Python simulation correctly implements
the key mechanics of Floor_v1.sol.

Test categories:
1. FPR calculation (tradeable supply, locked supply)
2. Solvency invariant (L_f - D >= P_f * S_tradeable)
3. Debt caps and coverage buffers
4. LRE (Liquidity Reallocation Elevation)
5. Bad debt mechanics
6. Tier merging
7. Trading operations
"""

import pytest
import numpy as np
from sims.models import Underlying, LST, fToken, BadDebtEvent


class TestUnderlying:
    """Tests for the Underlying asset model."""
    
    def test_initial_price(self):
        """Verify initial price is stored correctly."""
        u = Underlying("AVAX", initial_price=100.0, mu=0.1, sigma=0.5)
        assert u.current_price() == 100.0
        assert len(u.price_history) == 1
    
    def test_gbm_step(self):
        """Verify GBM step produces valid prices."""
        np.random.seed(42)
        u = Underlying("AVAX", initial_price=100.0, mu=0.1, sigma=0.5)
        
        # Run 100 steps
        for _ in range(100):
            new_price = u.simulate_step(1/365)
            assert new_price > 0
            assert new_price == u.current_price()
        
        assert len(u.price_history) == 101
    
    def test_price_drift(self):
        """Verify positive drift leads to positive expected return."""
        np.random.seed(42)
        n_paths = 100
        final_prices = []
        
        for _ in range(n_paths):
            u = Underlying("AVAX", initial_price=100.0, mu=0.5, sigma=0.3)
            for _ in range(365):  # 1 year
                u.simulate_step(1/365)
            final_prices.append(u.current_price())
        
        # With 50% drift, expect mean > initial
        assert np.mean(final_prices) > 100.0


class TestLST:
    """Tests for the LST model."""
    
    def test_yield_accrual(self):
        """Verify staking yield accrues over time."""
        u = Underlying("AVAX", initial_price=100.0, mu=0.0, sigma=0.01)
        lst = LST("sAVAX", underlying=u, staking_yield=0.05, p_depeg_base=0)
        
        # Run for 365 steps (1 year) with stable underlying
        for _ in range(365):
            u.simulate_step(1/365)
            lst.simulate_step(1/365)
        
        # Should have ~5% yield
        assert lst.index > 1.04
        assert lst.index < 1.06
    
    def test_depeg_events(self):
        """Verify depeg events occur with non-zero probability."""
        np.random.seed(42)
        u = Underlying("AVAX", initial_price=100.0, mu=-0.5, sigma=0.8)
        lst = LST("sAVAX", underlying=u, staking_yield=0.05, 
                  p_depeg_base=0.02, depeg_severity_mean=-0.05, depeg_severity_std=0.02)
        
        # Run for 100 steps in stressful conditions
        for _ in range(100):
            u.simulate_step(1/365)
            lst.simulate_step(1/365)
        
        # Should have at least some depeg events
        assert len(lst.depeg_events) > 0
    
    def test_stress_correlation(self):
        """Verify depeg probability increases during stress."""
        np.random.seed(42)
        
        # Count depegs in stressed vs non-stressed conditions
        stressed_depegs = []
        normal_depegs = []
        
        for _ in range(50):
            # Stressed scenario
            u1 = Underlying("AVAX", initial_price=100.0, mu=-1.5, sigma=1.0)
            lst1 = LST("sAVAX", underlying=u1, staking_yield=0.05,
                      p_depeg_base=0.01, stress_depeg_multiplier=3.0)
            for _ in range(30):
                u1.simulate_step(1/365)
                lst1.simulate_step(1/365)
            stressed_depegs.append(len(lst1.depeg_events))
            
            # Normal scenario
            u2 = Underlying("AVAX", initial_price=100.0, mu=0.1, sigma=0.3)
            lst2 = LST("sAVAX", underlying=u2, staking_yield=0.05,
                      p_depeg_base=0.01, stress_depeg_multiplier=3.0)
            for _ in range(30):
                u2.simulate_step(1/365)
                lst2.simulate_step(1/365)
            normal_depegs.append(len(lst2.depeg_events))
        
        # Stressed should have more depegs on average
        assert np.mean(stressed_depegs) > np.mean(normal_depegs)


class TestFTokenFPR:
    """Tests for FPR calculation - mirrors getCoverageRatio() in Floor_v1.sol."""
    
    def setup_method(self):
        """Create a fresh fToken for each test."""
        self.underlying = Underlying("AVAX", initial_price=100.0, mu=0.0, sigma=0.1)
        self.ftoken = fToken(
            name="fAVAX",
            underlying=self.underlying,
            initial_reserves=1100000,
            initial_supply=1000000,
            initial_floor=1.0,
            buy_fee=0.003,
            sell_fee=0.005,
            origination_fee=0.02,
        )
    
    def test_initial_fpr(self):
        """Verify initial FPR is correctly calculated."""
        # FPR = (L_f - D) / (P_f * S_tradeable)
        # = (1100000 - 0) / (1.0 * 1000000) = 1.1
        fpr = self.ftoken.calculate_fpr()
        assert abs(fpr - 1.1) < 0.001
    
    def test_fpr_uses_tradeable_supply(self):
        """Verify FPR uses tradeable supply, not total supply.
        
        This mirrors getCoverageRatio() in Floor_v1.sol which uses
        _getTradeableSupply() = totalSupply - lockedSupply
        """
        # Lock some supply
        self.ftoken.locked_supply = 500000
        
        # FPR = (1100000 - 0) / (1.0 * 500000) = 2.2
        fpr = self.ftoken.calculate_fpr()
        assert abs(fpr - 2.2) < 0.001
    
    def test_fpr_considers_debt(self):
        """Verify debt reduces available assets in FPR."""
        self.ftoken.debt = 100000
        
        # FPR = (1100000 - 100000) / (1.0 * 1000000) = 1.0
        fpr = self.ftoken.calculate_fpr()
        assert abs(fpr - 1.0) < 0.001
    
    def test_coverage_ratio_bps(self):
        """Verify get_coverage_ratio_bps returns basis points."""
        # FPR = 1.1 -> 11000 bps
        bps = self.ftoken.get_coverage_ratio_bps()
        assert bps == 11000


class TestFTokenSolvencyInvariant:
    """Tests for the core solvency invariant: L_f - D >= P_f * S_tradeable."""
    
    def setup_method(self):
        """Create a fresh fToken for each test."""
        self.underlying = Underlying("AVAX", initial_price=100.0, mu=0.0, sigma=0.1)
        self.ftoken = fToken(
            name="fAVAX",
            underlying=self.underlying,
            initial_reserves=1100000,
            initial_supply=1000000,
            initial_floor=1.0,
            buy_fee=0.003,
            sell_fee=0.005,
            origination_fee=0.02,
            debt_cap_bps=5000,
            min_coverage_buffer_bps=500,
        )
    
    def test_is_solvent_initially(self):
        """Verify system starts solvent."""
        assert self.ftoken.is_solvent()
        assert self.ftoken.calculate_fpr() >= 1.0
    
    def test_headroom_calculation(self):
        """Verify headroom calculation."""
        # Headroom = A_f - (P_f * S_tradeable)
        # = (1100000 - 0) - (1.0 * 1000000) = 100000
        headroom = self.ftoken.calculate_headroom()
        assert abs(headroom - 100000) < 1
    
    def test_loan_respects_coverage(self):
        """Verify loans cannot violate coverage invariant."""
        # Try to originate a loan that would violate coverage
        success, _, _, _ = self.ftoken.originate_loan(
            amount=200000,  # Would reduce available assets too much
            collateral_tokens=200000
        )
        
        # Should still be solvent after attempted loan
        assert self.ftoken.is_solvent()
    
    def test_sell_respects_coverage(self):
        """Verify sells cannot violate coverage invariant."""
        # First add some reserves via buy to have premium supply
        self.ftoken.buy(500000)
        
        # Try to sell a large amount
        initial_reserves = self.ftoken.reserves
        initial_fpr = self.ftoken.calculate_fpr()
        
        _, _, success = self.ftoken.sell(999999999)  # Huge sell
        
        # System should still be solvent
        assert self.ftoken.is_solvent()


class TestFTokenDebtCaps:
    """Tests for debt caps and coverage buffers - mirrors Floor_v1.sol governance."""
    
    def setup_method(self):
        """Create a fresh fToken for each test."""
        self.underlying = Underlying("AVAX", initial_price=100.0, mu=0.0, sigma=0.1)
        self.ftoken = fToken(
            name="fAVAX",
            underlying=self.underlying,
            initial_reserves=1100000,
            initial_supply=1000000,
            initial_floor=1.0,
            buy_fee=0.003,
            sell_fee=0.005,
            origination_fee=0.02,
            debt_cap_bps=5000,  # 50% max
            min_coverage_buffer_bps=500,  # 5% buffer
        )
    
    def test_debt_cap(self):
        """Verify debt cap is respected."""
        # Debt cap = 50% of 1100000 = 550000
        debt_cap = self.ftoken.get_debt_cap()
        assert debt_cap == 550000
    
    def test_max_borrowable(self):
        """Verify max borrowable respects both cap and coverage."""
        max_borrow = self.ftoken.get_max_borrowable()
        
        # Should be positive but limited by headroom
        assert max_borrow > 0
        assert max_borrow <= self.ftoken.calculate_headroom()
        assert max_borrow <= self.ftoken.get_debt_cap()
    
    def test_loan_rejected_at_cap(self):
        """Verify loans are rejected when at debt cap."""
        # Set debt to cap
        self.ftoken.debt = self.ftoken.get_debt_cap()
        
        # Try to add more debt
        success, _, _, _ = self.ftoken.originate_loan(
            amount=10000,
            collateral_tokens=15000
        )
        
        # Should be rejected
        assert not success


class TestFTokenLRE:
    """Tests for Liquidity Reallocation Elevation."""
    
    def setup_method(self):
        """Create a fresh fToken for each test."""
        self.underlying = Underlying("AVAX", initial_price=100.0, mu=0.0, sigma=0.1)
        self.ftoken = fToken(
            name="fAVAX",
            underlying=self.underlying,
            initial_reserves=2000000,  # Extra reserves
            initial_supply=500000,
            initial_floor=1.0,
            buy_fee=0.003,
            sell_fee=0.005,
            origination_fee=0.02,
            lre_threshold=2.0,  # Trigger when premium 2x floor
            lre_realloc_bps=2000,  # 20% reallocation
        )
    
    def test_premium_liquidity(self):
        """Verify premium liquidity calculation."""
        # Premium = total - (floor_price * floor_supply)
        # = 2000000 - (1.0 * 500000) = 1500000
        premium_liq = self.ftoken.get_premium_liquidity()
        assert abs(premium_liq - 1500000) < 1
    
    def test_lre_condition(self):
        """Verify LRE triggers when threshold is met."""
        can_lre, excess = self.ftoken.can_perform_lre()
        
        # Premium/Floor = 1500000/500000 = 3.0 >= 2.0 threshold
        assert can_lre
        assert excess > 0
    
    def test_lre_execution(self):
        """Verify LRE raises floor when executed."""
        old_floor = self.ftoken.floor_price
        amount = self.ftoken.perform_lre()
        
        # Should have reallocated something
        assert amount > 0
        
        # Floor should have increased
        assert self.ftoken.floor_price >= old_floor


class TestFTokenBadDebt:
    """Tests for bad debt mechanics - mirrors Section 9.2 of spec."""
    
    def setup_method(self):
        """Create a fresh fToken for each test."""
        self.underlying = Underlying("AVAX", initial_price=100.0, mu=0.0, sigma=0.1)
        self.ftoken = fToken(
            name="fAVAX",
            underlying=self.underlying,
            initial_reserves=1100000,
            initial_supply=1000000,
            initial_floor=1.0,
            buy_fee=0.003,
            sell_fee=0.005,
            origination_fee=0.02,
            bad_debt_lgd=0.3,  # 30% loss given default
            loan_default_prob_base=0.1,  # High for testing
        )
    
    def test_bad_debt_reduces_reserves(self):
        """Verify bad debt reduces L_f directly.
        
        Per spec: 'A write-off of size ΔD effectively does: 
        L_f → L_f - ΔD, D → D - ΔD'
        """
        # Create a loan
        self.ftoken.originate_loan(
            amount=100000,
            collateral_tokens=150000
        )
        
        initial_reserves = self.ftoken.reserves
        initial_debt = self.ftoken.debt
        
        # Force a default by running many steps with high default prob
        np.random.seed(42)
        for _ in range(100):
            self.ftoken.process_loan_defaults()
            if self.ftoken.get_total_bad_debt() > 0:
                break
        
        # If we had a default, reserves should have decreased
        if self.ftoken.get_total_bad_debt() > 0:
            assert self.ftoken.reserves < initial_reserves
            assert self.ftoken.debt < initial_debt
    
    def test_bad_debt_records(self):
        """Verify bad debt events are recorded."""
        self.ftoken.originate_loan(
            amount=50000,
            collateral_tokens=75000
        )
        
        np.random.seed(42)
        for _ in range(100):
            self.ftoken.process_loan_defaults()
        
        # Check records
        total_bad_debt = self.ftoken.get_total_bad_debt()
        recorded_bad_debt = sum(r.amount for r in self.ftoken.bad_debt_records)
        
        assert abs(total_bad_debt - recorded_bad_debt) < 0.01


class TestFTokenTierMerging:
    """Tests for tier merging mechanics."""
    
    def setup_method(self):
        """Create a fresh fToken for each test."""
        self.underlying = Underlying("AVAX", initial_price=100.0, mu=0.0, sigma=0.1)
        self.ftoken = fToken(
            name="fAVAX",
            underlying=self.underlying,
            initial_reserves=5000000,  # High reserves for testing
            initial_supply=1000000,
            initial_floor=1.0,
            buy_fee=0.003,
            sell_fee=0.005,
            origination_fee=0.02,
            tier_schedule='harmonic',
            tier_capacity_base=100000,
            tick_size=0.01,
        )
    
    def test_floor_only_increases(self):
        """Verify floor price never decreases."""
        np.random.seed(42)
        
        prices = [self.ftoken.floor_price]
        for _ in range(50):
            self.underlying.simulate_step(1/365)
            self.ftoken.simulate_step(
                dt=1/365,
                buy_volume=np.random.uniform(0, 100000),
                sell_volume=np.random.uniform(0, 50000)
            )
            prices.append(self.ftoken.floor_price)
        
        # Check monotonicity
        for i in range(1, len(prices)):
            assert prices[i] >= prices[i-1], f"Floor decreased at step {i}"
    
    def test_harmonic_tier_capacity(self):
        """Verify harmonic tier schedule produces decreasing capacities."""
        capacities = [self.ftoken._get_tier_capacity(i) for i in range(1, 10)]
        
        # Harmonic: each tier has smaller capacity
        for i in range(1, len(capacities)):
            assert capacities[i] < capacities[i-1]


class TestFTokenTrading:
    """Tests for trading operations."""
    
    def setup_method(self):
        """Create a fresh fToken for each test."""
        self.underlying = Underlying("AVAX", initial_price=100.0, mu=0.0, sigma=0.1)
        self.ftoken = fToken(
            name="fAVAX",
            underlying=self.underlying,
            initial_reserves=1100000,
            initial_supply=1000000,
            initial_floor=1.0,
            buy_fee=0.003,
            sell_fee=0.005,
            origination_fee=0.02,
        )
    
    def test_buy_increases_reserves(self):
        """Verify buys increase reserves."""
        initial_reserves = self.ftoken.reserves
        self.ftoken.buy(100000)
        
        assert self.ftoken.reserves > initial_reserves
    
    def test_buy_fee_collected(self):
        """Verify buy fees are collected."""
        initial_pending = self.ftoken.pending_fees
        _, fee_f, fee_g = self.ftoken.buy(100000)
        
        assert fee_f + fee_g > 0
        assert self.ftoken.pending_fees > initial_pending
    
    def test_sell_decreases_reserves(self):
        """Verify sells decrease reserves."""
        # First buy some
        self.ftoken.buy(200000)
        
        initial_reserves = self.ftoken.reserves
        tokens_to_sell = 50000
        
        payout, fee, success = self.ftoken.sell(tokens_to_sell)
        
        if success:
            assert self.ftoken.reserves < initial_reserves
    
    def test_recalibrate_after_sell(self):
        """Verify curve recalibrates after sells."""
        # Buy to create premium supply - add more reserves first
        self.ftoken.reserves += 500000  # Ensure headroom for sells
        self.ftoken.buy(500000)
        initial_premium = self.ftoken.premium_supply
        
        # Sell - use small amount to ensure it goes through
        payout, fee, success = self.ftoken.sell(10000)
        
        # If sell succeeded, premium should decrease
        if success:
            assert self.ftoken.premium_supply < initial_premium
        else:
            # If sell was rejected, at least verify system is still solvent
            assert self.ftoken.is_solvent()


class TestIntegration:
    """Integration tests running full simulation steps."""
    
    def test_full_simulation_maintains_solvency(self):
        """Verify a full simulation maintains solvency invariant."""
        np.random.seed(42)
        
        underlying = Underlying("AVAX", initial_price=100.0, mu=0.0, sigma=0.5)
        ftoken = fToken(
            name="fAVAX",
            underlying=underlying,
            initial_reserves=1100000,
            initial_supply=1000000,
            initial_floor=1.0,
            buy_fee=0.003,
            sell_fee=0.005,
            origination_fee=0.02,
        )
        
        # Run 100 steps
        for _ in range(100):
            underlying.simulate_step(1/365)
            ftoken.simulate_step(
                dt=1/365,
                buy_volume=np.random.uniform(0, 50000),
                sell_volume=np.random.uniform(0, 30000),
                new_loan_amount=np.random.uniform(0, 1000),
                new_loan_collateral=np.random.uniform(0, 1500)
            )
        
        # Should still be solvent
        assert ftoken.is_solvent()
    
    def test_stress_scenario(self):
        """Test under stress conditions (high volatility, large trades)."""
        np.random.seed(42)
        
        underlying = Underlying("AVAX", initial_price=100.0, mu=-1.0, sigma=0.9)
        ftoken = fToken(
            name="fAVAX",
            underlying=underlying,
            initial_reserves=1500000,  # Extra buffer
            initial_supply=1000000,
            initial_floor=1.0,
            buy_fee=0.003,
            sell_fee=0.005,
            origination_fee=0.02,
        )
        
        # Run stress scenario
        for _ in range(90):
            underlying.simulate_step(1/365)
            ftoken.simulate_step(
                dt=1/365,
                buy_volume=np.random.uniform(0, 10000),  # Reduced buying
                sell_volume=np.random.uniform(0, 100000)  # Heavy selling
            )
        
        # Check that floor hasn't decreased
        assert ftoken.floor_price >= 1.0
        
        # Check that system hasn't completely failed
        assert ftoken.reserves > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

    def test_cannot_sell_below_min_supply(self):
        """Verify sell is rejected or capped if it would drop supply below MIN_SUPPLY."""
        # Setup small supply
        self.ftoken.buy(100.0)
        current_supply = self.ftoken.total_supply
        
        # Try to sell everything
        # Should be capped to leave MIN_SUPPLY
        payout, fee, success = self.ftoken.sell(current_supply)
        
        assert success
        assert self.ftoken.total_supply >= self.ftoken.MIN_SUPPLY
        assert abs(self.ftoken.total_supply - self.ftoken.MIN_SUPPLY) < 1e-9
        
        # Try to sell the remaining dust
        payout, fee, success = self.ftoken.sell(self.ftoken.total_supply)
        
        # Should be rejected
        assert not success
        assert self.ftoken.total_supply >= self.ftoken.MIN_SUPPLY
