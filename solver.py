"""
CSP Solver with Backtracking, MRV, Forward Checking, and Arc Consistency
=========================================================================
A complete CSP solver for Zebra/Logic Grid puzzles.
"""

import time
from typing import Dict, List, Tuple, Optional, Any, Set, Callable
from dataclasses import dataclass, field
from collections import deque
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
    action: str  # 'select_variable', 'assign', 'backtrack', 'prune', 'arc_consistent'
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
    traces: List[SolverTrace] = field(default_factory=list)


class CSPSolver:
    """
    CSP Solver implementing:
    - Backtracking search
    - MRV (Minimum Remaining Values) heuristic
    - Forward Checking
    - AC-3 (Arc Consistency)
    """
    
    def __init__(self, enable_tracing: bool = False):
        self.variables: Dict[str, CSPVariable] = {}
        self.constraints: List[CSPConstraint] = []
        self.binary_constraints: Dict[str, List[Tuple[str, CSPConstraint]]] = {}
        self.unary_constraints: Dict[str, List[CSPConstraint]] = {}
        
        # Solver settings
        self.use_mrv = True
        self.use_forward_checking = True
        self.use_arc_consistency = True
        
        # Statistics
        self.steps = 0
        self.backtracks = 0
        self.pruned_values = 0
        
        # Tracing
        self.enable_tracing = enable_tracing
        self.traces: List[SolverTrace] = []
    
    def add_variable(self, name: str, domain: List[int]):
        """Add a variable with its domain."""
        self.variables[name] = CSPVariable(name, set(domain), set(domain))
        self.binary_constraints[name] = []
        self.unary_constraints[name] = []
    
    def add_constraint(self, variables: List[str], check_func: Callable, description: str = ""):
        """Add a constraint."""
        constraint = CSPConstraint(variables, check_func, description)
        self.constraints.append(constraint)
        
        if len(variables) == 1:
            self.unary_constraints[variables[0]].append(constraint)
        elif len(variables) == 2:
            self.binary_constraints[variables[0]].append((variables[1], constraint))
            self.binary_constraints[variables[1]].append((variables[0], constraint))
    
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
    
    def _select_unassigned_variable(self, assignment: Dict[str, int]) -> Optional[str]:
        """
        Select next variable using MRV (Minimum Remaining Values) heuristic.
        """
        unassigned = [v for v in self.variables if v not in assignment]
        
        if not unassigned:
            return None
        
        if self.use_mrv:
            # MRV: select variable with smallest domain
            best_var = min(unassigned, key=lambda v: len(self.variables[v].domain))
            
            self._record_trace('select_variable', variable=best_var, 
                             details={'reason': 'MRV', 'domain_size': len(self.variables[best_var].domain)})
            return best_var
        else:
            return unassigned[0]
    
    def _order_domain_values(self, var_name: str, assignment: Dict[str, int]) -> List[int]:
        """
        Order domain values (can implement LCV - Least Constraining Value).
        """
        return list(self.variables[var_name].domain)
    
    def _is_consistent(self, var_name: str, value: int, assignment: Dict[str, int]) -> bool:
        """
        Check if assigning value to var_name is consistent with current assignment.
        """
        test_assignment = assignment.copy()
        test_assignment[var_name] = value
        
        for constraint in self.constraints:
            # Check if all variables in constraint are assigned
            if all(v in test_assignment for v in constraint.variables):
                values = [test_assignment[v] for v in constraint.variables]
                if not constraint.check_func(*values):
                    return False
        
        return True
    
    def _forward_check(self, var_name: str, value: int, assignment: Dict[str, int], 
                       domains: Dict[str, Set[int]]) -> Optional[Dict[str, Set[int]]]:
        """
        Forward checking: prune domains of unassigned variables.
        Returns new domains or None if any domain becomes empty.
        """
        new_domains = {v: d.copy() for v, d in domains.items()}
        
        for other_var, constraint in self.binary_constraints[var_name]:
            if other_var not in assignment:
                # Prune values from other_var's domain
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
                    self._record_trace('prune', variable=other_var, 
                                      details={'pruned': pruned, 'caused_by': var_name})
                
                new_domains[other_var] = valid_values
                
                if not valid_values:
                    return None
        
        return new_domains
    
    def _ac3(self, domains: Dict[str, Set[int]]) -> bool:
        """
        AC-3 algorithm for arc consistency.
        Returns False if any domain becomes empty.
        """
        queue = deque()
        
        # Initialize queue with all arcs
        for var_name in self.variables:
            for other_var, _ in self.binary_constraints[var_name]:
                queue.append((var_name, other_var))
        
        while queue:
            xi, xj = queue.popleft()
            
            if self._revise(domains, xi, xj):
                if not domains[xi]:
                    return False
                
                # Add all arcs (xk, xi) where xk != xj
                for xk, _ in self.binary_constraints[xi]:
                    if xk != xj:
                        queue.append((xk, xi))
        
        return True
    
    def _revise(self, domains: Dict[str, Set[int]], xi: str, xj: str) -> bool:
        """
        Revise domain of xi based on xj.
        """
        revised = False
        
        # Find constraint between xi and xj
        constraint = None
        for other_var, c in self.binary_constraints[xi]:
            if other_var == xj:
                constraint = c
                break
        
        if not constraint:
            return False
        
        values_to_remove = set()
        
        for val_i in domains[xi]:
            # Check if there exists a value in xj's domain that satisfies constraint
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
        
        return revised
    
    def _backtrack(self, assignment: Dict[str, int], domains: Dict[str, Set[int]]) -> Optional[Dict[str, int]]:
        """
        Backtracking search with forward checking and arc consistency.
        """
        self.steps += 1
        
        # Check if assignment is complete
        if len(assignment) == len(self.variables):
            return assignment.copy()
        
        # Select unassigned variable
        var_name = self._select_unassigned_variable(assignment)
        if var_name is None:
            return None
        
        # Try each value in domain
        for value in self._order_domain_values(var_name, assignment):
            self._record_trace('assign', variable=var_name, value=value)
            
            if self._is_consistent(var_name, value, assignment):
                assignment[var_name] = value
                new_domains = domains.copy()
                new_domains[var_name] = {value}
                
                # Forward checking
                if self.use_forward_checking:
                    new_domains = self._forward_check(var_name, value, assignment, new_domains)
                    if new_domains is None:
                        self._record_trace('backtrack', variable=var_name, value=value,
                                          details={'reason': 'forward_check_failed'})
                        self.backtracks += 1
                        del assignment[var_name]
                        continue
                
                # Arc consistency
                if self.use_arc_consistency:
                    if not self._ac3(new_domains):
                        self._record_trace('backtrack', variable=var_name, value=value,
                                          details={'reason': 'arc_consistency_failed'})
                        self.backtracks += 1
                        del assignment[var_name]
                        continue
                    self._record_trace('arc_consistent', variable=var_name)
                
                # Update domains in variables
                saved_domains = {v: self.variables[v].domain.copy() for v in self.variables}
                for v in new_domains:
                    self.variables[v].domain = new_domains[v]
                
                # Recursive call
                result = self._backtrack(assignment, new_domains)
                
                if result is not None:
                    return result
                
                # Restore domains
                for v in saved_domains:
                    self.variables[v].domain = saved_domains[v]
                
                del assignment[var_name]
                self.backtracks += 1
                self._record_trace('backtrack', variable=var_name, value=value,
                                  details={'reason': 'no_solution'})
        
        return None
    
    def solve(self) -> SolverStats:
        """
        Solve the CSP problem.
        
        Returns:
            SolverStats with solution and statistics
        """
        start_time = time.time()
        
        # Reset statistics
        self.steps = 0
        self.backtracks = 0
        self.pruned_values = 0
        self.traces = []
        
        # Apply unary constraints first
        if not self._apply_unary_constraints():
            return SolverStats(
                solved=False,
                solution=None,
                steps=self.steps,
                backtracks=self.backtracks,
                pruned_values=self.pruned_values,
                time_seconds=time.time() - start_time,
                traces=self.traces
            )
        
        # Initial arc consistency
        domains = {v: self.variables[v].domain.copy() for v in self.variables}
        if self.use_arc_consistency:
            if not self._ac3(domains):
                return SolverStats(
                    solved=False,
                    solution=None,
                    steps=self.steps,
                    backtracks=self.backtracks,
                    pruned_values=self.pruned_values,
                    time_seconds=time.time() - start_time,
                    traces=self.traces
                )
            
            for v in domains:
                self.variables[v].domain = domains[v]
        
        # Backtracking search
        solution = self._backtrack({}, domains)
        
        return SolverStats(
            solved=solution is not None,
            solution=solution,
            steps=self.steps,
            backtracks=self.backtracks,
            pruned_values=self.pruned_values,
            time_seconds=time.time() - start_time,
            traces=self.traces
        )
    
    def reset(self):
        """Reset domains to original values."""
        for var in self.variables.values():
            var.domain = var.original_domain.copy()
        self.steps = 0
        self.backtracks = 0
        self.pruned_values = 0
        self.traces = []


