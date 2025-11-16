class Constraint():
    pass

class Eq(Constraint):
    pass

class Neq(Constraint):
    pass

class Sum(Constraint):
    def __init__(self, target):
        self.target = target

class Lt(Constraint):
    def __init__(self, target):
        self.target = target

class Gt(Constraint):
    def __init__(self, target):
        self.target = target
