# CSP Solver Optimizations

This document explains all optimizations implemented in the solver to reduce the number of steps required to solve logic grid puzzles.

---

## Summary of Optimizations

| # | Optimization | Purpose | Impact |
|---|-------------|---------|--------|
| 1 | MRV Heuristic | Variable selection | Fail-first principle |
| 2 | Degree Heuristic | MRV tiebreaker | Better variable ordering |
| 3 | LCV Heuristic | Value ordering | Try least constraining values first |
| 4 | Domain Wipeout Detection | Improved LCV | Avoid immediate failures |
| 5 | Forward Checking | Propagation | Prune domains early |
| 6 | AC-3 Arc Consistency | Propagation | Stronger domain reduction |
| 7 | Optimized AC-3 Queue | Efficiency | Avoid duplicate arc processing |
| 8 | Conflict-Directed Backjumping | Smart backtracking | Skip irrelevant branches |
| 9 | Nogood Learning | Memory | Remember failed combinations |
| 10 | Naked/Hidden Pairs | Inference | Sudoku-style elimination |
| 11 | Watched Literals | Efficiency | Reduce constraint checks |
| 12 | Optimized Consistency Check | Efficiency | Only check relevant constraints |

---

## Detailed Explanations

### 1. MRV (Minimum Remaining Values) Heuristic

**What it does:** Selects the variable with the smallest domain (fewest possible values) to assign next.

**Why it reduces steps:** 
- "Fail-first" principle - if a variable has only 1 value, assign it immediately
- If a variable has 0 values, we detect failure without further exploration
- Variables with small domains cause failures sooner, pruning the search tree

**Example:**
```
If Name_Alice can be {1,2,3} and Name_Bob can be {2}, pick Bob first.
This immediately assigns Bob=2, then propagation reduces Alice's choices.
```

---

### 2. Degree Heuristic (MRV Tiebreaker)

**What it does:** When multiple variables have the same domain size, choose the one involved in the most constraints with unassigned variables.

**Why it reduces steps:**
- Assigning a highly constrained variable causes more propagation
- More propagation = more domain reductions = earlier detection of failures
- Breaks ties in MRV intelligently rather than arbitrarily

**Example:**
```
If Name_Alice and Name_Bob both have domain {1,2}:
- Alice has 3 constraints with unassigned variables
- Bob has 1 constraint with unassigned variables
→ Pick Alice (higher degree), causing more immediate propagation
```

---

### 3. LCV (Least Constraining Value) Heuristic

**What it does:** Orders domain values by how many options they eliminate from neighboring variables. Try values that eliminate fewer options first.

**Why it reduces steps:**
- If we're on the right path, we want to keep options open for other variables
- Values that severely restrict neighbors are more likely to cause backtracking
- "Succeed-first" for value ordering (opposite of fail-first for variable selection)

**Example:**
```
For Color_Red with domain {1,2,3}:
- Value 1 eliminates 5 values from neighbors
- Value 2 eliminates 2 values from neighbors
- Value 3 eliminates 8 values from neighbors
→ Try order: 2, 1, 3
```

---

### 4. Domain Wipeout Detection

**What it does:** Enhanced LCV that prioritizes avoiding values that would completely empty a neighbor's domain (causing immediate failure).

**Why it reduces steps:**
- A domain wipeout means guaranteed backtracking
- Better to avoid wipeouts than minimize general conflicts
- Scoring: `wipeouts * 1000 + conflicts` prioritizes no-wipeout values

**Example:**
```
Value 1: causes 1 wipeout, 3 conflicts → score 1003
Value 2: causes 0 wipeouts, 7 conflicts → score 7
→ Pick Value 2 (no wipeouts) even though it has more conflicts
```

---

### 5. Forward Checking

**What it does:** After assigning a variable, immediately remove inconsistent values from all connected unassigned variables.

**Why it reduces steps:**
- Detects failures before making more assignments
- Reduces domain sizes, helping MRV make better choices
- Catches "obvious" impossibilities immediately

**Example:**
```
After assigning Name_Alice = 1:
- AllDifferent constraint removes 1 from Name_Bob's domain
- AllDifferent constraint removes 1 from Name_Carol's domain
- "Same house" constraint with Color_Red forces Color_Red = 1
```

---

### 6. AC-3 Arc Consistency

**What it does:** Ensures every value in every domain has at least one consistent value in every connected variable. Iteratively removes unsupported values.

**Why it reduces steps:**
- Stronger propagation than forward checking
- Can detect failures that require looking 2+ steps ahead
- Often solves simple puzzles entirely through propagation (0 search steps!)

**Algorithm:**
```
1. Add all arcs (Xi, Xj) to queue
2. For each arc, check if Xi has values with no support in Xj
3. Remove unsupported values from Xi
4. If Xi changed, re-add all arcs (Xk, Xi) to queue
5. Repeat until queue is empty or a domain empties
```

---

### 7. Optimized AC-3 Queue

**What it does:** Uses a set alongside the queue to prevent adding duplicate arcs.

**Why it reduces steps (time):**
- Standard AC-3 can re-process the same arc many times
- Set membership check is O(1)
- Significantly faster on problems with many constraints

