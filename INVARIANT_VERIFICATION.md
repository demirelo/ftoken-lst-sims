# Smart Contract Invariants vs Simulation Implementation

## Summary

This document compares the invariants enforced in the `floors-sc` smart contracts with those implemented in the Monte Carlo simulation.

## Core Solvency Invariant

### ✅ IMPLEMENTED: `L_f - D >= P_f * S_0`

**Smart Contract**: Checked in `sellTo()` and `increaseDebt()` via `_calculateAvailableFloorAssets()` and `_requireCoverageInvariant()`

**Simulation**: 
- Line 111-116: `calculate_fpr()` computes `(reserves - debt) / (floor_price * total_supply)`
- Line 189: Sell solvency check enforces `new_reserves - debt >= new_liability`
- Line 213: Loan solvency check enforces `current_headroom + net_headroom_change >= 0`

**Status**: ✅ Correctly implemented

---

## Trading Invariants

### ✅ IMPLEMENTED: Sell Solvency Check

**Smart Contract** (`Floor_v1.sol:sellTo`):
```solidity
_requireCoverageInvariant(
    _calculateAvailableFloorAssets() - totalCollateralTokenMovedOut,
    tradeableSupply - amount_
);
```

**Simulation** (Line 179-202):
```python
new_reserves = self.reserves - net_payout
new_supply = self.total_supply - tokens_to_burn
new_liability = self.floor_price * new_supply

if new_reserves - self.debt >= new_liability:
    # Execute sell
else:
    # REJECT SELL (Contract Reverts)
    pass
```

**Status**: ✅ Correctly implemented

### ✅ IMPLEMENTED: Buy Fee Handling

**Smart Contract** (`BC_Discrete_Redeeming_VirtualSupply_v1.sol:buyFor`):
- Fees are deducted from collateral before adding to virtual supply

**Simulation** (Line 145-158):
```python
fee = buy_volume * self.buy_fee
net_investment = buy_volume - fee
self.reserves += net_investment
self.pending_fees += fee
```

**Status**: ✅ Correctly implemented

---

## Credit/Lending Invariants

### ✅ IMPLEMENTED: Loan Headroom Check

**Smart Contract** (`Floor_v1.sol:increaseDebt`):
```solidity
uint availableFloorAssets = _calculateAvailableFloorAssets();
uint requiredCoverageWithBuffer = /* P_f * S_tradeable + buffer */;
require(availableFloorAssets - amount_ >= requiredCoverageWithBuffer);
```

**Simulation** (Line 204-217):
```python
net_headroom_change = -new_loan_amount
current_headroom = self.calculate_headroom()

if current_headroom + net_headroom_change >= 0:
    self.debt += new_loan_amount
    self.pending_fees += loan_fee
```

**Status**: ✅ Correctly implemented

### ⚠️ MISSING: Debt Cap (`_debtCapBps`)

**Smart Contract** (`Floor_v1.sol:increaseDebt`):
```solidity
if (_debtCapBps != 0) {
    require(newTotalDebt <= /* debt cap calculation */);
}
```

**Simulation**: No debt cap enforcement

**Impact**: Low - Headroom check provides similar protection, but explicit cap adds governance control

---

## Fee Elevation Invariants

### ✅ IMPLEMENTED: Batched Fee Injection

**Smart Contract** (`FloorElevationManager_v1.sol:elevateFloor`):
- Fees accumulate in `_pendingElevation`
- Only injected when `>= _elevationThreshold` and cooldown passes

**Simulation** (Line 220-222):
```python
if self.pending_fees >= self.elevation_threshold:
    self.reserves += self.pending_fees
    self.pending_fees = 0.0
```

**Status**: ✅ Correctly implemented

### ⚠️ MISSING: Cooldown Period

**Smart Contract** (`FloorElevationManager_v1.sol`):
```solidity
require(
    block.timestamp >= _lastElevationTimeStamp + _cooldownPeriod,
    "Cooldown period not passed"
);
```