class ZebraPuzzleSolver:
    """
    High-level solver specifically for Zebra/Logic Grid puzzles.
    Converts puzzle format to CSP and solves it.
    """
    
    def __init__(self, enable_tracing: bool = False):
        self.solver = CSPSolver(enable_tracing=enable_tracing)
        self.num_houses = 0
        self.attributes: Dict[str, List[str]] = {}
    
    def setup_from_puzzle(self, puzzle) -> bool:
        """
        Set up CSP from a CSPPuzzle object.
        
        Args:
            puzzle: CSPPuzzle object from data_loader
        
        Returns:
            True if setup successful
        """
        self.num_houses = puzzle.num_houses
        self.attributes = puzzle.attributes
        
        # Add variables
        for attr_name, values in puzzle.attributes.items():
            for value in values:
                var_name = f"{attr_name}_{value}"
                self.solver.add_variable(var_name, list(range(1, puzzle.num_houses + 1)))
        
        # Add AllDifferent constraints for each attribute
        for attr_name, values in puzzle.attributes.items():
            var_names = [f"{attr_name}_{value}" for value in values]
            for i in range(len(var_names)):
                for j in range(i + 1, len(var_names)):
                    self.solver.add_constraint(
                        [var_names[i], var_names[j]],
                        lambda x, y: x != y,
                        f"AllDiff: {var_names[i]} != {var_names[j]}"
                    )
        
        # Add constraints from clues
        for clue_info in puzzle.parsed_clues:
            self._add_clue_constraint(clue_info)
        
        return True
    
    def _add_clue_constraint(self, clue_info: Dict):
        """Add constraint based on parsed clue info."""
        clue_type = clue_info['type']
        entities = clue_info['entities']
        clue_text = clue_info['clue'].lower()
        
        # Handle position constraints (only need one entity)
        if clue_type in ['first_house', 'not_first_house', 'last_house', 'not_last_house', 'in_house']:
            if entities[0] is None:
                return
            
            attr1, val1 = entities[0]
            var1 = f"{attr1}_{val1}"
            
            if clue_type == 'first_house':
                self.solver.add_constraint([var1], lambda x: x == 1, f"{var1} is in house 1")
            elif clue_type == 'not_first_house':
                self.solver.add_constraint([var1], lambda x: x != 1, f"{var1} is not in house 1")
            elif clue_type == 'last_house':
                num = clue_info.get('num_houses', self.num_houses)
                self.solver.add_constraint([var1], lambda x, n=num: x == n, f"{var1} is in last house")
            elif clue_type == 'not_last_house':
                num = clue_info.get('num_houses', self.num_houses)
                self.solver.add_constraint([var1], lambda x, n=num: x != n, f"{var1} is not in last house")
            elif clue_type == 'in_house':
                house = clue_info['house']
                self.solver.add_constraint([var1], lambda x, h=house: x == h, f"{var1} is in house {house}")
            return
        
        # Handle binary constraints (need two entities)
        if entities[0] is None or entities[1] is None:
            return
        
        attr1, val1 = entities[0]
        attr2, val2 = entities[1]
        var1 = f"{attr1}_{val1}"
        var2 = f"{attr2}_{val2}"
        
        # Determine order based on position in clue for directional constraints
        if clue_type in ['directly_left', 'directly_right', 'left_of', 'right_of']:
            pos1 = clue_text.find(val1.lower())
            pos2 = clue_text.find(val2.lower())
            if pos2 < pos1:
                var1, var2 = var2, var1
        
        if clue_type == 'equality':
            self.solver.add_constraint([var1, var2], lambda x, y: x == y, 
                                       f"{var1} == {var2}")
        
        elif clue_type == 'directly_left':
            self.solver.add_constraint([var1, var2], lambda x, y: x == y - 1,
                                       f"{var1} directly left of {var2}")
        
        elif clue_type == 'directly_right':
            self.solver.add_constraint([var1, var2], lambda x, y: x == y + 1,
                                       f"{var1} directly right of {var2}")
        
        elif clue_type == 'next_to':
            self.solver.add_constraint([var1, var2], lambda x, y: abs(x - y) == 1,
                                       f"{var1} next to {var2}")
        
        elif clue_type == 'left_of':
            self.solver.add_constraint([var1, var2], lambda x, y: x < y,
                                       f"{var1} left of {var2}")
        
        elif clue_type == 'right_of':
            self.solver.add_constraint([var1, var2], lambda x, y: x > y,
                                       f"{var1} right of {var2}")
        
        elif clue_type == 'houses_between':
            num = clue_info.get('num_between', 1)
            self.solver.add_constraint([var1, var2], lambda x, y, n=num: abs(x - y) == n + 1,
                                       f"{num} houses between {var1} and {var2}")
    
    def solve(self) -> SolverStats:
        """Solve the puzzle."""
        return self.solver.solve()
    
    def format_solution(self, solution: Dict[str, int]) -> Dict[str, Dict[str, str]]:
        """
        Format solution as required for submission.
        
        Args:
            solution: Dict mapping variable names to house numbers
        
        Returns:
            Dict mapping house/person to attributes
        """
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
                        # Normalize attribute name for output
                        output_attr = attr_name.lower()
                        if output_attr == 'bookgenre':
                            output_attr = 'book_genre'
                        elif output_attr == 'carmodel':
                            output_attr = 'car_model'
                        result[house_key][output_attr] = value
                        break
        
        return result
    
    def format_solution_by_person(self, solution: Dict[str, int]) -> Dict[str, Dict[str, str]]:
        """
        Format solution indexed by person name (if Name attribute exists).
        
        Args:
            solution: Dict mapping variable names to house numbers
        
        Returns:
            Dict mapping person name to their attributes
        """
        if not solution:
            return {}
        
        if 'Name' not in self.attributes:
            return self.format_solution(solution)
        
        result = {}
        
        # Build house -> attributes mapping first
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
        
        # Convert to person-indexed format
        for house, attrs in house_attrs.items():
            if 'name' in attrs:
                person_name = attrs['name']
                result[person_name] = {k: v for k, v in attrs.items() if k != 'name'}
                result[person_name]['house'] = house
        
        return result
    
    def get_traces(self) -> List[SolverTrace]:
        """Get solver traces."""
        return self.solver.traces