**Implementation:**
```python
queue_set = set()  # For O(1) membership check
queue = deque()    # For FIFO processing

# Only add if not already in queue
if arc not in queue_set:
    queue.append(arc)
    queue_set.add(arc)
```

---

### 8. Conflict-Directed Backjumping

**What it does:** Instead of backtracking to the previous variable (chronological), jumps directly to the variable that caused the conflict.

**Why it reduces steps:**
- Avoids exploring branches that will fail for the same reason
- Can skip many levels of the search tree
- Particularly effective when conflicts are caused by distant variables

**Example:**
```
Assignment order: A=1, B=2, C=3, D=4, E=5
Conflict detected: E conflicts with A (not D!)

Chronological: backtrack D, try D=5... still fails... backtrack C... etc.
Backjumping: jump directly back to A, try A=2
→ Saves exploring all combinations of B,C,D that would fail anyway
```

---

### 9. Nogood Learning

**What it does:** Records combinations of assignments that led to failure. Prunes future branches that would repeat these combinations.

**Why it reduces steps:**
- Never repeat the same mistake twice
- Can prune branches before any search
- Accumulated knowledge speeds up later parts of search

**Example:**
```
Learned: {(Color_Red=1), (Name_Alice=2)} → failure
Later, if we assign Color_Red=1 and are about to try Name_Alice=2:
→ Skip immediately, this combination is known to fail
```

---

### 10. Naked/Hidden Pairs Detection

**What it does:** Implements Sudoku-style inference rules. If N variables in the same attribute group can only have N values, those values are removed from other variables in the group.

**Why it reduces steps:**
- Derives implicit constraints from the problem structure
- Can reduce domains without search
- Particularly effective for AllDifferent constraints

**Example - Naked Pair:**
```
In the Name attribute (must all be different houses):
- Name_Alice: {1, 2}
- Name_Bob: {1, 2}
- Name_Carol: {1, 2, 3}

Alice and Bob form a "naked pair" - they must use values 1 and 2.
→ Remove 1 and 2 from Carol's domain: {3}
→ Carol must be in house 3!
```

**Example - Naked Triple:**
```
- Name_Alice: {1, 2}
- Name_Bob: {2, 3}
- Name_Carol: {1, 3}
- Name_Dave: {1, 2, 3, 4}

Alice, Bob, Carol form a naked triple using values {1, 2, 3}.
→ Remove 1, 2, 3 from Dave's domain: {4}
```

---

### 11. Watched Literals

**What it does:** For each constraint, only track 2 "support" values. Only re-check the constraint when both supports are removed.

**Why it reduces steps (time):**
- Most constraint checks are unnecessary (values still have support)
- Only triggers full check when absolutely needed
- Common in modern SAT/CSP solvers

**Implementation:**
```python
# For constraint "A != B":
# Watch A=1 (supported by B=2,3,4,5)
# Watch A=2 (supported by B=1,3,4,5)

# If we remove A=3: no re-check needed (watches still valid)
# If we remove A=1: find new watch or trigger full check
```

---

### 12. Optimized Consistency Check

**What it does:** Instead of checking all constraints, only check:
1. Unary constraints on the current variable
2. Binary constraints with already-assigned variables

**Why it reduces steps (time):**
- Old method: iterate through ALL constraints, check if fully assigned
- New method: directly access relevant constraints via index
- O(constraints) → O(neighbors)

**Before:**
```python
for constraint in self.constraints:  # Check all!
    if all(v in assignment for v in constraint.variables):
        # Check constraint
```

**After:**
```python
# Only check constraints involving var_name and assigned variables
for other_var, constraint in self.binary_constraints[var_name]:
    if other_var in assignment:
        # Check constraint
```

---

## Performance Comparison

### Test_100_Puzzles.csv (3x3 puzzles)

| Version | Avg Steps | Avg Time | Total Time |
|---------|-----------|----------|------------|
| Original | 8.24 | 0.36ms | 0.08s |
| Optimized | 8.20 | 0.30ms | 0.07s |

The 3x3 puzzles are simple enough that both versions perform similarly. The optimizations shine on larger/harder puzzles.

---

## When Each Optimization Helps Most

| Optimization | Best For |
|-------------|----------|
| MRV | All puzzles |
| Degree Heuristic | Puzzles with many constraints |
| LCV | Puzzles with multiple solutions or tight constraints |
| Forward Checking | All puzzles |
| AC-3 | Puzzles solvable by pure propagation |
| Backjumping | Deep search trees with distant conflicts |
| Nogood Learning | Similar subproblems, symmetric puzzles |
| Naked Pairs | Puzzles with AllDifferent constraints |
| Watched Literals | Puzzles with many constraints |

---

## Configuration

All optimizations can be enabled/disabled in `solver_optimized.py`:

```python
self.use_mrv = True
self.use_degree_heuristic = True
self.use_lcv = True
self.use_lcv_wipeout = True
self.use_forward_checking = True
self.use_arc_consistency = True
self.use_backjumping = True
self.use_nogood_learning = True
self.use_sac = False  # Can be too aggressive
self.use_naked_pairs = True
self.use_watched_literals = True
```

---

## Files

- `solver.py` - Original solver with basic optimizations
- `solver_optimized.py` - Fully optimized solver with all techniques
- `run.py` - Uses the optimized solver by default
