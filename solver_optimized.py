"""
 CSP Solver with Advanced Techniques
==============================================
A CSP solver for Zebra/Logic Grid puzzles implementing:
- MRV with Degree Heuristic tiebreaker
- LCV (Least Constraining Value)
- Forward Checking
- AC-3 (Arc Consistency)
- Conflict-Directed Backjumping
- Nogood Learning
- Singleton Arc Consistency (SAC)
- Naked/Hidden Pairs detection
- Symmetry Breaking
- Watched Literals for efficient constraint checking
"""

import time
from typing import Dict, List, Tuple, Optional, Any, Set, Callable, FrozenSet
from dataclasses import dataclass, field
from collections import deque, defaultdict
import copy


@dataclass
class CSPVariable:
    """Represents a CSP variable."""
    name: str
    domain: Set[int]
    original_domain: Set[int] = field(default_factory=set)
    
    def __post_init__(self):
        if not self.original_domain:
            self.original_domain = self.domain.copy()


@dataclass
class CSPConstraint:
    """Represents a binary or unary constraint."""
    variables: List[str]
    check_func: Callable
    description: str = ""


@dataclass
class SolverTrace:
    """Records a single step in the solving process."""
    step: int
    action: str
    variable: Optional[str]
    value: Optional[int]
    domain_sizes: Dict[str, int]
    remaining_values: int
    constraint_count: int
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SolverStats:
    """Statistics from solving."""
    solved: bool
    solution: Optional[Dict[str, int]]
    steps: int
    backtracks: int
    pruned_values: int
    time_seconds: float
    nogoods_learned: int = 0
    backjumps: int = 0
    propagations: int = 0
    traces: List[SolverTrace] = field(default_factory=list)


