import random
from dataclasses import dataclass
from enum import Enum
from typing import Set, Tuple
from constraint import Constraint, Eq, Neq, Sum, Lt, Gt
from ortools.sat.python import cp_model


d = 10
n = d * 2

def get_edge_cells(board):
    edges = set()
    for i in range(n):
        for j in range(n):
            if board[i][j]:
                for (dr, dc) in [(0, 1), (0, -1), (-1, 0), (1, 0)]:
                    if 0 <= i + dr < n and 0 <= j + dc < n and not board[i + dr][j + dc]:
                        edges.add((i + dr, j + dc))
    return edges

def is_white_cell(r, c):
    return (r + c) % 2 == 0


def create_board_shape():
    board =  [[False for _ in range(n)] for _ in range(n)]
    # initial domino
    board[n//2][n//2] = True
    board[n//2][n//2 - 1] =  True

    print(is_white_cell(0, 0))
    for i in range(d - 1):
        edge_cells = get_edge_cells(board)

        white_cells =  [(r, c) for (r, c) in edge_cells if is_white_cell(r, c)]
        black_cells =  [(r, c) for (r, c) in edge_cells if not is_white_cell(r, c)]

        (white_row, white_col) = random.choice(white_cells)
        (black_row, black_col) = random.choice(black_cells)
        board[white_row][white_col] = True
        board[black_row][black_col] = True
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
    directions = [(0, 1), (0, -1), (-1, 0), (1, 0)]
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
    if random.random() < 0.15:
        region.constraint = Eq


# Assigning pips
def assign_cell_values(regions):
    board =  [[None for _ in range(n)] for _ in range(n)]

    for region in regions:
        if region.constraint == Eq:
            eq_cell_value = random.randint(0, 6)
            for (r, c) in region.cells:
                board[r][c] = eq_cell_value 
        else:
            for (r, c) in region.cells:
                board[r][c] = random.randint(0, 6)
    return board

cell_value_board = assign_cell_values(regions)

for i in cell_value_board:
    for j in i:
        if j is None:
            print(" ", end = "")
        else:
            print(j, end = "")
    print()

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
                
print(valid_dominos)
for i in placed_dominos:
    for j in i:
        if j is None:
            print(" ", end = "")
        else:
            print(j, end = "")
    print()
#           



def print_board():
    board =  [["." for _ in range(n)] for _ in range(n)]
    for i, region in enumerate(regions):
        for (r, c) in region.cells:
            board[r][c] = chr(i + ord('A'))
    for i in board:
        for j in i:
            print(j, end = "")
        print()
# print(board)
print_board()