**Simulation**: No cooldown mechanism

**Impact**: Low - Time-based logic less critical in discrete Monte Carlo steps

---

## Buffer and Safety Margins

### ⚠️ MISSING: Minimum Coverage Buffer (`_minCoverageBufferBps`)

**Smart Contract** (`Floor_v1.sol:increaseDebt`):
```solidity
uint minCoverageBuffer = _minCoverageBufferBps != 0
    ? floorPrice.mulDivDown(tradeableSupply, MAX_BPS).mulDivDown(_minCoverageBufferBps, MAX_BPS)
    : 0;
uint requiredCoverageWithBuffer = requiredCoverage + minCoverageBuffer;
```

**Simulation**: No explicit buffer requirement beyond `H >= 0`

**Impact**: Medium - Buffer provides additional safety margin for governance

**Recommendation**: Add configurable `min_coverage_buffer_bps` parameter

---

## Tier Merge Logic

### ✅ IMPLEMENTED: Harmonic Tier Schedule

**Smart Contract**: Uses discrete segment structure with `raiseFloor()`

**Simulation** (Line 122-134):
```python
def get_next_tier_capacity(self):
    if self.tier_schedule == 'harmonic':
        return self.tier_capacity_base / (self.merges_count + 1)
```

**Status**: ✅ Correctly implements O(m log m) scaling from Appendix B

### ✅ IMPLEMENTED: Safe Merge Check

**Simulation** (Line 271-272):
```python
required_backing = self.floor_price * (self.floor_supply + next_capacity)
if (self.reserves - self.debt) >= required_backing:
    # Merge
```

**Status**: ✅ Correctly implements `L_f - D >= P_next * (S_0 + M_next)`

---

## Missing Features from Paper (Not in Smart Contracts)

### ❌ NOT IMPLEMENTED: Algorithmic Borrow Rates

**Paper** (Section 10.1):
```
r_borrow(FPR) = r_min + α * max(0, FPR_target - FPR)
```

**Status**: Not implemented (static origination fee only)

**Impact**: Medium - Dynamic rates would improve governance control

### ❌ NOT IMPLEMENTED: Explicit Headroom Budgeting

**Paper** (Section 10.2):
```
H = H_f + H_c  // Floor budget + Credit budget
```

**Status**: Not implemented (implicit competition only)

**Impact**: Low - Current greedy floor-raising approximates one policy

### ❌ NOT IMPLEMENTED: Fee Routing Parameters

**Paper** (Section 10.3):
```
α_f + α_c + α_b = 1  // Floor, Stakeholders, Buybacks
```

**Status**: All fees currently go to floor (α_f = 1.0)

**Impact**: Low for risk simulation - simplification is conservative

---

## Recommendations

### High Priority
1. ✅ **All critical solvency invariants are implemented**
2. ⚠️ **Add `min_coverage_buffer_bps`** - Simple addition for realism

### Medium Priority
3. ⚠️ **Add debt cap (`debt_cap_bps`)** - Governance control
4. ❌ **Implement algorithmic borrow rates** - Per paper Section 10.1
5. ❌ **Add fee routing split (`alpha_f`, `alpha_c`)** - Per paper Section 10.3

### Low Priority
6. ⚠️ **Add cooldown period** - Less critical for Monte Carlo
7. ❌ **Explicit headroom budgeting** - Mostly policy, current greedy OK

---

## Conclusion

The simulation **correctly implements all critical solvency invariants** from the smart contracts:
- Core invariant `L_f - D >= P_f * S_0` ✅
- Sell solvency check ✅
- Loan headroom check ✅
- Batched fee injection ✅
- Harmonic tier scaling ✅

**Missing features** are mostly governance/policy mechanisms from the research paper that extend beyond core solvency. The simulation is suitable for risk analysis as-is, with optional enhancements for debt caps and coverage buffers to match full production behavior.
