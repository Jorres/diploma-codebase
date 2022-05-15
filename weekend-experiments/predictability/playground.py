import os
import pysat
import subprocess
import sys
import time
from pycryptosat import Solver
from pysat.solvers import Maplesat as PysatSolver


# 0 0 0 | 0
# 0 0 1 | 0
# 0 1 0 | 0
# 0 1 1 | 1
# 1 0 0 | 0
# 1 0 1 | 1
# 1 1 0 | 1
# 1 1 1 | 1

def do_single_test(i, j, k, m):
    formula = pysat.formula.CNF()

    if i == 0:
        i = 1
    else:
        i = -1

    if j == 0:
        j = 1
    else:
        j = -1

    if k == 0:
        k = 1
    else:
        k = -1

    if m == 0:
        m = 1
    else:
        m = -1
    
    formula.append([-1*i, -1*j, m ])
    formula.append([-1*i, -1*k, m ])
    formula.append([-1*j, -1*k, m ])

    formula.append([   i,    j, -m ])
    formula.append([   i,    k, -m ])
    formula.append([   j,    k, -m ])

    solver = Solver()
    solver.add_clauses(formula.clauses)
    res, solution = solver.solve()

    return res


def do_all_tests():
    for i in range(0, 2):
        for j in range(0, 2):
            for k in range(0, 2):
                for m in range(0, 2):
                    should_be = (i + j + k) > 1
                    should_be_2 = should_be == (m == 1)
                    print(i, j, k, m)
                    assert do_single_test(i, j, k, m) == should_be_2


do_all_tests()
