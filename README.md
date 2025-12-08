# Pips Puzzle Solver — Final Project

## 1. Overview

This project implements a complete constraint-programming solver using CP-SAT for *Pips*, a logic puzzle involving:

- A shaped grid of cells
- Regions, each labeled with a constraint
- A set of dominos, each containing two pip values  

The solver must place every domino on the grid so that:

1. Every valid cell is covered exactly once.
2. Pip values written onto cells match the values of the placed dominos.
3. All region constraints (Eq, Neq, Sum, Lt, Gt) are satisfied. If a region has an Eq constraint, all cell values in the region must be the same. For Neq, all values must be different. For Sum, Lt, and Gt, the sum of the values in the cell must be equal to the target, less than the target number, or greater than the target number respectively.

## Initial Approach: Modeling Pips as a Constraint Optimization Problem

Our first step was to formalize the Pips puzzle into a precise constraint-satisfaction model
The puzzle contains:

- A board with valid cells (`.`) and blocked cells (`#`)
- A set of **regions**, each with a constraint (Eq, Neq, Sum, Lt, Gt)
- A list of **dominos**, each containing two pip values `(a, b)`
- The requirement that dominos must be placed onto the board so that:
  - Every valid cell is covered exactly once
  - Pip values in cells match the domino that covers them
  - All region constraints are satisfied

To encode this, we introduced three major classes of variables and a set of structural rules that relate them.

### Variable Definitions

#### 1. Domino Placement Variables
For each domino `d`, we enumerate all valid placements:

- (row, col) of its left/top cell
- orientation (horizontal/vertical)
- forward/reversed ordering of pip values

If domino `d` has `K` possible placements, we define place[d] ∈ {0, 1, …, K–1}. Each index encodes a deterministic geometric placement.

#### 2. Cell Pip Value Variables:
For each valid board cell `(r, c)`, cell_value[r][c] ∈ [0, max_pip]. These are the values that are constrained by region rules, and inherit values from domino implications as defined next.

#### 3. Boolean Placement Indicators
To support implications and “exactly one” constraints, we add Boolean helpers is_place[d][k] = 1 ⇔ (place[d] == k). These allows us to add conditional constraints that link domino placements to cell values, i.e. `is_place[d][k] → cell_value[r][c] == v0
is_place[d][k] → cell_value[r2][c2] == v1`, so on and so forth. Thus, the choice of placement directly assigns pip values to cells.

### Constraints
1. Exact cell coverage For each valid cell (r, c) we collect all placements (d, k) whose geometry covers that cell. We then enforce AddExactlyOne( is_place[d][k] for all (d, k) that cover (r, c)). This guarantees that every valid cell is covered by some domino, no cell is covered by two dominos, and blocked cells are simply ignored and have no variables.
2. Domino → cell value consistency For each domino d and placement k, we know the coordinates of its first cell (r1, c1) and second cell (r2, c2), the pip values (v0, v1) contributed to those cells in that orientation. We encode:
```
is_place[d][k] ⇒ cell_value[r1][c1] = v0
is_place[d][k] ⇒ cell_value[r2][c2] = v1
```
These channel the high-level placement decision into concrete pip assignments at the cell level. Together with the coverage constraints, this forbids “splitting” dominos or creating inconsistent pip patterns.

3. Region constraints: During parsing we build a mapping: label → list of cells in that region, label → (constraint_type, target_value?)
For each region we collect its cell-value variables and add the appropriate constraint:
Eq: all equal: cell_value[r1][c1] = cell_value[r2][c2] = …
Neq: all distinct: AddAllDifferent(vars)
Sum: sum equals target: Add(sum(vars) == target)
Lt: sum strictly less than target: Add(sum(vars) < target)
Gt: sum strictly greater than target: Add(sum(vars) > target)

This directly mirrors the logical rules of the puzzle.
### Why CP-SAT?
We chose OR-Tools CP-SAT since it has a natural match to the problem sucture (combinatorial placement choices, boolean implications, and arithmetic constraints on sums and equality). CP-SAT is designed exactly for this mix of SAT-style logic and integer arithmetic.
- CP-SAT also has efficient propagation on exact-one and implication constraints. Constraints such as AddExactlyOne and conditional equalities are optimized in CP-SAT. When we tie is_place[d][k] to cell_value variables, the solver can quickly prune inconsistent placements without explicit backtracking logic on our side.
- Built-in support for AllDifferent and linear sums. Region constraints use AllDifferent, equality sums, and strict inequalities. CP-SAT provides these natively and uses sophisticated propagation algorithms (e.g., for AllDifferent) that would be tedious and error-prone to reimplement using a simple SAT solver.
- Robust performance and completeness. Overall this let us focus on a clean model rather than custom search code, while still getting reasonable runtimes across a wide variety of randomly generated puzzles.

Overall, expressing Pips as a CP-SAT model gives us a clear separation between puzzle logic (encoded as constraints) and search strategy (delegated to the solver), and provides a solid baseline before layering on additional heuristics like equality-first branching or static domain pruning.