if __name__ == "__main__":
    # Test the solver with a simple example
    print("Testing CSP Solver...")
    
    solver = CSPSolver(enable_tracing=True)
    
    # Simple 3-house puzzle
    for name in ['Alice', 'Bob', 'Carol']:
        solver.add_variable(f'Name_{name}', [1, 2, 3])
    
    for color in ['Red', 'Blue', 'Green']:
        solver.add_variable(f'Color_{color}', [1, 2, 3])
    
    # AllDifferent for names
    solver.add_constraint(['Name_Alice', 'Name_Bob'], lambda x, y: x != y)
    solver.add_constraint(['Name_Alice', 'Name_Carol'], lambda x, y: x != y)
    solver.add_constraint(['Name_Bob', 'Name_Carol'], lambda x, y: x != y)
    
    # AllDifferent for colors
    solver.add_constraint(['Color_Red', 'Color_Blue'], lambda x, y: x != y)
    solver.add_constraint(['Color_Red', 'Color_Green'], lambda x, y: x != y)
    solver.add_constraint(['Color_Blue', 'Color_Green'], lambda x, y: x != y)
    
    # Alice lives in red house
    solver.add_constraint(['Name_Alice', 'Color_Red'], lambda x, y: x == y)
    
    # Bob is in house 2
    solver.add_constraint(['Name_Bob'], lambda x: x == 2)
    
    # Green house is to the right of blue house
    solver.add_constraint(['Color_Blue', 'Color_Green'], lambda x, y: x < y)
    
    stats = solver.solve()
    
    print(f"\nSolved: {stats.solved}")
    print(f"Solution: {stats.solution}")
    print(f"Steps: {stats.steps}")
    print(f"Backtracks: {stats.backtracks}")
    print(f"Time: {stats.time_seconds:.4f}s")
