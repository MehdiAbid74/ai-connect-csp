# 3×3 Logic Puzzle Solver (CSP)

This project solves the provided “3 houses” logic puzzles from `Test_100_Puzzles.csv` and writes the answers to `results.csv`.

Each puzzle has 3 houses (House 1–3). Every house gets:
- one **Name**
- one **Color**
- one **Pet**

The clues say things like “Eve lives in the white house” or “The white house is immediately left of the red house”.

## Files

- `parser.py` – reads the puzzle text and turns each clue into a check the solver can apply
- `solver.py` – generates possible full grids, removes the ones that break clues, and counts steps
- `run.py` – runs all 100 puzzles and creates `results.csv`
- `Test_100_Puzzles.csv` – input dataset
- `results.csv` – output dataset (what you submit)

## What the solver is doing (in plain language)

1. **List all possible full answers**
  - For a 3×3 puzzle there are only 216 complete grids to consider.
2. **Apply the clues to throw out wrong answers**
  - If a candidate grid breaks any clue, it is removed.
3. **If more than one answer is still possible**
  - The puzzle is under-specified (multiple solutions).
  - The solver still outputs one valid solution, and it computes how many “choices” you would need to make to end up with that single solution.

This is a CSP approach: we have variables (Name/Color/Pet for each house), allowed values, and constraints (the clues) that eliminate invalid combinations.

## What “steps” means (how we count them)

We count two types of steps:

1. **Forward-checking steps (propagation):** when applying a clue actually reduces the remaining candidate solutions.
2. **Decision steps (branching):** when there are still multiple candidates left, and you must “pick” a value (a guess/choice) to narrow it down.

Total steps is:

$$
	ext{steps} = \text{forward\_check\_steps} + \text{decision\_steps}
$$

The solver minimizes `decision_steps` (the number of choices) after it has applied all clue propagation.

## Output format

`results.csv` has 3 columns:
- `id` – the puzzle id
- `grid_solution` – JSON for the solved 3×3 grid
- `steps` – the total steps (as defined above)

## Run

```bash
python run.py
```

This writes `results.csv` in the project folder.
