import random
from abc import ABC

class Constraint(ABC):
    @classmethod
    def create(cls, region_sum = None):
        return cls()

    @classmethod
    def create_random(cls, region_sum, constraints = None, probs = None):
        
        if probs is None:
            return random.choice(constraints).create(region_sum)
        constraint = random.choices(constraints, weights=probs)[0]
        return constraint.create(region_sum)

                      
class Eq(Constraint):
    def __str__(self):
        return "EQ"


class Neq(Constraint):
    def __str__(self):
        return "NEQ"


class Sum(Constraint):
    def __init__(self, target):
        self.target = target

    @classmethod
    def create(cls, region_sum):
        return cls(region_sum)

    def __str__(self):
        return f"SUM {self.target}"

class Lt(Constraint):
    def __init__(self, target):
        self.target = target

    @classmethod
    def create(cls, region_sum):
        return cls(min(region_sum + random.randint(0, 2), 18))

    def __str__(self):
        return f"LT {self.target}"

class Gt(Constraint):
    def __init__(self, target):
        self.target = target

    @classmethod
    def create(cls, region_sum):
        return cls(max(region_sum - random.randint(0, 2), 0))

    def __str__(self):
        return f"GT {self.target}"

class NoConstraint(Constraint):
    pass
