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

### Challenges:
#### **1. Dynamic Pruning (Failed Attempt)**
Our early idea was to prune search branches *during solving* by enforcing constraints like:
- If partial region sum exceeds LT target → prune immediately  
- If remaining max possible sum cannot reach SUM target → prune  
- If remaining minimum sum exceeds GT target → prune  
BUT CP-SAT does not allow access to partial assignments or dynamic domain inspection.
Thus we could not implement true branch-and-bound pruning. This forced us to adopt **static pruning**, applied *before* constraints are given to the solver, and this luckily improved our solving time.
However, we ultimately abandoned LS for **two major reasons**.
#### **2. Attempt to Use Local Search**
We explored replacing or augmenting CP-SAT with **local search (LS)** methods because:
- It naturally supports **incremental improvements** rather than full satisfaction modeling  
- It can exploit the spatial structure of dominos and regions  
- It is not limited by CP-SAT’s lack of dynamic pruning
However, we realized this would be too complex for two main reasons.
1. **Defining a Valid Neighborhood Was Far More Complex Than Expected**
A valid LS neighbor requires:
1. A legal tiling of dominos  
2. Domino orientation consistency  
3. Region constraints remaining satisfied or at least not severly violated  
4. Pip consistency tied to the specific allowed domino pairs  
However, we discovered the obstacles that:
- Any change to a single domino can invalidate 2–6 adjacent dominos, causing cascading conflicts.
- Rotating or swapping dominos often creates uncovered cells or overlaps, which LS is not equipped to correct cleanly.
- Simple “swap two dominos” cannot discover all possible geometric orientations.
- Generating legal neighbors required reconstructing almost the entire board, defeating the purpose of LS's incremental approach.
2. **Local Search Cannot Guarantee Feasibility**
Pips puzzles require **exact constraint satisfaction**:
- SUM regions must match exactly  
- LT/GT constraints impose strict inequalities  
- Equality regions must all share the same pip value  
- Only specific domino pip-pairs are allowed  
LS, unless heavily guided, can get stuck in infeasible solutions where many constraints are still not fully met, especially with many different geometric orientations of dominos in the puzzle.

**Overall, since our baseline model was already pretty fast, we stuck to making preprocessing-based improvements to this using various heuristics**.

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

### Performance Analysis: Number of Dominos vs. Solver Runtime
The following three plots compare how the **default solver**, the **equality-first heuristic solver**, and the **static pruning solver** scale with respect to the **number of dominos** in a puzzle. Each puzzle is auto-generated using the same parameters, ensuring comparable structure across solvers.

![alt text](/images/default_num_dominos.png)
![alt text](/images/equality_num_dominos.png)
![alt text](/images/pruning_num_dominos.png)

Across all solvers, runtime increases roughly exponentially with the number of dominos.  
This behavior is expected because as the board grows, region constraints, adjacency constraints, and pips domain interactions all multiply and the search space becomes combinatorially larger.

1. Default Solver Behavior
- Shows a smooth and predictable exponential growth curve.
- Runtime remains under ~0.5s until ~20 dominos.
- After ~30 dominos, growth becomes noticeably steeper.
- Spikes appear around 40–45 dominos, but overall variance is low.

The default solver simply relies on CP-SAT’s internal branching heuristics and learns constraints organically during search.  

2. Equality Heuristic Solver Behavior
- Runtime for small cases is comparable to (sometimes faster than) the default solver.
- Variance increases dramatically for puzzles above ~30 dominos.
- Sharp peaks (2–3s) occur more frequently than in the baseline solver.
This could be because when equality regions are common, propagation is strong and the solver finishes quickly, but when equality regions are rare, the solver becomes suboptimal since it still spends preprocessing time counting the number of each pip value even when unnecessary.

3. Pruning Heuristic Solver Behavior (Static Domain Reduction + AddHint)
- Best overall scaling among the three solvers.
- Lower variance: runtime rises steadily without the large spikes seen in the equality solver.
- Maintains a noticeable speedup (roughly 10–15%) over the default solver at higher domino counts.
- Peaks are smaller, often staying below ~2.5s even for 50 dominos (compared to 3s for other solvers)
This solver applies static preprocessing and added hints to motivate the checking of certain regions earlier, allowing infeasible domains to be pruned earlier. Therefore, it makes sense that it may have better performance on average.

**Overall, we see that the pruning heuristic performs the best as the puzzle size increases**

### Constraint-Type Performance Analysis

This section analyzes the performance characteristics of the **Default Solver**, the **Equality Heuristic Solver**, and the **Pruning Heuristic Solver** when puzzles are restricted to *only one type of region constraint* at a time.  

![alt text](/images/default_constraint_type.png)
![alt text](/images/equality_constraint_type.png)
![alt text](/images/pruning_constraint_type.png)

1. Default Solver Behavior
- **EQ, NEQ, and SUM** constraints all run very quickly (≈0.23–0.28s).
- **LT** is the slowest by a noticeable margin: **~0.34s**.
- **GT** is slightly slower than SUM, but still significantly faster than LT.
- **NoConstraint** (regions with no constraint) is the fastest case overall (~0.21s).

This makes sense since LT constraints allow for a wide range of feasible assignments and therefore may have the weakest propagation. EQ and NEQ are stricter and therefore can quickly prune branches/reduce domain width. Clearly, the no-constraint region is the fastest to solve since dominos can be placed in any order.

Overall, The default solver performs **best on highly structured regions** (EQ/NEQ) and **worst on underconstrained LT regions**, where its search space expands significantly.

2. Equality Heuristic Solver Behavior
- EQ and NEQ remain fast (≈0.23–0.24s).
- SUM behaves very similarly (~0.24s).
- LT and GT again show the slowest runtimes (0.30–0.31s).
- NoConstraint stays around ~0.22s.

We noticed that this doesn't change the speed significantly of puzzles with onnly equality puzzles, but can affect the running time of other puzzle types. This could be related to the preprocessing time of counting pip values.

3. Pruning Heuristic Solver Behavior (Static Domain Reduction + AddHint)
- EQ, NEQ, SUM remain fast (≈0.22–0.24s).
- LT and GT are again the slowest (~0.30–0.34s).
- NoConstraint remains the fastest (≈0.21–0.22s).

Static pruning improves performance uniformly, but does not eliminate the inherent complexity differences between constraint types. This did not have a major effect on puzzles limited only to Equality or NEQ, but increased performance on SUM compared to the other solvers. This could be because many generated SUM regions seen are small, and this preprocessing may allow the solver to set the value of those SUM regions initially, therefore pruning the search space. However, this increased the running time of puzzles limited to only Gt constraints, which was unexpected.

**Overall, the pruning solver improves solve times uniformly, but constraint type still dominates performance behavior.**
**Weak constraints (LT, GT) inherently hurt propagation and therefore remain the slowest, even with pruning applied.**

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
