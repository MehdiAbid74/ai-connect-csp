#!/usr/bin/env python3
"""
AI Connect 2025 - CSP Solver Runner
===================================
Script to run the solver on test puzzles and generate results.json

Usage:
    python run.py                           # Run on ZebraLogicBench test set
    python run.py --input test.json         # Run on local JSON file
    python run.py --input data.csv          # Run on CSV file
    python run.py --input data.parquet      # Run on Parquet file
    python run.py --max 100                 # Limit number of puzzles
    python run.py --trace                   # Enable trace generation
    python run.py --output results.json     # Specify output file

For final submission:
    python run.py --input held_out_test.json --output results.json
"""

import argparse
import json
import sys
import time
from typing import Dict, List, Optional, Any

from data_loader import load_puzzles, CSPPuzzle
from solver import ZebraPuzzleSolver, SolverStats
from trace_generator import TraceGenerator


def solve_puzzles(puzzles: List[CSPPuzzle], 
                  enable_tracing: bool = False,
                  verbose: bool = True) -> Dict[str, Any]:
    """
    Solve a list of puzzles and return results.
    
    Args:
        puzzles: List of CSPPuzzle objects
        enable_tracing: Whether to generate traces
        verbose: Print progress
    
    Returns:
        Dictionary with results and statistics
    """
    results = {}
    stats_list = []
    trace_generator = TraceGenerator() if enable_tracing else None
    
    total_start = time.time()
    solved_count = 0
    
    for i, puzzle in enumerate(puzzles):
        if verbose:
            print(f"[{i+1}/{len(puzzles)}] Solving {puzzle.puzzle_id}...", end=" ", flush=True)
        
        try:
            solver = ZebraPuzzleSolver(enable_tracing=enable_tracing)
            solver.setup_from_puzzle(puzzle)
            stats = solver.solve()
            
            if stats.solved:
                solved_count += 1
                # Format solution for output
                solution = solver.format_solution_by_person(stats.solution)
                results[puzzle.puzzle_id] = solution
                
                if verbose:
                    print(f"✓ ({stats.steps} steps, {stats.time_seconds*1000:.1f}ms)")
            else:
                results[puzzle.puzzle_id] = {"error": "No solution found"}
                if verbose:
                    print("✗ No solution")
            
            # Collect statistics
            stats_list.append({
                'puzzle_id': puzzle.puzzle_id,
                'solved': stats.solved,
                'steps': stats.steps,
                'backtracks': stats.backtracks,
                'time_seconds': stats.time_seconds
            })
            
            # Process traces if enabled
            if enable_tracing and trace_generator:
                trace_generator.process_solver_traces(
                    puzzle.puzzle_id, stats.traces, stats, solver
                )
                
        except Exception as e:
            results[puzzle.puzzle_id] = {"error": str(e)}
            if verbose:
                print(f"✗ Error: {e}")
            
            stats_list.append({
                'puzzle_id': puzzle.puzzle_id,
                'solved': False,
                'steps': 0,
                'backtracks': 0,
                'time_seconds': 0,
                'error': str(e)
            })
    
    total_time = time.time() - total_start
    
    # Calculate summary statistics
    solved_stats = [s for s in stats_list if s['solved']]
    
    summary = {
        'total_puzzles': len(puzzles),
        'solved': solved_count,
        'accuracy': (solved_count / len(puzzles) * 100) if puzzles else 0,
        'avg_steps': sum(s['steps'] for s in solved_stats) / len(solved_stats) if solved_stats else 0,
        'avg_time_ms': (sum(s['time_seconds'] for s in stats_list) / len(stats_list) * 1000) if stats_list else 0,
        'total_time_seconds': total_time
    }
    
    # Save traces if enabled
    if trace_generator:
        trace_generator.save_traces_json('solver_traces.json')
        trace_generator.save_traces_csv('solver_traces.csv')
    
    return {
        'results': results,
        'stats': stats_list,
        'summary': summary
    }


