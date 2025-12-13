"""
Trace Generator for CSP Solver
==============================
Logs feature vectors at each decision step for training purposes.
"""

import json
import csv
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import os

from solver import SolverTrace, SolverStats, ZebraPuzzleSolver


@dataclass
class TraceFeatures:
    """Feature vector for a single decision step."""
    # Puzzle info
    puzzle_id: str
    step_num: int
    
    # Action info
    action: str
    variable: str
    value: Optional[int]
    
    # Domain features
    min_domain_size: int
    max_domain_size: int
    avg_domain_size: float
    total_remaining_values: int
    num_singleton_domains: int  # domains with size 1
    num_empty_domains: int  # domains with size 0
    
    # Constraint features
    constraint_count: int
    
    # Variable-specific features (for selected variable)
    selected_var_domain_size: int
    selected_var_constraint_degree: int  # number of constraints involving this variable
    
    # Search state
    assignment_depth: int  # number of variables already assigned
    
    # Outcome (known after solving)
    led_to_solution: bool
    led_to_backtrack: bool


class TraceGenerator:
    """Generates and exports trace data from solver runs."""
    
    def __init__(self, output_dir: str = "traces"):
        self.output_dir = output_dir
        self.all_traces: List[TraceFeatures] = []
        
        # Create output directory if needed
        os.makedirs(output_dir, exist_ok=True)
    
    def process_solver_traces(self, puzzle_id: str, traces: List[SolverTrace], 
                             stats: SolverStats, solver: ZebraPuzzleSolver) -> List[TraceFeatures]:
        """
        Convert solver traces to feature vectors.
        
        Args:
            puzzle_id: Unique puzzle identifier
            traces: List of SolverTrace objects
            stats: Final solver statistics
            solver: The solver instance (for constraint info)
        
        Returns:
            List of TraceFeatures
        """
        features_list = []
        assignment_depth = 0
        
        # Track which steps led to solution vs backtrack
        backtrack_steps = set()
        for i, trace in enumerate(traces):
            if trace.action == 'backtrack':
                # Mark the corresponding assign step
                for j in range(i - 1, -1, -1):
                    if traces[j].action == 'assign' and traces[j].variable == trace.variable:
                        backtrack_steps.add(j)
                        break
        
        for i, trace in enumerate(traces):
            # Calculate domain statistics
            domain_sizes = list(trace.domain_sizes.values())
            
            # Get constraint degree for selected variable
            constraint_degree = 0
            if trace.variable and trace.variable in solver.solver.binary_constraints:
                constraint_degree = len(solver.solver.binary_constraints[trace.variable])
            
            # Update assignment depth
            if trace.action == 'assign':
                assignment_depth += 1
            elif trace.action == 'backtrack':
                assignment_depth -= 1
            
            features = TraceFeatures(
                puzzle_id=puzzle_id,
                step_num=trace.step,
                action=trace.action,
                variable=trace.variable or "",
                value=trace.value,
                min_domain_size=min(domain_sizes) if domain_sizes else 0,
                max_domain_size=max(domain_sizes) if domain_sizes else 0,
                avg_domain_size=sum(domain_sizes) / len(domain_sizes) if domain_sizes else 0,
                total_remaining_values=trace.remaining_values,
                num_singleton_domains=sum(1 for d in domain_sizes if d == 1),
                num_empty_domains=sum(1 for d in domain_sizes if d == 0),
                constraint_count=trace.constraint_count,
                selected_var_domain_size=trace.domain_sizes.get(trace.variable, 0) if trace.variable else 0,
                selected_var_constraint_degree=constraint_degree,
                assignment_depth=assignment_depth,
                led_to_solution=stats.solved and i not in backtrack_steps,
                led_to_backtrack=i in backtrack_steps
            )
            
            features_list.append(features)
        
        self.all_traces.extend(features_list)
        return features_list
    
    def save_traces_json(self, filename: str = None):
        """Save all traces to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"traces_{timestamp}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump([asdict(t) for t in self.all_traces], f, indent=2)
        
        print(f"Saved {len(self.all_traces)} traces to {filepath}")
        return filepath
    
    def save_traces_csv(self, filename: str = None):
        """Save all traces to CSV file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"traces_{timestamp}.csv"
        
        filepath = os.path.join(self.output_dir, filename)
        
        if not self.all_traces:
            print("No traces to save")
            return None
        
        with open(filepath, 'w', newline='') as f:
            fieldnames = list(asdict(self.all_traces[0]).keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for trace in self.all_traces:
                writer.writerow(asdict(trace))
        
        print(f"Saved {len(self.all_traces)} traces to {filepath}")
        return filepath
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics of collected traces."""
        if not self.all_traces:
            return {"total_traces": 0}
        
        actions = {}
        for trace in self.all_traces:
            actions[trace.action] = actions.get(trace.action, 0) + 1
        
        solution_traces = sum(1 for t in self.all_traces if t.led_to_solution)
        backtrack_traces = sum(1 for t in self.all_traces if t.led_to_backtrack)
        
        return {
            "total_traces": len(self.all_traces),
            "unique_puzzles": len(set(t.puzzle_id for t in self.all_traces)),
            "action_counts": actions,
            "solution_traces": solution_traces,
            "backtrack_traces": backtrack_traces,
            "avg_domain_size": sum(t.avg_domain_size for t in self.all_traces) / len(self.all_traces),
            "avg_assignment_depth": sum(t.assignment_depth for t in self.all_traces) / len(self.all_traces)
        }
    
    def clear(self):
        """Clear all collected traces."""
        self.all_traces = []


def generate_traces_for_puzzles(puzzles, output_dir: str = "traces", 
                                max_puzzles: Optional[int] = None) -> Dict[str, Any]:
    """
    Generate traces for a list of puzzles.
    
    Args:
        puzzles: List of CSPPuzzle objects
        output_dir: Directory to save trace files
        max_puzzles: Maximum number of puzzles to process
    
    Returns:
        Summary statistics
    """
    generator = TraceGenerator(output_dir)
    
    if max_puzzles:
        puzzles = puzzles[:max_puzzles]
    
    print(f"Generating traces for {len(puzzles)} puzzles...")
    
    solved_count = 0
    failed_count = 0
    
    for i, puzzle in enumerate(puzzles):
        print(f"  Processing {puzzle.puzzle_id} ({i+1}/{len(puzzles)})...", end=" ")
        
        try:
            solver = ZebraPuzzleSolver(enable_tracing=True)
            solver.setup_from_puzzle(puzzle)
            stats = solver.solve()
            
            if stats.solved:
                solved_count += 1
                print(f"✓ Solved in {stats.steps} steps")
            else:
                failed_count += 1
                print(f"✗ No solution")
            
            # Process traces
            generator.process_solver_traces(puzzle.puzzle_id, stats.traces, stats, solver)
            
        except Exception as e:
            failed_count += 1
            print(f"✗ Error: {e}")
    
    # Save traces
    generator.save_traces_json()
    generator.save_traces_csv()
    
    summary = generator.get_summary()
    summary['solved_puzzles'] = solved_count
    summary['failed_puzzles'] = failed_count
    
    print(f"\n=== Trace Generation Summary ===")
    print(f"Puzzles solved: {solved_count}/{len(puzzles)}")
    print(f"Total traces: {summary['total_traces']}")
    print(f"Action counts: {summary.get('action_counts', {})}")
    
    return summary


if __name__ == "__main__":
    # Test trace generation
    print("Testing Trace Generator...")
    
    # Import data loader
    try:
        from data_loader import load_zebra_logic_bench, CSPPuzzle
        
        # Load a few puzzles
        puzzles = load_zebra_logic_bench(split="test", max_puzzles=5)
        
        if puzzles:
            summary = generate_traces_for_puzzles(puzzles, max_puzzles=3)
            print(f"\nFull summary: {summary}")
        else:
            print("No puzzles loaded")
            
    except ImportError as e:
        print(f"Could not import data_loader: {e}")
        print("Make sure data_loader.py is in the same directory")
    except Exception as e:
        print(f"Error: {e}")
        print("\nTo test with the HuggingFace dataset, install: pip install datasets")
