from threading import Timer
from collections import namedtuple


def print_to_file(filename, data):
    with open(filename, 'a') as f:
        f.write(data + '\n')
    pass


def interrupt(s):
    s.interrupt()


def while_true_generator():
    while True:
        yield


def solve_with_timeout(solver, assumptions, timeout):
    timer = Timer(timeout, interrupt, [solver])
    timer.start()

    result = solver.solve_limited(assumptions=assumptions, expect_interrupt=True)

    if result is None:
        solver.clear_interrupt()
    else:
        timer.cancel()

    return result


def solve_with_conflict_limit(solver, assumptions, limit):
    solver.conf_budget(limit)
    result = solver.solve_limited(assumptions=assumptions)
    return result


class PrunedGates:
    def __init__(self, ands, nots):
        self.ands = ands
        self.nots = nots
