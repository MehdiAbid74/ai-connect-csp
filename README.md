# AI Connect 2025 - CSP Solver for ZebraLogicBench

A Constraint Satisfaction Problem (CSP) solver for logic grid puzzles (Zebra puzzles) built for the AI Connect 2025 challenge.

## Overview

This project implements a symbolic CSP solver with:
- **Backtracking search** with intelligent variable/value ordering
- **MRV (Minimum Remaining Values)** heuristic for variable selection
- **Forward Checking** for early failure detection
- **AC-3 (Arc Consistency)** for constraint propagation
- **Trace generation** for analyzing search behavior

## Project Structure

```
ai-connect-csp/
├── data_loader.py      # Load & parse ZebraLogicBench puzzles
├── solver.py           # CSP solver with MRV, AC-3, forward checking
├── trace_generator.py  # Generate traces for training/analysis
├── evaluation.ipynb    # Evaluation notebook with metrics
├── run.py             # Main entry point for running solver
├── parser.py          # Legacy parser (single puzzle mode)
├── results.json       # Output file with solutions
└── README.md          # This file
```

## Quick Start

### 1. Setup Environment

**python contraint wont install**
Solution:
```bash
pip install python-constraint
```
(not just constraint)

### 3. Run the Solver

```bash
# Run on ZebraLogicBench test set
python run.py

# Run with options
python run.py --max 100          # Limit to 100 puzzles
python run.py --trace            # Enable trace generation
python run.py --input test.json  # Use custom input file
python run.py --help             # Show all options
```

### 4. Run Evaluation Notebook

Open `evaluation.ipynb` in Jupyter or VS Code and run all cells.

## Evaluation Metrics

The solver is evaluated using:

- **Accuracy** (%) - Percentage of puzzles solved correctly
- **Efficiency** - Average number of search steps
- **Composite Score** = Accuracy - α × (AvgSteps / MaxAvgSteps)
  - Where α = 10 is the efficiency penalty weight

## Solver Architecture

### CSP Formulation

For a puzzle with N houses and M attributes:
- **Variables**: `{Attribute}_{Value}` (e.g., `Name_Alice`, `Color_Red`)
- **Domains**: {1, 2, ..., N} representing house positions
- **Constraints**: Derived from puzzle clues

### Constraint Types Supported

| Type | Example Clue |
|------|--------------|
| Equality | "Eric is the person who loves mystery books" |
| Directly Left | "The dog owner is directly left of the cat owner" |
| Directly Right | "Alice is directly right of Bob" |
| Next To | "Alice and Bob are next to each other" |
| Left Of | "The red house is somewhere to the left of the blue house" |
| Right Of | "Peter is somewhere to the right of Carol" |
| Houses Between | "There is one house between Alice and Bob" |
| First House | "The tennis player is in the first house" |
| Not First House | "Carol is not in the first house" |
| In House N | "Alice lives in house 3" |

### Algorithm Flow

1. **Parse Puzzle** → Extract variables, domains, constraints
2. **Apply Unary Constraints** → Reduce domains immediately
3. **Initial AC-3** → Establish arc consistency
4. **Backtracking Search**:
   - Select unassigned variable (MRV)
   - Order domain values
   - For each value:
     - Check consistency
     - Forward check
     - AC-3 propagation
     - Recursive search or backtrack

## Output Format

### results.json

```json
{
  "puzzle_001": {
    "Alice": {"color": "red", "pet": "dog", "house": 1},
    "Bob": {"color": "blue", "pet": "cat", "house": 2}
  },
  "puzzle_002": {...}
}
```

### Trace Output (traces/solver_traces.json)

```json
[
  {
    "puzzle_id": "puzzle_001",
    "step_num": 1,
    "action": "assign",
    "variable": "Name_Alice",
    "value": 1,
    "min_domain_size": 3,
    "led_to_solution": true
  }
]
```

## Testing

```bash
# Test individual components
python data_loader.py     # Test data loading
python solver.py          # Test solver with simple example
python trace_generator.py # Test trace generation

# Run legacy single-puzzle parser
python parser.py
```

## Submission Checklist

- [] `solver.py` - CSP solver implementation
- [] `run.py` - Script to run solver on test puzzles
- [] `README.md` - Approach explanation
- [] `results.json` - Generated output for test set
- [] `evaluation.ipynb` - Analysis notebook

## Approach Summary

Our solver uses a **constraint propagation + backtracking** approach:

1. **Parsing**: Natural language clues are parsed using regex patterns to identify constraint types and entities.

2. **CSP Formulation**: Each attribute-value pair becomes a variable with domain {1..N}. AllDifferent constraints ensure each value appears once.

3. **Solving**: We use MRV to select the most constrained variable, forward checking to prune domains after assignments, and AC-3 to maintain arc consistency.

4. **Optimizations**:
   - Unary constraints applied upfront
   - Initial arc consistency before search
   - Domain pruning at each step
   - Early failure detection

## References

- ZebraLogicBench: https://huggingface.co/datasets/allenai/ZebraLogicBench
- AC-3 Algorithm: Mackworth, 1977
- Backtracking Search: Russell & Norvig, AIMA