## Solver Analysis for different implementations
In our project, we developed three CP-SAT–based solvers for Pips puzzles. Each solver targets a different performance need and applies different levels of preprocessing and guided search.
### 1. `solve_pips` — The Baseline Solver 

This is the default that only includes the constraints/variables defined above and solves accordingly. It encodes the puzzle exactly and lets CP-SAT determine the search order and propagation strategy internally.

### 2. `solve_pips_equality` — The Equality-First Heuristic Solver

This solver performs structural preprocessing pass targeting equality regions. This is something that we both use when solving the puzzles as individuals, so we decided to see if it would improve performance. It works by counting the number of times each pip value appears across all dominos, and if the # of times it appears is less than T (the number of cells covered by one equality region), that pip value is eliminated from consideration in that equality region.

### 3. `solve_pips_pruning` — The Statically Pruning Heuristic Solver
We decided to try a heuristic that limits cell values during search by removing values in LT/GT/SUM branches if the setting of that value would lead to no feasible solution that meets the constraints.
Initially, we thought of doing dynamic proving, where the solver would eliminate impossible pip values during search by seeing the partially assigned values to some region, and updating the domains of other cells in that region to remove assignments that would lead to no solution. However, after looking into it, we found no easy way to query CP-SAT settings during search and update domains dynamically, unless we introduced many additional variables/constraints into the solver which seemed unnecessary since this is likely already handled more efficiently than CP-SAT.

However, we decided to still statically prune cell value domains at the onset, and guessed that this wouldn't increase the preprocessing time as much as our previous equality heuristic since we only iterate over all regions, and not all dominos.
For each region defined by the puzzle:
- Compute trivial upper bounds (max_sum = 6 * |region|).
- Compute trivial lower bounds (min_sum = 0).

Use SUM / LT / GT targets to shrink domains of individual cells before constructing the model.
Examples:
- SUM(region) = T → each cell must satisfy 0 ≤ cell ≤ T.
- LT(region) = T → each cell must satisfy cell ≤ T.
- GT(region) = T with small regions → infer minimum values if the region cannot exceed T otherwise.

![alt text](/images/default_num_dominos.png)
![alt text](/images/equality_num_dominos.png)
![alt text](/images/pruning_num_dominos.png)

![alt text](/images/default_constraint_type.png)
![alt text](/images/equality_constraint_type.png)
![alt text](/images/pruning_constraint_type.png)

## Code Explanation:
The `create_puzzle.py` file has code designed to autogenerate multiple pips puzzles (with parameters such as size, number of dominos, max pip value), which we use in benchmarking. Our main file is `PipsSolver.ipynb`, which contains the puzzle parsing logic, creation of the CP-SAT model, and implementation of heuristics. This file is complete with thorough markdown annotations throughout.

## File Structure Overview
- **`PipsSolver.ipynb`**
  - Main notebook containing all solver implementations:
    - Puzzle parsing logic
    - CP-SAT model construction (variables, constraints, channeling)
    - Three solvers: baseline, equality heuristic, pruning solver
    - Benchmarking code and performance graphs
    - Full markdown explanations of approach and results

- **`create_puzzle.py`**
  - Autogenerates valid Pips puzzles used for benchmarking.
  - Allows control over:
    - Number of dominos
    - Region sizes
    - Constraint types and probabilities
    - Min/max pip values
  - Ensures generated puzzles are solvable by constructing dominos after assigning pip values.

- **`constraint.py`**
  - Defines classes for constraint types (`Eq`, `Neq`, `Sum`, `Lt`, `Gt`, `NoConstraint`)
  - Used by the puzzle generator to label regions with constraint metadata.

- **`pips1.txt`**
  - Example puzzle input.
  - note: other puzzle inputs will be stored in `_puzzle_results/` after running the .ipynb file

- **`/images`**
  - Contains images generated during benchmarking.

## Instructions to Run
To run this project, one can simply run the PipsSolver.ipynb within the class virtual environment to get the desired results/analysis. Make sure to have ortools, matplotlib, and numpy installed beforehand. No additional work needs to be done to run the puzzle and see the results.

The python notebook can be modified to run a specific puzzle as well.
To generate a puzzle, run `puzzle_text = encode(20, [1,2,3,4,5])` as an example. The encode function has the input structure, and additional variables can be added if needed.
```
def encode(num_dominos, region_sizes, constraints=None, probs=None, min_pip=0, max_pip=6)
```
Next, to save a puzzle to a file:
```
puzzle_path = os.path.join(RESULT_DIR, f"puzzle_{i}.txt")
with open(puzzle_path, "w") as f:
    f.write(puzzle_text)p
```
To solve this puzzle and write the solution to a file:
```
n, board, constraints, dominos = parse_pips_puzzle(puzzle_path)
sol, solver = solve_pips(n, board, constraints, dominos)
solution_path = os.path.join(RESULT_DIR, f"solution_{i}.txt")
write_solution_file(solution_path, board, sol)
```
Note that the `solve_pips` can also be replaced by `solve_pips_equality` or `solve_pips_pruning` if you would prefer to run the model with a specific heuristic, but otherwise, that's it!