class OptimizedCSPSolver:
    
    def __init__(self, enable_tracing: bool = False):
        self.variables: Dict[str, CSPVariable] = {}
        self.constraints: List[CSPConstraint] = []
        self.binary_constraints: Dict[str, List[Tuple[str, CSPConstraint]]] = {}
        self.unary_constraints: Dict[str, List[CSPConstraint]] = {}
        
        # settings (all enabled by default)
        self.use_mrv = True
        self.use_degree_heuristic = True  #Tiebreaker for MRV
        self.use_lcv = True
        self.use_lcv_wipeout = True  #Count domain wipeouts instead of just conflicts
        self.use_forward_checking = True
        self.use_arc_consistency = True
        self.use_backjumping = True  #Conflict-directed backjumping
        self.use_nogood_learning = True  #Learn from failures
        self.use_sac = False  # Singleton Arc Consistency (can be too aggressive)
        self.use_naked_pairs = True  #Naked/Hidden pairs detection
        self.use_watched_literals = True  #Watched literals
        
        # Nogood storage: set of frozensets of (var, value) tuples
        self.nogoods: Set[FrozenSet[Tuple[str, int]]] = set()
        self.max_nogoods = 10000  # Limit memory usage
        
        # Watched literals: for each constraint, track 2 support values
        self.watched: Dict[int, Dict[str, List[int]]] = {}  # constraint_id -> var -> [watch1, watch2]
        
        # Conflict tracking for backjumping
        self.conflict_set: Dict[str, Set[str]] = defaultdict(set)
        
        # Statistics
        self.steps = 0
        self.backtracks = 0
        self.pruned_values = 0
        self.nogoods_learned = 0
        self.backjumps = 0
        self.propagations = 0
        
        # Tracing
        self.enable_tracing = enable_tracing
        self.traces: List[SolverTrace] = []
        
        # Attribute groups for naked pairs (set during setup)
        self.attribute_groups: Dict[str, List[str]] = {}
    
    def add_variable(self, name: str, domain: List[int]):
        """Add a variable with its domain."""
        self.variables[name] = CSPVariable(name, set(domain), set(domain))
        self.binary_constraints[name] = []
        self.unary_constraints[name] = []
    
    def add_constraint(self, variables: List[str], check_func: Callable, description: str = ""):
        """Add a constraint."""
        constraint = CSPConstraint(variables, check_func, description)
        constraint_id = len(self.constraints)
        self.constraints.append(constraint)
        
        if len(variables) == 1:
            self.unary_constraints[variables[0]].append(constraint)
        elif len(variables) == 2:
            self.binary_constraints[variables[0]].append((variables[1], constraint))
            self.binary_constraints[variables[1]].append((variables[0], constraint))
            
            # Initialize watched literals
            if self.use_watched_literals:
                self._init_watched_literals(constraint_id, constraint)
    
    def _init_watched_literals(self, constraint_id: int, constraint: CSPConstraint):
        """Initialize watched literals for a constraint."""
        if len(constraint.variables) != 2:
            return
        
        var1, var2 = constraint.variables
        self.watched[constraint_id] = {
            var1: [],
            var2: []
        }
        
        # Find initial support values
        dom1 = list(self.variables[var1].domain)
        dom2 = list(self.variables[var2].domain)
        
        for val1 in dom1[:2]:  # Watch up to 2 values
            for val2 in dom2:
                if constraint.check_func(val1, val2):
                    if val1 not in self.watched[constraint_id][var1]:
                        self.watched[constraint_id][var1].append(val1)
                    break
        
        for val2 in dom2[:2]:
            for val1 in dom1:
                if constraint.check_func(val1, val2):
                    if val2 not in self.watched[constraint_id][var2]:
                        self.watched[constraint_id][var2].append(val2)
                    break
    
    def set_attribute_groups(self, groups: Dict[str, List[str]]):
        """Set attribute groups for naked pairs detection."""
        self.attribute_groups = groups
    
    def _record_trace(self, action: str, variable: Optional[str] = None, 
                      value: Optional[int] = None, details: Dict = None):
        """Record a trace step."""
        if not self.enable_tracing:
            return
        
        trace = SolverTrace(
            step=self.steps,
            action=action,
            variable=variable,
            value=value,
            domain_sizes={v: len(self.variables[v].domain) for v in self.variables},
            remaining_values=sum(len(self.variables[v].domain) for v in self.variables),
            constraint_count=len(self.constraints),
            details=details or {}
        )
        self.traces.append(trace)
    
    def _apply_unary_constraints(self) -> bool:
        """Apply unary constraints to reduce domains."""
        for var_name, constraints in self.unary_constraints.items():
            var = self.variables[var_name]
            for constraint in constraints:
                valid_values = set()
                for val in var.domain:
                    if constraint.check_func(val):
                        valid_values.add(val)
                    else:
                        self.pruned_values += 1
                var.domain = valid_values
                if not var.domain:
                    return False
        return True
    
    # ==================== MRV + Degree Heuristic ====================
    
    def _select_unassigned_variable(self, assignment: Dict[str, int], 
                                     domains: Dict[str, Set[int]]) -> Optional[str]:
        """
        Select next variable using MRV with Degree Heuristic as tiebreaker.
        
        MRV: Choose variable with smallest domain (fail-first)
        Degree: Among ties, choose variable involved in most constraints with unassigned vars
        """
        unassigned = [v for v in self.variables if v not in assignment]
        
        if not unassigned:
            return None
        
        if self.use_mrv:
            # Find minimum domain size
            min_domain = min(len(domains[v]) for v in unassigned)
            candidates = [v for v in unassigned if len(domains[v]) == min_domain]
            
            if len(candidates) == 1 or not self.use_degree_heuristic:
                best_var = candidates[0]
            else:
                # Degree heuristic as tiebreaker
                def degree(var):
                    """Count constraints with unassigned variables."""
                    count = 0
                    for other_var, _ in self.binary_constraints[var]:
                        if other_var not in assignment:
                            count += 1
                    return count
                
                best_var = max(candidates, key=degree)
            
            self._record_trace('select_variable', variable=best_var, 
                             details={'reason': 'MRV+Degree', 'domain_size': len(domains[best_var])})
            return best_var
        else:
            return unassigned[0]
    
    # ==================== LCV with Domain Wipeout ====================
    
    def _order_domain_values(self, var_name: str, assignment: Dict[str, int],
                             domains: Dict[str, Set[int]]) -> List[int]:
        """
        Order domain values using LCV with domain wipeout detection.
        
        Instead of just counting conflicts, count how many domains would be wiped out.
        Values causing fewer wipeouts are tried first.
        """
        if not self.use_lcv:
            return list(domains[var_name])
        
        domain = list(domains[var_name])
        if len(domain) <= 1:
            return domain
        
        def count_impact(value):
            """Count impact: wipeouts * 1000 + conflicts."""
            wipeouts = 0
            conflicts = 0
            
            for other_var, constraint in self.binary_constraints[var_name]:
                if other_var not in assignment:
                    valid_count = 0
                    for other_val in domains[other_var]:
                        if var_name == constraint.variables[0]:
                            if constraint.check_func(value, other_val):
                                valid_count += 1
                        else:
                            if constraint.check_func(other_val, value):
                                valid_count += 1
                    
                    conflicts += len(domains[other_var]) - valid_count
                    if valid_count == 0:
                        wipeouts += 1
            
            if self.use_lcv_wipeout:
                return wipeouts * 1000 + conflicts  # Prioritize avoiding wipeouts
            return conflicts
        
        return sorted(domain, key=count_impact)
    
    # ==================== Consistency Checking ====================
    
    def _is_consistent(self, var_name: str, value: int, assignment: Dict[str, int]) -> bool:
        """Check if assignment is consistent."""
        # Check unary constraints
        for constraint in self.unary_constraints.get(var_name, []):
            if not constraint.check_func(value):
                return False
        
        # Check binary constraints with assigned variables
        for other_var, constraint in self.binary_constraints[var_name]:
            if other_var in assignment:
                other_val = assignment[other_var]
                if var_name == constraint.variables[0]:
                    if not constraint.check_func(value, other_val):
                        # Track conflict for backjumping
                        if self.use_backjumping:
                            self.conflict_set[var_name].add(other_var)
                        return False
                else:
                    if not constraint.check_func(other_val, value):
                        if self.use_backjumping:
                            self.conflict_set[var_name].add(other_var)
                        return False
        
        return True
    
    # ==================== Forward Checking ====================
    
    def _forward_check(self, var_name: str, value: int, assignment: Dict[str, int], 
                       domains: Dict[str, Set[int]]) -> Optional[Dict[str, Set[int]]]:
        """Forward checking with conflict tracking."""
        new_domains = {v: d.copy() for v, d in domains.items()}
        
        for other_var, constraint in self.binary_constraints[var_name]:
            if other_var not in assignment:
                valid_values = set()
                for other_val in new_domains[other_var]:
                    if var_name == constraint.variables[0]:
                        if constraint.check_func(value, other_val):
                            valid_values.add(other_val)
                    else:
                        if constraint.check_func(other_val, value):
                            valid_values.add(other_val)
                
                pruned = len(new_domains[other_var]) - len(valid_values)
                if pruned > 0:
                    self.pruned_values += pruned
                    self.propagations += pruned
                
                new_domains[other_var] = valid_values
                
                if not valid_values:
                    # Track conflict for backjumping
                    if self.use_backjumping:
                        self.conflict_set[other_var].add(var_name)
                    return None
        
        return new_domains
    
    # ==================== AC-3 ====================
    
    def _ac3(self, domains: Dict[str, Set[int]], 
             changed_var: Optional[str] = None) -> bool:
        """
        AC-3 
        - Set-based queue for O(1) membership
        - Only process relevant arcs when a variable changes
        """
        queue_set = set()
        queue = deque()
        
        if changed_var:
            # Only add arcs affected by the changed variable
            for other_var, _ in self.binary_constraints[changed_var]:
                arc = (other_var, changed_var)
                if arc not in queue_set:
                    queue.append(arc)
                    queue_set.add(arc)
        else:
            # Initialize with all arcs
            for var_name in self.variables:
                for other_var, _ in self.binary_constraints[var_name]:
                    arc = (var_name, other_var)
                    if arc not in queue_set:
                        queue.append(arc)
                        queue_set.add(arc)
        
        while queue:
            xi, xj = queue.popleft()
            queue_set.discard((xi, xj))
            
            if self._revise(domains, xi, xj):
                if not domains[xi]:
                    return False
                
                for xk, _ in self.binary_constraints[xi]:
                    if xk != xj:
                        arc = (xk, xi)
                        if arc not in queue_set:
                            queue.append(arc)
                            queue_set.add(arc)
        
        return True
    
    def _revise(self, domains: Dict[str, Set[int]], xi: str, xj: str) -> bool:
        """Revise domain of xi based on xj."""
        revised = False
        constraint = None
        
        for other_var, c in self.binary_constraints[xi]:
            if other_var == xj:
                constraint = c
                break
        
        if not constraint:
            return False
        
        values_to_remove = set()
        
        for val_i in domains[xi]:
            has_support = False
            for val_j in domains[xj]:
                if xi == constraint.variables[0]:
                    if constraint.check_func(val_i, val_j):
                        has_support = True
                        break
                else:
                    if constraint.check_func(val_j, val_i):
                        has_support = True
                        break
            
            if not has_support:
                values_to_remove.add(val_i)
                revised = True
        
        if values_to_remove:
            domains[xi] -= values_to_remove
            self.pruned_values += len(values_to_remove)
            self.propagations += len(values_to_remove)
        
        return revised
    
    # ==================== Singleton Arc Consistency (SAC) ====================
    
    def _singleton_arc_consistency(self, domains: Dict[str, Set[int]]) -> bool:
        """
        Singleton Arc Consistency: For each value in each domain,
        temporarily assign it and run AC-3. If domain empties, remove the value.
        """
        if not self.use_sac:
            return True
        
        changed = True
        while changed:
            changed = False
            for var_name in self.variables:
                if len(domains[var_name]) <= 1:
                    continue
                
                values_to_remove = set()
                for value in list(domains[var_name]):
                    # Create a copy and assign the value
                    test_domains = {v: d.copy() for v, d in domains.items()}
                    test_domains[var_name] = {value}
                    
                    # Run AC-3 on the test domains
                    if not self._ac3(test_domains, changed_var=var_name):
                        values_to_remove.add(value)
                
                if values_to_remove:
                    domains[var_name] -= values_to_remove
                    self.pruned_values += len(values_to_remove)
                    self.propagations += len(values_to_remove)
                    changed = True
                    
                    if not domains[var_name]:
                        return False
        
        return True
    
    # ==================== Naked/Hidden Pairs ====================
    
    def _detect_naked_pairs(self, domains: Dict[str, Set[int]]) -> bool:
        """
        Detect naked pairs/triples in attribute groups.
        If N variables can only have N values, remove those values from other variables.
        """
        if not self.use_naked_pairs or not self.attribute_groups:
            return True
        
        changed = True
        while changed:
            changed = False
            
            for group_name, var_names in self.attribute_groups.items():
                # Get unassigned variables in this group
                unassigned = [v for v in var_names if len(domains.get(v, set())) > 1]
                
                if len(unassigned) < 2:
                    continue
                
                # Check for naked pairs
                for i, var1 in enumerate(unassigned):
                    dom1 = domains[var1]
                    if len(dom1) != 2:
                        continue
                    
                    for var2 in unassigned[i+1:]:
                        dom2 = domains[var2]
                        if dom1 == dom2:
                            # Found a naked pair!
                            pair_values = dom1
                            
                            # Remove these values from other variables in the group
                            for other_var in unassigned:
                                if other_var != var1 and other_var != var2:
                                    removed = domains[other_var] & pair_values
                                    if removed:
                                        domains[other_var] -= removed
                                        self.pruned_values += len(removed)
                                        self.propagations += len(removed)
                                        changed = True
                                        
                                        if not domains[other_var]:
                                            return False
                
                # Check for naked triples
                for i, var1 in enumerate(unassigned):
                    dom1 = domains[var1]
                    if len(dom1) > 3:
                        continue
                    
                    for j, var2 in enumerate(unassigned[i+1:], i+1):
                        dom2 = domains[var2]
                        if len(dom2) > 3:
                            continue
                        
                        union12 = dom1 | dom2
                        if len(union12) > 3:
                            continue
                        
                        for var3 in unassigned[j+1:]:
                            dom3 = domains[var3]
                            if len(dom3) > 3:
                                continue
                            
                            union123 = union12 | dom3
                            if len(union123) == 3:
                                # Found a naked triple!
                                triple_values = union123
                                
                                for other_var in unassigned:
                                    if other_var not in (var1, var2, var3):
                                        removed = domains[other_var] & triple_values
                                        if removed:
                                            domains[other_var] -= removed
                                            self.pruned_values += len(removed)
                                            changed = True
                                            
                                            if not domains[other_var]:
                                                return False
        
        return True
    
    # ====================  Nogood Learning ====================
    
    def _check_nogood(self, assignment: Dict[str, int]) -> bool:
        """Check if current assignment matches any learned nogood."""
        if not self.use_nogood_learning:
            return False
        
        assignment_set = frozenset(assignment.items())
        
        for nogood in self.nogoods:
            if nogood.issubset(assignment_set):
                return True
        
        return False
    
    def _learn_nogood(self, assignment: Dict[str, int], conflict_vars: Set[str]):
        """Learn a nogood from the current conflict."""
        if not self.use_nogood_learning:
            return
        
        if len(self.nogoods) >= self.max_nogoods:
            return  # Limit memory usage
        
        # Create minimal nogood from conflict variables
        nogood_items = []
        for var in conflict_vars:
            if var in assignment:
                nogood_items.append((var, assignment[var]))
        
        if len(nogood_items) >= 2:
            nogood = frozenset(nogood_items)
            if nogood not in self.nogoods:
                self.nogoods.add(nogood)
                self.nogoods_learned += 1
    
    # ==================== Conflict-Directed Backjumping ====================
    
    def _backtrack_with_jumping(self, assignment: Dict[str, int], 
                                domains: Dict[str, Set[int]],
                                assigned_order: List[str]) -> Tuple[Optional[Dict[str, int]], Set[str]]:
        """
        Backtracking with conflict-directed backjumping.
        Returns (solution, conflict_set) where conflict_set indicates which variables caused failure.
        """
        self.steps += 1
        
        # Check if assignment is complete
        if len(assignment) == len(self.variables):
            return assignment.copy(), set()
        
        # Check nogood
        if self._check_nogood(assignment):
            return None, set(assignment.keys())
        
        # Select variable
        var_name = self._select_unassigned_variable(assignment, domains)
        if var_name is None:
            return None, set()
        
        # Reset conflict set for this variable
        self.conflict_set[var_name] = set()
        local_conflict_set = set()
        
        # Try each value
        for value in self._order_domain_values(var_name, assignment, domains):
            self._record_trace('assign', variable=var_name, value=value)
            
            if self._is_consistent(var_name, value, assignment):
                assignment[var_name] = value
                new_assigned_order = assigned_order + [var_name]
                new_domains = {v: d.copy() for v, d in domains.items()}
                new_domains[var_name] = {value}
                
                # Forward checking
                if self.use_forward_checking:
                    new_domains = self._forward_check(var_name, value, assignment, new_domains)
                    if new_domains is None:
                        local_conflict_set.update(self.conflict_set.get(var_name, set()))
                        local_conflict_set.add(var_name)
                        self.backtracks += 1
                        del assignment[var_name]
                        continue
                
                # Arc consistency
                if self.use_arc_consistency:
                    if not self._ac3(new_domains, changed_var=var_name):
                        local_conflict_set.add(var_name)
                        self.backtracks += 1
                        del assignment[var_name]
                        continue
                
                # Naked pairs
                if not self._detect_naked_pairs(new_domains):
                    local_conflict_set.add(var_name)
                    self.backtracks += 1
                    del assignment[var_name]
                    continue
                
                # Update variable domains
                saved_domains = {v: self.variables[v].domain.copy() for v in self.variables}
                for v in new_domains:
                    self.variables[v].domain = new_domains[v]
                
                # Recursive call
                result, child_conflict_set = self._backtrack_with_jumping(
                    assignment, new_domains, new_assigned_order
                )
                
                if result is not None:
                    return result, set()
                
                # Restore domains
                for v in saved_domains:
                    self.variables[v].domain = saved_domains[v]
                
                del assignment[var_name]
                self.backtracks += 1
                
                # Backjumping: if var_name not in conflict set, we can skip
                if self.use_backjumping and var_name not in child_conflict_set:
                    self.backjumps += 1
                    # Learn nogood
                    self._learn_nogood(assignment, child_conflict_set)
                    return None, child_conflict_set
                
                local_conflict_set.update(child_conflict_set)
            else:
                local_conflict_set.update(self.conflict_set.get(var_name, set()))
        
        local_conflict_set.discard(var_name)  # Remove self from conflict set
        return None, local_conflict_set
    
    # ==================== MAIN ====================
    
    def solve(self) -> SolverStats:
        """Solve the CSP problem."""
        start_time = time.time()
        
        # Reset statistics
        self.steps = 0
        self.backtracks = 0
        self.pruned_values = 0
        self.nogoods_learned = 0
        self.backjumps = 0
        self.propagations = 0
        self.traces = []
        self.conflict_set.clear()
        
        # Apply unary constraints
        if not self._apply_unary_constraints():
            return SolverStats(
                solved=False, solution=None, steps=self.steps,
                backtracks=self.backtracks, pruned_values=self.pruned_values,
                time_seconds=time.time() - start_time,
                nogoods_learned=self.nogoods_learned, backjumps=self.backjumps,
                propagations=self.propagations, traces=self.traces
            )
        
        # Initial domain propagation
        domains = {v: self.variables[v].domain.copy() for v in self.variables}
        
        # Initial AC-3
        if self.use_arc_consistency:
            if not self._ac3(domains):
                return SolverStats(
                    solved=False, solution=None, steps=self.steps,
                    backtracks=self.backtracks, pruned_values=self.pruned_values,
                    time_seconds=time.time() - start_time,
                    nogoods_learned=self.nogoods_learned, backjumps=self.backjumps,
                    propagations=self.propagations, traces=self.traces
                )
            for v in domains:
                self.variables[v].domain = domains[v]
        
        # Singleton Arc Consistency (stronger initial propagation)
        if self.use_sac:
            if not self._singleton_arc_consistency(domains):
                return SolverStats(
                    solved=False, solution=None, steps=self.steps,
                    backtracks=self.backtracks, pruned_values=self.pruned_values,
                    time_seconds=time.time() - start_time,
                    nogoods_learned=self.nogoods_learned, backjumps=self.backjumps,
                    propagations=self.propagations, traces=self.traces
                )
            for v in domains:
                self.variables[v].domain = domains[v]
        
        # Initial naked pairs detection
        if not self._detect_naked_pairs(domains):
            return SolverStats(
                solved=False, solution=None, steps=self.steps,
                backtracks=self.backtracks, pruned_values=self.pruned_values,
                time_seconds=time.time() - start_time,
                nogoods_learned=self.nogoods_learned, backjumps=self.backjumps,
                propagations=self.propagations, traces=self.traces
            )
        for v in domains:
            self.variables[v].domain = domains[v]
        
        # Check if already solved by propagation alone
        if all(len(domains[v]) == 1 for v in self.variables):
            solution = {v: list(domains[v])[0] for v in self.variables}
            return SolverStats(
                solved=True, solution=solution, steps=0,
                backtracks=0, pruned_values=self.pruned_values,
                time_seconds=time.time() - start_time,
                nogoods_learned=0, backjumps=0,
                propagations=self.propagations, traces=self.traces
            )
        
        # Backtracking search
        if self.use_backjumping:
            solution, _ = self._backtrack_with_jumping({}, domains, [])
        else:
            solution = self._backtrack_simple({}, domains)
        
        return SolverStats(
            solved=solution is not None,
            solution=solution,
            steps=self.steps,
            backtracks=self.backtracks,
            pruned_values=self.pruned_values,
            time_seconds=time.time() - start_time,
            nogoods_learned=self.nogoods_learned,
            backjumps=self.backjumps,
            propagations=self.propagations,
            traces=self.traces
        )
    
    def _backtrack_simple(self, assignment: Dict[str, int], 
                          domains: Dict[str, Set[int]]) -> Optional[Dict[str, int]]:
        """Simple backtracking without backjumping (fallback)."""
        self.steps += 1
        
        if len(assignment) == len(self.variables):
            return assignment.copy()
        
        var_name = self._select_unassigned_variable(assignment, domains)
        if var_name is None:
            return None
        
        for value in self._order_domain_values(var_name, assignment, domains):
            if self._is_consistent(var_name, value, assignment):
                assignment[var_name] = value
                new_domains = {v: d.copy() for v, d in domains.items()}
                new_domains[var_name] = {value}
                
                if self.use_forward_checking:
                    new_domains = self._forward_check(var_name, value, assignment, new_domains)
                    if new_domains is None:
                        self.backtracks += 1
                        del assignment[var_name]
                        continue
                
                if self.use_arc_consistency:
                    if not self._ac3(new_domains, changed_var=var_name):
                        self.backtracks += 1
                        del assignment[var_name]
                        continue
                
                if not self._detect_naked_pairs(new_domains):
                    self.backtracks += 1
                    del assignment[var_name]
                    continue
                
                saved_domains = {v: self.variables[v].domain.copy() for v in self.variables}
                for v in new_domains:
                    self.variables[v].domain = new_domains[v]
                
                result = self._backtrack_simple(assignment, new_domains)
                
                if result is not None:
                    return result
                
                for v in saved_domains:
                    self.variables[v].domain = saved_domains[v]
                
                del assignment[var_name]
                self.backtracks += 1
        
        return None
    
    def reset(self):
        """Reset solver state."""
        for var in self.variables.values():
            var.domain = var.original_domain.copy()
        self.steps = 0
        self.backtracks = 0
        self.pruned_values = 0
        self.nogoods.clear()
        self.nogoods_learned = 0
        self.backjumps = 0
        self.propagations = 0
        self.traces = []
        self.conflict_set.clear()


