import random
from dataclasses import dataclass
from enum import Enum
from typing import Set, Tuple
from constraint import Constraint, Eq, Neq, Sum, Lt, Gt, NoConstraint
from ortools.sat.python import cp_model


directions = [(0, 1), (0, -1), (-1, 0), (1, 0)]


def empty_adjacent_cells(board, r, c):
    n = len(board)
    adj = []
    for dr, dc in directions:
        if 0 <= r + dr < n and 0 <= c + dc < n and not board[r + dr][c + dc]:
            adj.append((r + dr, c + dc))
    return adj


def create_board_shape(num_dominos):
    n = num_dominos * 4
    board = [[False for _ in range(n)] for _ in range(n)]
    dominos = [((n // 2, n // 2), (n // 2, n // 2 - 1))]
    # initial domino
    board[n // 2][n // 2] = True
    board[n // 2][n // 2 - 1] = True
    edges = set()
    edges.update(empty_adjacent_cells(board, n // 2, n // 2))
    edges.update(empty_adjacent_cells(board, n // 2, n // 2 - 1))

    dominos_fit = 1
    while dominos_fit < num_dominos:
        edge_cells = list(edges)
        (r, c) = random.choice(edge_cells)
        empty_adj = empty_adjacent_cells(board, r, c)
        if empty_adj:
            (r2, c2) = random.choice(empty_adj)
            board[r][c] = True
            board[r2][c2] = True
            dominos.append(((r, c), (r2, c2)))
            dominos_fit += 1
            edges.update(empty_adj)
            edges.update(empty_adjacent_cells(board, r2, c2))
            edges.remove((r, c))
            edges.remove((r2, c2))
    return board, dominos


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


def get_region_cells(start_cell, available_cells, size, n):
    cells = {start_cell}
    available_cells.remove(start_cell)
    stack = [start_cell]
    while stack:
        (i, j) = stack.pop()
        random.shuffle(directions)
        for dr, dc in directions:
            if (
                0 <= i + dr < n
                and 0 <= j + dc < n
                and (i + dr, j + dc) in available_cells
            ):
                if len(cells) == size:
                    return cells
                cells.add((i + dr, j + dc))
                stack.append((i + dr, j + dc))
                available_cells.remove((i + dr, j + dc))
    return cells


def get_regions(board: list[list[bool]], region_sizes):
    n = len(board)
    unassigned_cells = get_board_cells(board)
    regions = []
    while unassigned_cells:
        start_cell = random.choice(list(unassigned_cells))
        region_size = random.choice(region_sizes)
        region_cells = get_region_cells(start_cell, unassigned_cells, region_size, n)
        region = Region(region_cells, None)
        regions.append(region)
    return regions


def set_equality_constraints(regions, eq_prob):
    # equality constraint
    for region in regions:
        if eq_prob == 1 or (len(region.cells) > 1 and random.random() < eq_prob):
            region.constraint = Eq()


# Assigning pips
def assign_cell_values(regions, n, min_pip=0, max_pip=6):
    board = [[None for _ in range(n)] for _ in range(n)]

    for region in regions:
        if type(region.constraint) == Eq:
            eq_cell_value = random.randint(min_pip, max_pip)
            for r, c in region.cells:
                board[r][c] = eq_cell_value
        else:
            for r, c in region.cells:
                board[r][c] = random.randint(min_pip, max_pip)
    return board


def add_constraints(regions, cell_value_board, constraints=None, probs=None):
    if constraints is None:
        constraints = [Neq, Sum, Lt, Gt, NoConstraint]
    for region in regions:
        if region.constraint is None:
            region_sum = 0
            for r, c in region.cells:
                region_sum += cell_value_board[r][c]
            distinct = len(region.cells) == len(
                {cell_value_board[r][c] for r, c in region.cells}
            )
            if not distinct:
                if probs:
                    filtered_constraints = [
                        (c, p) for c, p in zip(constraints, probs) if constraints != Neq
                    ]
                    constraints, probs = zip(*filtered_constraints)
                    constraints, probs = list(constraints), list(probs)
                else:
                    constraints = [c for c in constraints if c != Neq]
                    if not constraints:
                        # Only constraint is Neq but current region has duplicate pips
                        constraints = [NoConstraint]
            region.constraint = Constraint.create_random(
                region_sum, constraints=constraints, probs=probs
            )


def get_dominos(domino_positions, cell_value_board):
    valid_dominos = []
    for (r1, c1), (r2, c2) in domino_positions:
        valid_dominos.append((cell_value_board[r1][c1], cell_value_board[r2][c2]))

    return valid_dominos


@dataclass
class Puzzle:
    num_dominos: int
    regions: list[Region]
    valid_dominos: list[Tuple[int, int]]


def create_puzzle(
    num_dominos, region_sizes, constraints=None, probs=None, min_pip=0, max_pip=6
):
    if constraints is None:
        constraints = [Eq, Neq, Sum, Lt, Gt, NoConstraint]
    try:
        eq_index = constraints.index(Eq)
    except ValueError:
        eq_index = -1
    if eq_index == -1:
        eq_prob = 0
    else:
        if probs is None:
            eq_prob = 1 / len(constraints)
        else:
            eq_prob = probs.pop(eq_index)
        constraints.pop(eq_index)

    n = num_dominos * 4
    region_sizes = [1, 2, 3, 4]
    board, domino_positions = create_board_shape(num_dominos)
    regions = get_regions(board, region_sizes)
    set_equality_constraints(regions, eq_prob)
    cell_value_board = assign_cell_values(regions, n, min_pip, max_pip)
    add_constraints(regions, cell_value_board, constraints, probs)
    valid_dominos = get_dominos(domino_positions, cell_value_board)
    return Puzzle(num_dominos, regions, valid_dominos)


def encode_board(regions, n, first_r, first_c):
    lines = []
    board = [["." for _ in range(n)] for _ in range(n)]
    for i, region in enumerate(regions):
        for r, c in region.cells:
            if type(region.constraint) is NoConstraint:
                board[r - first_r][c - first_c] = "#"
            else:
                board[r - first_r][c - first_c] = chr(i + ord("A"))

    for i in board:
        line = []
        for j in i:
            line.append(j)
        lines.append("".join(line))
    return "\n".join(lines)


def truncate_board(regions, n):
    board = [[False for _ in range(n)] for _ in range(n)]
    for i, region in enumerate(regions):
        for r, c in region.cells:
            board[r][c] = True
    first_r = -1
    last_r = -1
    for i, r in enumerate(board):
        if any(r):
            last_r = i
            if first_r == -1:
                first_r = i

    first_c = -1
    last_c = -1
    for i, c in enumerate(zip(*board)):
        if any(c):
            last_c = i
            if first_c == -1:
                first_c = i
    trunc_n = max(last_r - first_r + 1, last_c - first_c + 1)
    return trunc_n, first_r, first_c


def encode(
    num_dominos, region_sizes, constraints=None, probs=None, min_pip=0, max_pip=6
):
    puzzle = create_puzzle(num_dominos, region_sizes, constraints, probs)
    regions = puzzle.regions
    valid_dominos = puzzle.valid_dominos
    num_dominos = puzzle.num_dominos
    n, first_r, first_c = truncate_board(regions, num_dominos * 4)
    lines = []
    lines.append(str(n))

    lines.append(encode_board(regions, n, first_r, first_c))
    num_constraints = sum(
        1 for region in regions if type(region.constraint) is not NoConstraint
    )
    lines.append(str(num_constraints))
    for i, region in enumerate(regions):
        if type(region.constraint) is not NoConstraint:
            lines.append(chr(ord("A") + i) + " " + str(region.constraint))
    lines.append(str(num_dominos))
    for domino in valid_dominos:
        lines.append(f"{domino[0]} {domino[1]}")
    return "\n".join(lines)


def print_puzzle():
    print(encode(20, [1, 2, 3, 4, 5]))


def write_puzzle(path):
    with open(path, "w") as f:
        f.write(encode(20, [1, 2, 3, 4, 5]))


write_puzzle("text.txt")
