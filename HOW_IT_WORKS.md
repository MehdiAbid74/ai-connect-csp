# 🧩 How This Project Works - A Complete Beginner's Guide

## Table of Contents
1. [What is This Project?](#what-is-this-project)
2. [What Problem Does It Solve?](#what-problem-does-it-solve)
3. [The Puzzle Type We're Solving](#the-puzzle-type-were-solving)
4. [How Our Solver Works (The Brain)](#how-our-solver-works-the-brain)
5. [Project Files Explained](#project-files-explained)
6. [Step-by-Step: How Data Flows](#step-by-step-how-data-flows)
7. [How to Run the Project](#how-to-run-the-project)
8. [Understanding the Output](#understanding-the-output)
9. [Key Concepts Dictionary](#key-concepts-dictionary)
10. [Frequently Asked Questions](#frequently-asked-questions)

---

## What is This Project?

Imagine you have a really smart robot that can solve puzzles. This project is that robot's brain! 🤖

**In simple terms:** This is a computer program that automatically solves logic puzzles (like Sudoku, but more complex).

**Why was it built?** For the **AI Connect 2025 Challenge** - a competition where programmers build the best puzzle-solving program.

**What makes it special?** It doesn't just guess randomly. It uses smart strategies (algorithms) to solve puzzles quickly and correctly.

---

## What Problem Does It Solve?

### The Challenge
We have a dataset called **ZebraLogicBench** containing 1000+ logic puzzles. Our job is to:

1. ✅ **Read** the puzzles from the dataset
2. ✅ **Solve** each puzzle correctly
3. ✅ **Output** the answers in a specific format
4. ✅ **Be efficient** - solve quickly without wasting time

### The Scoring Formula
```
Score = Accuracy (%) - 10 × (Average Steps / Maximum Steps)
```

**Translation:** 
- Solve more puzzles correctly = Higher score ✅
- Take fewer steps to solve = Higher score ✅

---

## The Puzzle Type We're Solving

### What is a "Zebra Puzzle"?

You might know these as "Logic Grid Puzzles" or "Einstein's Riddle". Here's a simple example:

```
There are 3 houses in a row (House 1, House 2, House 3).
Each house has a person with a unique name, favorite color, and pet.

CLUES:
1. Alice lives in the red house
2. The blue house is directly to the left of the green house
3. Bob owns a dog
4. The cat owner lives in house 1
5. Carol doesn't live in the red house

QUESTION: Who lives where with which pet and color?
```

### What Makes It a "CSP"?

**CSP = Constraint Satisfaction Problem**

Think of it like this:
- **Variables** = The things we need to figure out (Who lives where? What color is each house?)
- **Domain** = Possible answers for each variable (House 1, 2, or 3)
- **Constraints** = Rules that must be followed (Alice lives in the red house)

**The goal:** Find values for all variables that satisfy ALL constraints.

---

## How Our Solver Works (The Brain)

### The Main Strategies

Our solver uses 4 clever techniques:

### 1. 🔙 Backtracking (Trial and Error with Memory)

**Simple Explanation:**
Like solving a maze - if you hit a dead end, go back to the last turn and try a different path.

```
Step 1: "Let's try putting Alice in House 1"
Step 2: "Now let's try Bob in House 2"
Step 3: "Hmm, this violates a rule... let me go BACK and try Bob in House 3 instead"
```

### 2. 📊 MRV - Minimum Remaining Values (Choose the Hardest First)

**Simple Explanation:**
If a variable has fewer choices left, solve it first. Why? If it only has 1 choice and that's wrong, we know immediately!

```
Example:
- "Color of House 1" can be: Red, Blue, Green (3 choices)
- "Pet in House 2" can be: Dog (1 choice) ← SOLVE THIS FIRST!
```

**Why it helps:** Finds mistakes faster, so we waste less time.

### 3. 🔮 Forward Checking (Look Before You Leap)

**Simple Explanation:**
Before making a choice, check if it would make the puzzle impossible to solve.

```
"If I put Alice in House 1..."
"Let me check... would any other variable become impossible?"
"Yes! Bob would have no valid house left... so don't put Alice in House 1"
```

### 4. 🔗 AC-3 (Arc Consistency - Super Detective)

**Simple Explanation:**
A deeper check that removes impossible values from all variables at once.

```
"If House 1 is Red, then House 2 and House 3 can't be Red"
"Let me remove Red from their possible values"
"Now those choices are simpler!"
```

### How They Work Together

```
┌─────────────────────────────────────────────────────────────┐
│                    SOLVING A PUZZLE                         │
├─────────────────────────────────────────────────────────────┤
│  1. AC-3 removes obviously impossible values                │
│  2. MRV picks the most constrained variable                 │
│  3. Try assigning a value to that variable                  │
│  4. Forward Checking removes newly impossible values        │
│  5. If stuck, Backtrack and try different value             │
│  6. Repeat until solved or no solution exists               │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Files Explained

Here's what each file does:

### 📁 `data_loader.py` - The Reader
**Job:** Reads puzzles from different sources

```
Input:  Dataset from HuggingFace, JSON files, CSV files
Output: Clean puzzle objects ready for solving
```

**Key Functions:**
- `load_puzzles()` - Main function to load puzzles from anywhere
- `parse_puzzle_header()` - Extracts number of houses and attributes
- `parse_clues()` - Extracts the clue sentences
- `parse_clue_to_constraint()` - Converts English sentences to math rules

**Example:**
```
Input:  "Alice lives in the red house"
Output: EQUALITY constraint - Alice's house = Red house's position
```

---

### 📁 `solver.py` - The Brain
**Job:** The actual puzzle-solving logic

```
Input:  Parsed puzzle with constraints
Output: Solution (who lives where with what)
```

**Key Classes:**
- `CSPVariable` - Represents one thing we need to figure out
- `CSPConstraint` - Represents one rule
- `CSPSolver` - The main solver with all strategies
- `ZebraPuzzleSolver` - Wrapper specifically for Zebra puzzles

**The Solving Process:**
```python
# Simplified view of what happens
solver = ZebraPuzzleSolver()
solver.setup_from_puzzle(puzzle)      # Set up variables and rules
stats = solver.solve()                # Run the solving algorithm
solution = stats.solution             # Get the answer!
```

---

### 📁 `run.py` - The Commander
**Job:** Runs everything and produces final output

```
Input:  Command line arguments (what puzzles to solve)
Output: results.json with all solutions
```

**What It Does:**
1. Reads puzzles using `data_loader.py`
2. Solves each puzzle using `solver.py`
3. Formats the answers
4. Saves everything to `results.json`

---

### 📁 `trace_generator.py` - The Note-Taker
**Job:** Records every decision the solver makes

```
Input:  Solver's steps
Output: Detailed logs for analysis
```

**Why Useful?**
- Helps debug when things go wrong
- Can train AI models to make better decisions
- Shows how efficient the solver is

---

### 📁 `results.json` - The Answer Sheet
**Job:** Final output with all solutions

**Format:**
```json
{
  "puzzle_000": {
    "Alice": {
      "color": "red",
      "pet": "dog",
      "house": 1
    },
    "Bob": {
      "color": "blue",
      "pet": "cat",
      "house": 2
    }
  }
}
```

---

### 📁 `evaluation.ipynb` - The Report Card
**Job:** Jupyter notebook that calculates scores and shows statistics

**Shows:**
- How many puzzles were solved correctly
- How fast the solver is
- Charts and graphs of performance

---

## Step-by-Step: How Data Flows

Let's follow one puzzle from start to finish:

### Step 1: Loading the Puzzle
```
┌─────────────────────────────────────────────────────────────┐
│ HuggingFace Dataset                                         │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ puzzle: "There are 3 houses. Each house has a person   │ │
│ │         with a name (Alice, Bob, Carol), color (red,   │ │
│ │         blue, green), and pet (dog, cat, fish)..."     │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ data_loader.py                                              │
│ - Extracts: 3 houses                                        │
│ - Extracts: attributes (name, color, pet)                   │
│ - Extracts: values (Alice, Bob, Carol, red, blue, green...) │
│ - Extracts: clues (list of rules)                           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ CSPPuzzle Object                                            │
│ {                                                           │
│   puzzle_id: "puzzle_000",                                  │
│   num_houses: 3,                                            │
│   attributes: {name: [...], color: [...], pet: [...]},      │
│   clues: ["Alice lives in...", "The dog owner..."],         │
│   parsed_clues: [{type: "equality", ...}, ...]              │
│ }                                                           │
└─────────────────────────────────────────────────────────────┘
```

### Step 2: Setting Up the CSP
```
┌─────────────────────────────────────────────────────────────┐
│ solver.py - setup_from_puzzle()                             │
├─────────────────────────────────────────────────────────────┤
│ CREATES VARIABLES:                                          │
│   Name_Alice: can be {1, 2, 3}                              │
│   Name_Bob: can be {1, 2, 3}                                │
│   Name_Carol: can be {1, 2, 3}                              │
│   Color_Red: can be {1, 2, 3}                               │
│   Color_Blue: can be {1, 2, 3}                              │
│   ... and so on                                             │
├─────────────────────────────────────────────────────────────┤
│ CREATES CONSTRAINTS:                                        │
│   - All names must be in different houses                   │
│   - All colors must be in different houses                  │
│   - "Alice lives in red house" → Name_Alice = Color_Red     │
│   - "Dog owner is left of cat" → Pet_Dog + 1 = Pet_Cat     │
│   ... and so on                                             │
└─────────────────────────────────────────────────────────────┘
```

### Step 3: Solving
```
┌─────────────────────────────────────────────────────────────┐
│ solver.py - solve()                                         │
├─────────────────────────────────────────────────────────────┤
│ Step 1: Run AC-3 to reduce domains                          │
│         Name_Alice: {1, 2, 3} → {1}  (only house 1 works!)  │
│                                                             │
│ Step 2: MRV picks Name_Alice (only 1 choice)                │
│                                                             │
│ Step 3: Assign Name_Alice = 1                               │
│                                                             │
│ Step 4: Forward Check - remove 1 from other names           │
│         Name_Bob: {1, 2, 3} → {2, 3}                        │
│         Name_Carol: {1, 2, 3} → {2, 3}                      │
│                                                             │
│ Step 5: MRV picks next variable, continue...                │
│                                                             │
│ ... (many more steps) ...                                   │
│                                                             │
│ Final: All variables assigned, all constraints satisfied!   │
└─────────────────────────────────────────────────────────────┘
```

### Step 4: Output
```
┌─────────────────────────────────────────────────────────────┐
│ Solution Found!                                             │
│ {                                                           │
│   Name_Alice: 1,    Color_Red: 1,     Pet_Dog: 2,          │
│   Name_Bob: 2,      Color_Blue: 2,    Pet_Cat: 3,          │
│   Name_Carol: 3,    Color_Green: 3,   Pet_Fish: 1          │
│ }                                                           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Formatted for results.json                                  │
│ {                                                           │
│   "Alice": {"color": "red", "pet": "fish", "house": 1},     │
│   "Bob": {"color": "blue", "pet": "dog", "house": 2},       │
│   "Carol": {"color": "green", "pet": "cat", "house": 3}     │
│ }                                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## How to Run the Project

### Step 1: Install Requirements
```powershell
# Open PowerShell in the project folder
cd b:\AI-CONNECT\ai-connect-csp

# Install required packages
pip install datasets pandas matplotlib
```

### Step 2: Run the Solver
```powershell
# Basic run - solves puzzles from ZebraLogicBench
python run.py

# Solve only first 10 puzzles (for testing)
python run.py --max 10

# Solve puzzles from a custom file
python run.py --input my_puzzles.json

# Enable detailed tracing
python run.py --trace

# See all options
python run.py --help
```

### Step 3: Check Results
After running, check these files:
- `results.json` - Your solutions
- `results_stats.json` - Statistics (how many solved, average time)
- `traces/` folder - Detailed logs (if tracing enabled)

---

## Understanding the Output

### Terminal Output
```
[1/100] Solving puzzle_000... ✓ (23 steps, 5.2ms)
[2/100] Solving puzzle_001... ✓ (45 steps, 8.1ms)
[3/100] Solving puzzle_002... ✗ No solution
...
============================================================
SUMMARY
============================================================
Solved: 98/100 (98.0%)
Average steps: 34.5
Average time: 6.8ms
============================================================
```

**What this means:**
- `✓` = Puzzle solved successfully
- `✗` = Could not find solution
- `23 steps` = How many decisions the solver made
- `5.2ms` = Time taken (milliseconds)

### results.json Format
```json
{
  "puzzle_000": {
    "Alice": {
      "nationality": "british",
      "color": "red",
      "pet": "dog",
      "house": 1
    },
    "Bob": {
      "nationality": "german", 
      "color": "blue",
      "pet": "cat",
      "house": 2
    }
  }
}
```

Each puzzle has a solution organized by person, showing all their attributes and which house they live in.

---

## Key Concepts Dictionary

| Term | Simple Explanation | Real-World Analogy |
|------|-------------------|-------------------|
| **CSP** | A problem with variables, possible values, and rules | Sudoku - fill numbers following rules |
| **Variable** | Something we need to figure out | "Which house does Alice live in?" |
| **Domain** | Possible values for a variable | {House 1, House 2, House 3} |
| **Constraint** | A rule that must be followed | "Alice can't be in House 3" |
| **Backtracking** | Going back when stuck | Hitting a dead end in a maze, turning around |
| **MRV** | Solving the most restricted thing first | Do the hardest homework first |
| **Pruning** | Removing impossible options | Crossing out wrong answers on a test |
| **Arc Consistency** | Advanced checking between pairs | Making sure related answers don't conflict |
| **Dataset** | Collection of puzzles | A puzzle book with 1000 puzzles |
| **HuggingFace** | Website hosting datasets | A library for data |
| **JSON** | A data format computers can read | Like a structured list |

---

## Frequently Asked Questions

### Q: Why do some puzzles show "No solution"?
**A:** Either:
1. The puzzle actually has no valid solution (contradictory clues)
2. Our parser couldn't understand some clues correctly
3. A bug in constraint generation

### Q: Why use MRV? Why not just solve in order?
**A:** Imagine you have a variable that can only be 1 value. If you check it last and it's wrong, you wasted time checking everything else. MRV catches these quickly!

### Q: What's the difference between Forward Checking and AC-3?
**A:** 
- **Forward Checking:** Only checks constraints with the variable you just assigned
- **AC-3:** Checks ALL pairs of constrained variables, deeper but slower

### Q: How is accuracy calculated?
**A:** 
```
Accuracy = (Correctly Solved Puzzles / Total Puzzles) × 100%
```

### Q: What if I want to use my own puzzles?
**A:** Save them in JSON format like this:
```json
[
  {
    "id": "my_puzzle_1",
    "puzzle": "There are 3 houses..."
  }
]
```
Then run: `python run.py --input my_puzzles.json`

### Q: Why Python?
**A:** Python is:
- Easy to read and write
- Has great libraries for data processing
- Standard for AI/ML challenges

---

## Summary: The Big Picture

```
┌─────────────────────────────────────────────────────────────────┐
│                        THE WHOLE SYSTEM                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│   │   INPUT     │    │   SOLVER    │    │   OUTPUT    │        │
│   │             │    │             │    │             │        │
│   │ • Dataset   │───▶│ • Parse     │───▶│ • results   │        │
│   │ • JSON file │    │ • Setup CSP │    │   .json     │        │
│   │ • CSV file  │    │ • Solve     │    │ • stats     │        │
│   │             │    │ • Format    │    │ • traces    │        │
│   └─────────────┘    └─────────────┘    └─────────────┘        │
│                              │                                  │
│                              │                                  │
│                    ┌─────────▼─────────┐                       │
│                    │ SOLVING STRATEGY  │                       │
│                    │                   │                       │
│                    │ 1. AC-3 (clean)   │                       │
│                    │ 2. MRV (pick)     │                       │
│                    │ 3. Assign (try)   │                       │
│                    │ 4. Forward Check  │                       │
│                    │ 5. Backtrack?     │                       │
│                    │ 6. Repeat!        │                       │
│                    └───────────────────┘                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**You now understand how this puzzle-solving robot works!** 🎉

---

## Need More Help?

1. **Check the README.md** for technical details
2. **Look at evaluation.ipynb** for performance analysis
3. **Run with `--trace`** to see exactly what the solver does
4. **Read the comments** in each Python file

Good luck with the AI Connect 2025 Challenge! 🚀