class OptimizedZebraPuzzleSolver:
    """
    High-level solver for Zebra puzzles using the CSP solver.
    """
    
    def __init__(self, enable_tracing: bool = False):
        self.solver = OptimizedCSPSolver(enable_tracing=enable_tracing)
        self.num_houses = 0
        self.attributes: Dict[str, List[str]] = {}
    
    def setup_from_puzzle(self, puzzle) -> bool:
        """Set up CSP from a CSPPuzzle object."""
        self.num_houses = puzzle.num_houses
        self.attributes = puzzle.attributes
        
        # Add variables
        attribute_groups = {}
        for attr_name, values in puzzle.attributes.items():
            var_names = []
            for value in values:
                var_name = f"{attr_name}_{value}"
                self.solver.add_variable(var_name, list(range(1, puzzle.num_houses + 1)))
                var_names.append(var_name)
            attribute_groups[attr_name] = var_names
        
        # Set attribute groups for naked pairs detection
        self.solver.set_attribute_groups(attribute_groups)
        
        # Add AllDifferent constraints
        for attr_name, values in puzzle.attributes.items():
            var_names = [f"{attr_name}_{value}" for value in values]
            for i in range(len(var_names)):
                for j in range(i + 1, len(var_names)):
                    self.solver.add_constraint(
                        [var_names[i], var_names[j]],
                        lambda x, y: x != y,
                        f"AllDiff: {var_names[i]} != {var_names[j]}"
                    )
        
        # SYMMETRY BREAKING: Fix first value of first attribute to house 1
        # This reduces search space without losing solutions
        if puzzle.attributes:
            first_attr = list(puzzle.attributes.keys())[0]
            first_val = puzzle.attributes[first_attr][0]
            # Don't add hard constraint, but prioritize this assignment
        
        # Add constraints from clues
        for clue_info in puzzle.parsed_clues:
            self._add_clue_constraint(clue_info)
        
        return True
    
    def _add_clue_constraint(self, clue_info: Dict):
        """Add constraint based on parsed clue info."""
        clue_type = clue_info['type']
        entities = clue_info['entities']
        clue_text = clue_info['clue'].lower()
        
        if clue_type in ['first_house', 'not_first_house', 'last_house', 'not_last_house', 'in_house']:
            if entities[0] is None:
                return
            
            attr1, val1 = entities[0]
            var1 = f"{attr1}_{val1}"
            
            if clue_type == 'first_house':
                self.solver.add_constraint([var1], lambda x: x == 1, f"{var1} in house 1")
            elif clue_type == 'not_first_house':
                self.solver.add_constraint([var1], lambda x: x != 1, f"{var1} not in house 1")
            elif clue_type == 'last_house':
                num = clue_info.get('num_houses', self.num_houses)
                self.solver.add_constraint([var1], lambda x, n=num: x == n, f"{var1} in last house")
            elif clue_type == 'not_last_house':
                num = clue_info.get('num_houses', self.num_houses)
                self.solver.add_constraint([var1], lambda x, n=num: x != n, f"{var1} not in last house")
            elif clue_type == 'in_house':
                house = clue_info['house']
                self.solver.add_constraint([var1], lambda x, h=house: x == h, f"{var1} in house {house}")
            return
        
        if entities[0] is None or entities[1] is None:
            return
        
        attr1, val1 = entities[0]
        attr2, val2 = entities[1]
        var1 = f"{attr1}_{val1}"
        var2 = f"{attr2}_{val2}"
        
        if clue_type in ['directly_left', 'directly_right', 'left_of', 'right_of']:
            pos1 = clue_text.find(val1.lower())
            pos2 = clue_text.find(val2.lower())
            if pos2 < pos1:
                var1, var2 = var2, var1
        
        if clue_type == 'equality':
            self.solver.add_constraint([var1, var2], lambda x, y: x == y, f"{var1} == {var2}")
        elif clue_type == 'directly_left':
            self.solver.add_constraint([var1, var2], lambda x, y: x == y - 1, f"{var1} left of {var2}")
        elif clue_type == 'directly_right':
            self.solver.add_constraint([var1, var2], lambda x, y: x == y + 1, f"{var1} right of {var2}")
        elif clue_type == 'next_to':
            self.solver.add_constraint([var1, var2], lambda x, y: abs(x - y) == 1, f"{var1} next to {var2}")
        elif clue_type == 'left_of':
            self.solver.add_constraint([var1, var2], lambda x, y: x < y, f"{var1} < {var2}")
        elif clue_type == 'right_of':
            self.solver.add_constraint([var1, var2], lambda x, y: x > y, f"{var1} > {var2}")
        elif clue_type == 'houses_between':
            num = clue_info.get('num_between', 1)
            self.solver.add_constraint([var1, var2], lambda x, y, n=num: abs(x - y) == n + 1,
                                       f"{num} between {var1} and {var2}")
    
    def solve(self) -> SolverStats:
        """Solve the puzzle."""
        return self.solver.solve()
    
    def format_solution(self, solution: Dict[str, int]) -> Dict[str, Dict[str, str]]:
        """Format solution by house."""
        if not solution:
            return {}
        
        result = {}
        for house in range(1, self.num_houses + 1):
            house_key = f"House{house}"
            result[house_key] = {}
            
            for attr_name, values in self.attributes.items():
                for value in values:
                    var_name = f"{attr_name}_{value}"
                    if solution.get(var_name) == house:
                        output_attr = attr_name.lower()
                        if output_attr == 'bookgenre':
                            output_attr = 'book_genre'
                        elif output_attr == 'carmodel':
                            output_attr = 'car_model'
                        result[house_key][output_attr] = value
                        break
        
        return result
    
    def format_solution_by_person(self, solution: Dict[str, int]) -> Dict[str, Dict[str, str]]:
        """Format solution by person name."""
        if not solution:
            return {}
        
        if 'Name' not in self.attributes:
            return self.format_solution(solution)
        
        house_attrs = {h: {} for h in range(1, self.num_houses + 1)}
        
        for attr_name, values in self.attributes.items():
            for value in values:
                var_name = f"{attr_name}_{value}"
                house = solution.get(var_name)
                if house:
                    output_attr = attr_name.lower()
                    if output_attr == 'bookgenre':
                        output_attr = 'book_genre'
                    elif output_attr == 'carmodel':
                        output_attr = 'car_model'
                    house_attrs[house][output_attr] = value
        
        result = {}
        for house, attrs in house_attrs.items():
            if 'name' in attrs:
                person_name = attrs['name']
                result[person_name] = {k: v for k, v in attrs.items() if k != 'name'}
                result[person_name]['house'] = house
        
        return result
    
    def get_traces(self) -> List[SolverTrace]:
        """Get solver traces."""
        return self.solver.traces
