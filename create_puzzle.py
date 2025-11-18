import random
from dataclasses import dataclass
from enum import Enum
from typing import Set, Tuple
from constraint import Constraint, Eq, Neq, Sum, Lt, Gt, NoConstraint 
from ortools.sat.python import cp_model


num_dominos = 20
n = num_dominos * 2
directions = [(0, 1), (0, -1), (-1, 0), (1, 0)]


def empty_adjacent_cells(board, r, c):
    adj = []
    for (dr, dc) in directions:
        if 0 <= r + dr < n and 0 <= c + dc < n and not board[r + dr][c + dc]:
            adj.append((r + dr, c + dc))
    return adj


def get_edge_cells(board):
    edges = set()
    for i in range(n):
        for j in range(n):
            if board[i][j]:
                edges.update(empty_adjacent_cells(board, i, j))
    return edges



def create_board_shape():
    board =  [[False for _ in range(n)] for _ in range(n)]
    # initial domino
    board[n//2][n//2] = True
    board[n//2][n//2 - 1] =  True

    for i in range(num_dominos - 1):
        edge_cells = list(get_edge_cells(board))
        (r, c) = random.choice(edge_cells)
        board[r][c] = True
        (r2, c2) = random.choice(empty_adjacent_cells(board, r, c))
        board[r2][c2] = True
    return board

def get_board_cells(board):
    cells = set()
    for i, row in enumerate(board):
        for j, cell in enumerate(row):
            if cell:
                cells.add((i, j))
    return cells


@dataclass
class Region:
    cells: Set[Tuple[int, int]]
    constraint: Constraint


def get_region_cells(start_cell, available_cells, size):
    cells = {start_cell}
    available_cells.remove(start_cell)
    stack = [start_cell]
    while stack:
        (i, j) = stack.pop()
        random.shuffle(directions)
        for (dr, dc) in directions:
            if 0 <= i + dr < n and 0 <= j + dc < n and (i + dr, j + dc) in available_cells:
                if len(cells) == size:
                    return cells
                cells.add((i + dr, j + dc))
                stack.append((i + dr, j + dc))
                available_cells.remove((i + dr, j + dc))
    return cells


region_sizes = [1,2,3,4]
board = create_board_shape()
unassigned_cells = get_board_cells(board)

regions = []
while unassigned_cells:
    start_cell = random.choice(list(unassigned_cells))
    region_size = random.choice(region_sizes)
    region_cells = get_region_cells(start_cell,  unassigned_cells, region_size)
    region = Region(region_cells, None)
    regions.append(region)


# equality constraint
for region in regions:
    if len(region.cells) > 1 and random.random() < 0.15:
        region.constraint = Eq()


# Assigning pips
def assign_cell_values(regions):
    board =  [[None for _ in range(n)] for _ in range(n)]

    for region in regions:
        if type(region.constraint) == Eq:
            eq_cell_value = random.randint(0, 6)
            for (r, c) in region.cells:
                board[r][c] = eq_cell_value 
        else:
            for (r, c) in region.cells:
                board[r][c] = random.randint(0, 6)
    return board

cell_value_board = assign_cell_values(regions)

"""
for i in cell_value_board:
    for j in i:
        if j is None:
            print(" ", end = "")
        else:
            print(j, end = "")
    print()
"""


def add_constraints(regions):
    for region in regions:
        if region.constraint is None:
            region_sum = 0
            for (r, c) in region.cells:
                region_sum += cell_value_board[r][c]
            region.constraint = Constraint.create_random(region_sum,
                                                         constraints = [Neq,
                                                                        Sum,
                                                                        Lt, Gt,
                                                                        NoConstraint])

add_constraints(regions)

# Creating dominos
dominos = []
model = cp_model.CpModel()
# horizontal
for r in range(n):
    for c in range(n - 1):
        var = model.NewBoolVar(f'h_{r}_{c}')
        dominos.append((var, [(r,c), (r, c + 1)]))

# vertical 
for r in range(n - 1):
    for c in range(n):
        var = model.NewBoolVar(f'v_{r}_{c}')
        dominos.append((var, [(r,c), (r + 1, c)]))

cells = {cell for region in regions for cell in region.cells}
for (r, c) in cells:
    dominos_over_cell = [var for var, domino_cells in dominos if (r, c) in
                         domino_cells and all([domino_cell in cells for domino_cell in
                                               domino_cells])]
    model.Add(sum(dominos_over_cell) == 1)

valid_dominos = []
placed_dominos =  [[0 for _ in range(n)] for _ in range(n)]
solver = cp_model.CpSolver()
status = solver.Solve(model)
if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
    domino_id = 1
    for var, cells in dominos:
        if solver.Value(var):
            domino = []
            for r, c in cells:
                domino.append(cell_value_board[r][c])
                placed_dominos[r][c] = domino_id

            valid_dominos.append(tuple(domino))
            domino_id += 1

def encode_board():
    lines = []
    board =  [["." for _ in range(n)] for _ in range(n)]
    for i, region in enumerate(regions):
        for (r, c) in region.cells:
            if type(region.constraint) is NoConstraint:
                board[r][c] = '#'
            else:
                board[r][c] = chr(i + ord('A'))

    for i in board:
        line = []
        for j in i:
            line.append(j)
        lines.append("".join(line))
    return "\n".join(lines)

def encode():
    lines = []
    lines.append(str(n))

    lines.append(encode_board())
    num_constraints = sum(1 for region in regions if type(region.constraint) is not
                          NoConstraint)
    lines.append(str(num_constraints))
    for i, region in enumerate(regions):
        if type(region.constraint) is not NoConstraint:
            lines.append(chr(ord('A') + i) + " " + str(region.constraint))
    lines.append(str(num_dominos))
    for domino in valid_dominos:
        lines.append(f"{domino[0]} {domino[1]}")
    return "\n".join(lines)

def print_puzzle():
   print(encode()) 

def write_puzzle(path):
    with open(path, "w") as f:
        f.write(encode())

print_puzzle()
write_puzzle("text.txt")