def main():
    parser = argparse.ArgumentParser(
        description='AI Connect 2025 - CSP Solver for ZebraLogicBench',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py                           # Run on ZebraLogicBench
  python run.py --input test.json         # Run on local JSON file
  python run.py --input data.csv          # Run on CSV file
  python run.py --max 100 --trace         # Limit puzzles and enable tracing
  
For final submission:
  python run.py --input held_out_test.json --output results.json
        """
    )
    parser.add_argument(
        '--input', '-i',
        type=str,
        help='Input source: JSON/CSV/Parquet file path, or "zebra" for HuggingFace'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='results.json',
        help='Output file for results (default: results.json)'
    )
    parser.add_argument(
        '--max', '-m',
        type=int,
        default=None,
        help='Maximum number of puzzles to solve'
    )
    parser.add_argument(
        '--split', '-s',
        type=str,
        default='test',
        help='Dataset split to use (default: test)'
    )
    parser.add_argument(
        '--mode',
        type=str,
        default='grid_mode',
        choices=['grid_mode', 'mc_mode'],
        help='ZebraLogicBench mode: grid_mode or mc_mode (default: grid_mode)'
    )
    parser.add_argument(
        '--trace', '-t',
        action='store_true',
        help='Enable trace generation'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress progress output'
    )
    parser.add_argument(
        '--puzzle-column',
        type=str,
        default='puzzle',
        help='Column name for puzzle text in CSV/Parquet (default: puzzle)'
    )
    parser.add_argument(
        '--id-column',
        type=str,
        default='id',
        help='Column name for puzzle ID in CSV/Parquet (default: id)'
    )
    
    args = parser.parse_args()
    
    # Load puzzles
    print("=" * 60)
    print("AI Connect 2025 - CSP Solver")
    print("=" * 60)
    
    try:
        if args.input:
            print(f"\nLoading puzzles from: {args.input}")
            puzzles = load_puzzles(
                args.input,
                split=args.split,
                max_puzzles=args.max,
                mode=args.mode,
                puzzle_column=args.puzzle_column,
                id_column=args.id_column
            )
        else:
            print(f"\nLoading ZebraLogicBench ({args.split} split, {args.mode})...")
            puzzles = load_puzzles(
                "zebra",
                split=args.split,
                max_puzzles=args.max,
                mode=args.mode
            )
    except Exception as e:
        print(f"Error loading dataset: {e}")
        print("\nMake sure you have the datasets library installed:")
        print("  pip install datasets")
        sys.exit(1)
    
    if not puzzles:
        print("No puzzles to solve!")
        sys.exit(1)
    
    if args.max and len(puzzles) > args.max:
        puzzles = puzzles[:args.max]
    
    print(f"Loaded {len(puzzles)} puzzles\n")
    
    # Solve puzzles
    print("Solving puzzles...")
    print("-" * 60)
    
    output = solve_puzzles(
        puzzles,
        enable_tracing=args.trace,
        verbose=not args.quiet
    )
    
    # Save results
    print("-" * 60)
    print("\nSaving results...")
    
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output['results'], f, indent=2, ensure_ascii=False)
    print(f"  Results saved to: {args.output}")
    
    # Save detailed stats
    stats_file = args.output.replace('.json', '_stats.json')
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump({
            'summary': output['summary'],
            'details': output['stats']
        }, f, indent=2)
    print(f"  Statistics saved to: {stats_file}")
    
    # Print summary
    summary = output['summary']
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Puzzles solved: {summary['solved']}/{summary['total_puzzles']}")
    print(f"  Accuracy: {summary['accuracy']:.2f}%")
    print(f"  Avg steps: {summary['avg_steps']:.2f}")
    print(f"  Avg time: {summary['avg_time_ms']:.2f}ms")
    print(f"  Total time: {summary['total_time_seconds']:.2f}s")
    print("=" * 60)
    
    # Return exit code based on success rate
    if summary['accuracy'] >= 50:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
